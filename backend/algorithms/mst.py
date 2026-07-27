"""Minimum spanning tree algorithms (Kruskal and Prim).

All algorithms operate solely on ``graph_core.Graph``. NetworkX is never used
for solving — only for validation in tests via ``Graph.to_networkx()``.
"""

from __future__ import annotations

import time
from heapq import heappop, heappush
from typing import Any, Hashable, Optional

from algorithms.union_find import UnionFind
from graph_core.graph import Graph

Edge = tuple[Hashable, Hashable, float]
MSTResult = tuple[list[Edge], float]


def kruskals(
    graph: Graph,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> MSTResult:
    """Compute an MST with Kruskal's algorithm and Union–Find.

    Approach: Sort all edges by increasing weight, then greedily add an edge
    when its endpoints lie in different components (Union–Find detects and
    merges those components). The first ``|V| - 1`` accepted edges form an MST
    when the graph is connected.

    Time complexity: O(E log E) — dominated by sorting the edge list.
    Subsequent Union–Find work is O(E · α(V)), which is effectively linear
    and does not change the leading term. (Equivalently O(E log V) since
    ``log E = O(log V²) = O(log V)``.)

    Space complexity: O(V + E) — Union–Find parents/ranks are O(V); the
    sorted edge list and MST edge list are O(E).

    Prefer Kruskal's when the graph is sparse (``E ≈ V``) or when edges are
    already available as an explicit list to sort. Prefer Prim's for dense
    graphs when an adjacency-matrix / binary-heap cut representation makes
    the O(E log V) bound attractive relative to sorting a huge edge list.

    Requires: undirected, connected graph (weights may be any real numbers).

    Returns:
        ``(mst_edges, total_weight)`` where each edge is ``(u, v, weight)``.

    Raises:
        ValueError: If the graph is directed or disconnected.
    """
    if graph.directed:
        raise ValueError("MST algorithms require an undirected graph")

    nodes = graph.get_nodes()
    n = len(nodes)
    if n == 0:
        return [], 0.0

    edges = sorted(graph.get_edges(), key=lambda e: e[2])
    uf = UnionFind(nodes)
    mst: list[Edge] = []
    total = 0.0

    for u, v, weight in edges:
        if record_steps is not None:
            record_steps.append(
                {
                    "action": "consider",
                    "edge": [u, v],
                    "weight": weight,
                }
            )
        if uf.union(u, v):
            mst.append((u, v, weight))
            total += weight
            if record_steps is not None:
                record_steps.append(
                    {
                        "action": "accept",
                        "edge": [u, v],
                        "weight": weight,
                        "total": total,
                    }
                )
            if len(mst) == n - 1:
                break
        elif record_steps is not None:
            record_steps.append(
                {
                    "action": "reject",
                    "edge": [u, v],
                    "weight": weight,
                    "reason": "cycle",
                }
            )

    if len(mst) != n - 1:
        raise ValueError("Graph is disconnected; no spanning tree exists")

    return mst, total


def prims(
    graph: Graph,
    start: Hashable | None = None,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> MSTResult:
    """Compute an MST with Prim's algorithm and a binary min-heap.

    Approach: Grow a tree from ``start`` (or an arbitrary node) by always
    adding the lightest edge that connects a tree vertex to a non-tree
    vertex. A min-heap stores candidate cut edges; settled vertices are
    never re-expanded.

    Time complexity: O(E log V) with a binary heap — each edge may cause a
    heap push, and each of the O(E) heap operations costs O(log V) (lazy
    decrease-key style, as with Dijkstra).

    Space complexity: O(V + E) — the heap may hold O(E) candidate edges and
    the in-tree set / MST list are O(V).

    Prefer Prim's for dense graphs (``E ≈ V²``), especially with an
    adjacency-matrix formulation where a simpler O(V²) Prim variant avoids
    an explicit edge sort. Prefer Kruskal's for sparse graphs where sorting
    O(E) edges is cheap and Union–Find merges are nearly O(1).

    Requires: undirected, connected graph.

    Returns:
        ``(mst_edges, total_weight)`` where each edge is ``(u, v, weight)``.

    Raises:
        ValueError: If the graph is directed, empty (with a requested start),
            or disconnected.
    """
    if graph.directed:
        raise ValueError("MST algorithms require an undirected graph")

    nodes = graph.get_nodes()
    n = len(nodes)
    if n == 0:
        return [], 0.0

    if start is None:
        start = nodes[0]
    elif start not in graph.get_nodes():
        raise ValueError(f"start node {start!r} is not in the graph")

    in_tree: set[Hashable] = {start}
    mst: list[Edge] = []
    total = 0.0
    heap: list[tuple[float, Hashable, Hashable]] = []

    if record_steps is not None:
        record_steps.append({"action": "start", "node": start})

    for v, weight in graph.get_neighbors(start).items():
        heappush(heap, (weight, start, v))

    while heap and len(in_tree) < n:
        weight, u, v = heappop(heap)
        if v in in_tree:
            if record_steps is not None:
                record_steps.append(
                    {
                        "action": "skip",
                        "edge": [u, v],
                        "weight": weight,
                        "reason": "already_in_tree",
                    }
                )
            continue

        in_tree.add(v)
        mst.append((u, v, weight))
        total += weight
        if record_steps is not None:
            record_steps.append(
                {
                    "action": "add",
                    "edge": [u, v],
                    "weight": weight,
                    "node": v,
                    "total": total,
                }
            )

        for nbr, w in graph.get_neighbors(v).items():
            if nbr not in in_tree:
                heappush(heap, (w, v, nbr))

    if len(in_tree) != n:
        raise ValueError("Graph is disconnected; no spanning tree exists")

    return mst, total


def compare_mst_algorithms(
    graph: Graph,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Run Kruskal's and Prim's and verify they agree on MST weight.

    The total MST weight is unique even when several MSTs exist (e.g. under
    tied edge weights); edge sets may still differ. Wall-clock timings for
    this particular graph size are reported so callers can see which method
    was faster here (not a general complexity claim).
    """
    kruskal_steps: list[dict[str, Any]] = []
    prim_steps: list[dict[str, Any]] = []

    t0 = time.perf_counter()
    kruskal_edges, kruskal_weight = kruskals(graph, record_steps=kruskal_steps)
    t1 = time.perf_counter()
    prim_edges, prim_weight = prims(graph, record_steps=prim_steps)
    t2 = time.perf_counter()

    if abs(kruskal_weight - prim_weight) > 1e-9:
        raise AssertionError(
            f"MST weights differ: Kruskal={kruskal_weight}, Prim={prim_weight}"
        )

    kruskal_ms = (t1 - t0) * 1000.0
    prim_ms = (t2 - t1) * 1000.0
    if kruskal_ms <= prim_ms:
        faster = "kruskals"
        note = (
            f"Kruskal's was faster on this graph "
            f"({kruskal_ms:.3f} ms vs Prim's {prim_ms:.3f} ms; "
            f"|V|={graph.num_nodes}, |E|={graph.num_edges})."
        )
    else:
        faster = "prims"
        note = (
            f"Prim's was faster on this graph "
            f"({prim_ms:.3f} ms vs Kruskal's {kruskal_ms:.3f} ms; "
            f"|V|={graph.num_nodes}, |E|={graph.num_edges})."
        )

    result = {
        "kruskals": {
            "edges": kruskal_edges,
            "total_weight": kruskal_weight,
            "time_ms": kruskal_ms,
            "steps": kruskal_steps,
        },
        "prims": {
            "edges": prim_edges,
            "total_weight": prim_weight,
            "time_ms": prim_ms,
            "steps": prim_steps,
        },
        "total_weight": kruskal_weight,
        "faster": faster,
        "note": note,
    }

    if record_steps is not None:
        record_steps.extend(
            [
                {"action": "compare_kruskals_done", "time_ms": kruskal_ms},
                {"action": "compare_prims_done", "time_ms": prim_ms},
                {"action": "compare_result", "faster": faster, "note": note},
            ]
        )

    return result
