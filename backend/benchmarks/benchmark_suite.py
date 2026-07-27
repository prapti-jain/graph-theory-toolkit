#!/usr/bin/env python3
"""Standalone asymptotic-complexity benchmark suite for core algorithms.

Run from the ``backend/`` directory::

    python -m benchmarks.benchmark_suite

or::

    python benchmarks/benchmark_suite.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

# Ensure ``backend/`` is on sys.path when executed as a script.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from algorithms.centrality import pagerank
from algorithms.flows import ford_fulkerson
from algorithms.mst import kruskals, prims
from algorithms.shortest_paths import dijkstra
from algorithms.traversal import bfs
from benchmarks.benchmark import (
    evaluate_claim,
    fit_against_graph_terms,
    fit_complexity_curve,
    graph_term_fn,
    predict_curve,
    run_benchmark,
)
from graph_core.generators import random_graph, random_weighted_graph
from graph_core.graph import Graph

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Algorithms where pure power-of-n fits are especially misleading; report
# side-by-side n-power vs graph-term R² for these.
GRAPH_TERM_REPORT_ALGOS = {"dijkstra", "kruskals", "ford_fulkerson"}

CLAIMED_TERM_LABEL = {
    "O(E log V)": "E*log(V)",
    "O(E log E)": "E*log(E)",
    "O(V E^2)": "V*E^2",
    "O(V+E)": "V+E",
    "O(k(V+E))": "k(V+E)",
    "O(n)": "n",
    "O(n log n)": "n*log(n)",
    "O(n^2)": "n^2",
}


def _sparse_p(n: int, avg_degree: float = 6.0) -> float:
    """Edge probability targeting roughly ``avg_degree`` for ER graphs."""
    if n <= 1:
        return 0.0
    return min(0.5, avg_degree / max(n - 1, 1))


def gen_undirected(n: int) -> Graph:
    return random_graph(n, _sparse_p(n), directed=False, weighted=False)


def gen_weighted_undirected(n: int) -> Graph:
    return random_weighted_graph(n, _sparse_p(n), 1.0, 10.0)


def gen_connected_weighted(n: int) -> Graph:
    """Connected weighted undirected graph (required for MST)."""
    p = max(_sparse_p(n, avg_degree=8.0), min(0.4, 3.0 * __import__("math").log(n + 1) / n))
    for _ in range(40):
        g = random_weighted_graph(n, p, 1.0, 10.0)
        if nx.is_connected(g.to_networkx()):
            return g
    # Fallback: denser graph.
    return random_weighted_graph(n, min(0.5, p * 2), 1.0, 10.0)


def gen_directed_flow(n: int) -> Graph:
    """Sparse directed capacity network."""
    g = random_graph(n, _sparse_p(n, avg_degree=5.0), directed=True, weighted=True)
    # Ensure every capacity is positive and a bit larger for numeric stability.
    out = Graph(directed=True, weighted=True)
    for node in g.get_nodes():
        out.add_node(node)
    for u, v, w in g.get_edges():
        out.add_edge(u, v, max(float(w), 0.05) * 5.0)
    # Guarantee source 0 can reach at least one other node.
    if n >= 2 and out.num_edges == 0:
        out.add_edge(0, 1, 1.0)
    return out


def gen_directed(n: int) -> Graph:
    return random_graph(n, _sparse_p(n), directed=True, weighted=False)


def _wrap_bfs(graph: Graph) -> Any:
    return bfs(graph, 0)


def _wrap_dijkstra(graph: Graph) -> Any:
    return dijkstra(graph, 0)


def _wrap_ford(graph: Graph) -> Any:
    sink = graph.num_nodes - 1 if graph.num_nodes > 1 else 0
    return ford_fulkerson(graph, 0, sink)


def _count_augmenting_paths(graph: Graph) -> int:
    """Instrument one Edmonds–Karp run (not timed) to count augmentations."""
    sink = graph.num_nodes - 1 if graph.num_nodes > 1 else 0
    steps: list[dict[str, Any]] = []
    ford_fulkerson(graph, 0, sink, record_steps=steps)
    return sum(1 for s in steps if s.get("action") == "augment")


def _wrap_pagerank(graph: Graph) -> Any:
    return pagerank(graph, max_iterations=50, tolerance=1e-6)


def _save_plot(
    name: str,
    points: list[dict[str, Any]],
    fit: dict[str, Any],
    claimed: str,
) -> Path:
    sizes = [p["size"] for p in points]
    times = [p["mean_time"] for p in points]
    edges = [p["num_edges"] for p in points]
    stds = [p["std_time"] for p in points]

    best = fit["best_fit"]
    param = fit["fits"][best]["param"]
    curve = predict_curve(sizes, edges, best, param)

    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    ax.errorbar(
        sizes,
        times,
        yerr=stds,
        fmt="o",
        color="#1f4e79",
        ecolor="#7a9bb8",
        capsize=3,
        label="measured mean ± std",
    )
    ax.plot(
        sizes,
        curve,
        "--",
        color="#c45c26",
        linewidth=2,
        label=f"fitted {best}",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("nodes (n)")
    ax.set_ylabel("runtime (s)")
    ax.set_title(
        f"{name}: empirical {fit['empirical_label']}, claimed {claimed}"
    )
    ax.legend(loc="best")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    fig.tight_layout()

    out = RESULTS_DIR / f"{name}.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def _format_point_line(row: dict[str, Any], *, show_median: bool) -> str:
    median_bit = ""
    if show_median and "median_time" in row:
        median_bit = f"  median={row['median_time']*1000:8.3f} ms"
    flag = ""
    if row.get("high_variance"):
        ratio = (row["std_time"] / row["mean_time"]) if row["mean_time"] else 0.0
        flag = (
            f"  ** high variance (std={ratio:.0%} of mean), "
            "consider re-running **"
        )
    return (
        f"  n={row['size']:>5d}  edges={row['num_edges']:>6d}  "
        f"mean={row['mean_time']*1000:8.3f} ms"
        f"{median_bit}"
        f"  std={row['std_time']*1000:7.3f} ms"
        f"{flag}"
    )


def _side_by_side_report(
    name: str,
    claimed: str,
    n_fit: dict[str, Any],
    term_fit: dict[str, Any],
) -> str:
    term_label = CLAIMED_TERM_LABEL.get(claimed, claimed)
    n_status = "MISLEADING"
    term_status = "MATCH" if term_fit.get("match") else "WEAK"
    r2 = term_fit["r_squared"]
    return (
        f"{name}: fit vs n = {n_fit['empirical_label']} [{n_status}], "
        f"fit vs {term_label} = R^2={r2:.2f} [{term_status}]"
    )


def _run_case(
    name: str,
    algorithm_fn: Callable[..., Any],
    graph_generator: Callable[[int], Graph],
    graph_sizes: list[int],
    claimed: str,
    candidates: list[str],
    repetitions: int = 3,
    *,
    show_median: bool = False,
    instrument_flow: bool = False,
) -> dict[str, Any]:
    print(f"\n=== Benchmarking {name} ===")
    print(f"sizes={graph_sizes}, repetitions={repetitions}, claimed={claimed}")
    points = run_benchmark(
        algorithm_fn,
        graph_sizes,
        graph_generator,
        repetitions=repetitions,
        retain_graphs=instrument_flow,
    )

    flow_notes: list[dict[str, Any]] = []
    if instrument_flow:
        print(
            "  note: O(V*E^2) is a worst-case Edmonds–Karp bound; random "
            "sparse graphs rarely approach it."
        )
        print(
            "  augmenting paths found vs theoretical worst-case O(V*E) "
            "augmentations:"
        )
        for row in points:
            g = row["graph"]
            v = int(g.num_nodes)
            e = int(g.num_edges)
            paths = _count_augmenting_paths(g)
            worst = v * e
            note = {
                "size": v,
                "num_edges": e,
                "augmenting_paths": paths,
                "worst_case_VE": worst,
                "fraction_of_worst_case": (paths / worst) if worst else 0.0,
            }
            flow_notes.append(note)
            print(
                f"    n={v:>4d}  E={e:>5d}  paths={paths:>4d}  "
                f"worst-case V*E={worst:>8d}  "
                f"({note['fraction_of_worst_case']:.4%} of bound)"
            )
            # Drop non-JSON-serializable graph handle before saving results.
            del row["graph"]

    for row in points:
        print(_format_point_line(row, show_median=show_median))

    sizes = [p["size"] for p in points]
    times = [p["mean_time"] for p in points]
    edges = [p["num_edges"] for p in points]

    fit = fit_complexity_curve(sizes, times, candidates, edges=edges)
    claim = evaluate_claim(fit, claimed)

    term_fit: dict[str, Any] | None = None
    report_line: str
    if name in GRAPH_TERM_REPORT_ALGOS:
        term_fit = fit_against_graph_terms(
            sizes, edges, times, graph_term_fn(claimed)
        )
        report_line = _side_by_side_report(name, claimed, fit, term_fit)
        print(f"  -> {report_line}")
        if name == "ford_fulkerson":
            print(
                "  -> explanation: claimed O(V*E^2) is worst-case; on these "
                "sparse random digraphs the number of augmenting paths is "
                "far below V*E, so wall-clock growth need not track V*E^2."
            )
    else:
        status = "MATCH" if claim["match"] else "MISMATCH"
        report_line = (
            f"{name}: empirical fit = {fit['empirical_label']}, "
            f"best model = {fit['best_fit']}, claimed {claimed} -- {status}"
        )
        print(f"  -> {report_line}")

    plot_path = _save_plot(name, points, fit, claimed)
    print(f"  plot: {plot_path}")

    result: dict[str, Any] = {
        "name": name,
        "claimed": claimed,
        "candidates": candidates,
        "sizes": graph_sizes,
        "points": points,
        "fit": fit,
        "claim": claim,
        "report": report_line,
        "plot": str(plot_path.name),
    }
    if term_fit is not None:
        result["graph_term_fit"] = term_fit
    if flow_notes:
        result["flow_augmentation_notes"] = flow_notes
        result["flow_bound_comment"] = (
            "O(V*E^2) is a worst-case bound; random sparse graphs rarely "
            "approach it. Compare augmenting_paths to worst_case_VE (= V*E)."
        )
    return result


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    default_sizes = [50, 100, 200, 400, 800, 1600]
    # Edmonds–Karp is O(V E^2); keep graphs smaller / sparser.
    flow_sizes = [40, 60, 80, 100, 140, 180]
    # PageRank iterates over edges many times; drop the largest size slightly.
    pagerank_sizes = [50, 100, 200, 400, 800, 1200]

    linearish = ["O(n)", "O(V+E)", "O(n log n)", "O(E log V)", "O(n^2)"]
    heapish = ["O(n)", "O(V+E)", "O(E log V)", "O(E log E)", "O(n log n)", "O(n^2)"]
    flowish = ["O(V+E)", "O(E log V)", "O(n^2)", "O(V E^2)", "O(n log n)"]
    pr_cands = ["O(n)", "O(V+E)", "O(k(V+E))", "O(n log n)", "O(n^2)"]

    cases: list[dict[str, Any]] = []

    cases.append(
        _run_case(
            "bfs",
            _wrap_bfs,
            gen_undirected,
            default_sizes,
            claimed="O(V+E)",
            candidates=linearish,
        )
    )
    cases.append(
        _run_case(
            "dijkstra",
            _wrap_dijkstra,
            gen_weighted_undirected,
            default_sizes,
            claimed="O(E log V)",
            candidates=heapish,
            repetitions=5,
            show_median=True,
        )
    )
    cases.append(
        _run_case(
            "kruskals",
            kruskals,
            gen_connected_weighted,
            default_sizes,
            claimed="O(E log E)",
            candidates=heapish,
        )
    )
    cases.append(
        _run_case(
            "prims",
            prims,
            gen_connected_weighted,
            default_sizes,
            claimed="O(E log V)",
            candidates=heapish,
        )
    )
    cases.append(
        _run_case(
            "ford_fulkerson",
            _wrap_ford,
            gen_directed_flow,
            flow_sizes,
            claimed="O(V E^2)",
            candidates=flowish,
            repetitions=2,
            instrument_flow=True,
        )
    )
    cases.append(
        _run_case(
            "pagerank",
            _wrap_pagerank,
            gen_directed,
            pagerank_sizes,
            claimed="O(k(V+E))",
            candidates=pr_cands,
        )
    )

    # Kruskal vs Prim head-to-head summary on identical sizes.
    print("\n=== Kruskal vs Prim (mean times) ===")
    k = next(c for c in cases if c["name"] == "kruskals")
    p = next(c for c in cases if c["name"] == "prims")
    comparison = []
    for kp, pp in zip(k["points"], p["points"]):
        row = {
            "size": kp["size"],
            "kruskals_ms": kp["mean_time"] * 1000,
            "prims_ms": pp["mean_time"] * 1000,
            "faster": "kruskals" if kp["mean_time"] <= pp["mean_time"] else "prims",
        }
        comparison.append(row)
        print(
            f"  n={row['size']:>5d}  Kruskal={row['kruskals_ms']:8.3f} ms  "
            f"Prim={row['prims_ms']:8.3f} ms  faster={row['faster']}"
        )

    payload = {
        "suite": "graph-theory-toolkit-benchmarks",
        "results": cases,
        "kruskal_vs_prim": comparison,
        "reports": [c["report"] for c in cases],
    }

    json_path = RESULTS_DIR / "benchmark_results.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\n========== REPORT ==========")
    for line in payload["reports"]:
        print(line)
    print(f"\nJSON saved to {json_path}")
    print(f"PNGs saved under {RESULTS_DIR}")


if __name__ == "__main__":
    main()
