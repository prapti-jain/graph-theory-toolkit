"""Empirical runtime benchmarking and asymptotic complexity curve fitting.

Empirical validation methodology
--------------------------------
Algorithm docstrings claim asymptotic bounds such as O(V + E) or O(E log V).
Those claims are statements about how *leading-term* cost grows with input
size; wall-clock measurements on finite machines include constant factors,
cache effects, interpreter overhead, and noise. To check whether an
implementation's observed growth is *consistent* with a claimed class, we:

1. Time the algorithm on a geometric sequence of graph sizes.
2. Fit each candidate complexity model ``T(n) ≈ a · f(n)`` (and, when edges
   matter, ``f(n, m)``) by least squares, comparing residuals.
3. Separately fit a log–log model ``log T ≈ b · log n + c``. On a log–log
   plot, polynomials ``T = Θ(n^k)`` appear as straight lines with slope ``k``,
   so the estimated exponent ``b`` distinguishes linear, n log n, quadratic,
   etc. growth more clearly than linear-scale plots.
4. Prefer ``fit_against_graph_terms`` for graph algorithms: compute the
   claimed term from recorded ``(V, E)`` (e.g. ``E log₂ V``) and report the
   R² of a linear regression of time vs that term. Pure power-of-n fits are
   often misleading when ``E`` is not Θ(``n²``).

Limitations: this is an approximation, not a proof. Constant factors can
dominate at modest ``n``; hardware and Python runtime variance add noise;
and for sparse graphs ``E = Θ(V)`` many distinct classes (O(V), O(V+E),
O(E log V)) look empirically similar. Treat a ``MATCH`` as supporting
evidence for the docstring claim, not a formal verification. Worst-case
bounds such as O(V E²) for Edmonds–Karp are rarely approached on random
sparse instances.
"""

from __future__ import annotations

import math
import statistics
import time
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np

try:
    from scipy.optimize import curve_fit
except ImportError:  # pragma: no cover
    curve_fit = None


ComplexityFn = Callable[[np.ndarray, np.ndarray, float], np.ndarray]


def run_benchmark(
    algorithm_fn: Callable[..., Any],
    graph_sizes: Sequence[int],
    graph_generator: Callable[[int], Any],
    repetitions: int = 3,
    *,
    retain_graphs: bool = False,
    **algo_kwargs: Any,
) -> list[dict[str, Any]]:
    """Time ``algorithm_fn`` across increasing graph sizes.

    For each size, builds one graph with ``graph_generator(size)``, runs the
    algorithm ``repetitions`` times with ``time.perf_counter()``, and records
    mean / median / std runtime plus edge count.

    ``algorithm_fn`` is called as ``algorithm_fn(graph, **algo_kwargs)``.
    Wrappers in the suite supply source/sink/start when needed.

    If ``retain_graphs`` is True, each result dict includes the timed
    ``graph`` object (for post-hoc instrumentation such as counting
    augmenting paths).
    """
    if repetitions < 1:
        raise ValueError("repetitions must be >= 1")

    results: list[dict[str, Any]] = []
    for size in graph_sizes:
        graph = graph_generator(int(size))
        samples: list[float] = []
        for _ in range(repetitions):
            start = time.perf_counter()
            algorithm_fn(graph, **algo_kwargs)
            samples.append(time.perf_counter() - start)

        mean_time = statistics.fmean(samples)
        median_time = float(statistics.median(samples))
        std_time = statistics.pstdev(samples) if len(samples) > 1 else 0.0
        num_edges = int(getattr(graph, "num_edges", 0))
        high_variance = bool(mean_time > 0 and std_time > 0.30 * mean_time)
        row: dict[str, Any] = {
            "size": int(size),
            "mean_time": mean_time,
            "median_time": median_time,
            "std_time": std_time,
            "num_edges": num_edges,
            "high_variance": high_variance,
            "samples": list(samples),
        }
        if retain_graphs:
            row["graph"] = graph
        results.append(row)
    return results


def fit_complexity_curve(
    sizes: Sequence[float],
    times: Sequence[float],
    candidate_complexities: Sequence[str],
    edges: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Fit empirical (size, time) data to theoretical complexity models.

    Each candidate name maps to a one-parameter model ``T ≈ a · f(n[, m])``.
    Models are fit with ``scipy.optimize.curve_fit`` when available, otherwise
    a closed-form least-squares scale factor. The candidate with the lowest
    sum of squared residuals is reported as the best fit.

    A log–log regression ``log T = b log n + c`` is also computed; the slope
    ``b`` is the empirical polynomial exponent used in suite reports
    (``O(n^b)``).
    """
    n = np.asarray(sizes, dtype=float)
    t = np.asarray(times, dtype=float)
    if edges is None:
        m = n.copy()
    else:
        m = np.asarray(edges, dtype=float)

    if len(n) < 2:
        raise ValueError("need at least two sizes to fit a complexity curve")
    if np.any(t <= 0) or np.any(n <= 0):
        raise ValueError("sizes and times must be positive for fitting")

    catalog = _complexity_catalog()
    fits: dict[str, dict[str, Any]] = {}

    for name in candidate_complexities:
        if name not in catalog:
            raise ValueError(f"unknown complexity candidate: {name!r}")
        model = catalog[name]
        param, residual = _fit_scale(model, n, m, t)
        fits[name] = {
            "param": float(param),
            "residual": float(residual),
            "rmse": float(math.sqrt(residual / len(t))),
        }

    best_fit = min(fits.keys(), key=lambda k: fits[k]["residual"])
    exponent, intercept = _loglog_exponent(n, t)

    return {
        "best_fit": best_fit,
        "best_residual": fits[best_fit]["residual"],
        "fits": fits,
        "empirical_exponent": float(exponent),
        "loglog_intercept": float(intercept),
        "empirical_label": f"O(n^{exponent:.2f})",
    }


TermFn = Callable[[float, float], float]


def graph_term_fn(complexity_name: str) -> TermFn:
    """Return ``term(V, E)`` for a named asymptotic class (no scale factor)."""
    catalog = _graph_term_catalog()
    if complexity_name not in catalog:
        raise ValueError(f"no graph-term function for {complexity_name!r}")
    return catalog[complexity_name]


def fit_against_graph_terms(
    sizes: Sequence[float],
    edges_list: Sequence[float],
    times: Sequence[float],
    term_fn: TermFn,
) -> dict[str, Any]:
    """Linear-regress runtime against a theoretical graph complexity term.

    For each data point ``i``, compute ``x_i = term_fn(V_i, E_i)`` using the
    recorded node and edge counts (not a pure power of ``n``). Then fit
    ``T ≈ a + b · x`` by ordinary least squares and report ``R²`` as the
    match score: high ``R²`` means observed time scales linearly with the
    claimed term (e.g. ``E log₂ V`` for Dijkstra).
    """
    n = np.asarray(sizes, dtype=float)
    m = np.asarray(edges_list, dtype=float)
    t = np.asarray(times, dtype=float)

    if len(n) < 2:
        raise ValueError("need at least two sizes to fit against graph terms")
    if len(n) != len(m) or len(n) != len(t):
        raise ValueError("sizes, edges_list, and times must have equal length")
    if np.any(t <= 0) or np.any(n <= 0):
        raise ValueError("sizes and times must be positive for fitting")

    terms = [
        float(term_fn(float(vi), float(ei))) for vi, ei in zip(n, m)
    ]
    return fit_time_vs_term_values(terms, times)


def fit_time_vs_term_values(
    terms: Sequence[float],
    times: Sequence[float],
) -> dict[str, Any]:
    """Linear-regress runtime against precomputed term values ``x_i``.

    Used both for theoretical terms (``E log V``, ``V E²``, …) and for
    observed terms such as ``paths_found · E`` for Edmonds–Karp, where the
    path count is measured per run rather than taken from a worst-case bound.
    """
    x = np.asarray(terms, dtype=float)
    t = np.asarray(times, dtype=float)

    if len(x) < 2:
        raise ValueError("need at least two points to fit time vs term")
    if len(x) != len(t):
        raise ValueError("terms and times must have equal length")
    if np.any(t <= 0):
        raise ValueError("times must be positive for fitting")
    if np.any(~np.isfinite(x)) or np.any(x < 0):
        raise ValueError("terms must be finite and non-negative")

    # Degenerate: constant term → cannot regress.
    if float(np.std(x)) <= 0:
        return {
            "terms": x.tolist(),
            "slope": 0.0,
            "intercept": float(np.mean(t)),
            "r_squared": 0.0,
            "residual": float(np.sum((t - np.mean(t)) ** 2)),
            "match": False,
        }

    slope, intercept = np.polyfit(x, t, 1)
    pred = intercept + slope * x
    ss_res = float(np.sum((t - pred) ** 2))
    ss_tot = float(np.sum((t - np.mean(t)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    r2 = max(0.0, min(1.0, r2))

    return {
        "terms": x.tolist(),
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r2),
        "residual": ss_res,
        "match": bool(r2 >= 0.90),
    }


def _graph_term_catalog() -> dict[str, TermFn]:
    def t_n(v: float, e: float) -> float:
        return v

    def t_n_log_n(v: float, e: float) -> float:
        return v * math.log2(max(v, 2.0))

    def t_n2(v: float, e: float) -> float:
        return v * v

    def t_v_plus_e(v: float, e: float) -> float:
        return v + e

    def t_e_log_v(v: float, e: float) -> float:
        return e * math.log2(max(v, 2.0))

    def t_e_log_e(v: float, e: float) -> float:
        return e * math.log2(max(e, 2.0))

    def t_v_e2(v: float, e: float) -> float:
        return v * (e * e)

    def t_k_v_plus_e(v: float, e: float) -> float:
        return v + e

    return {
        "O(n)": t_n,
        "O(n log n)": t_n_log_n,
        "O(n^2)": t_n2,
        "O(V+E)": t_v_plus_e,
        "O(E log V)": t_e_log_v,
        "O(E log E)": t_e_log_e,
        "O(V E^2)": t_v_e2,
        "O(k(V+E))": t_k_v_plus_e,
    }


def evaluate_claim(
    fit_result: dict[str, Any],
    claimed: str,
    residual_slack: float = 1.75,
) -> dict[str, Any]:
    """Decide whether the claimed complexity is consistent with the fit.

    A claim ``MATCH``es when it achieves the best residual, or a residual
    within ``residual_slack``× of the best (allowing near-ties between
    similar sparse-graph classes such as O(V+E) and O(E log V)).
    """
    fits = fit_result["fits"]
    if claimed not in fits:
        return {
            "claimed": claimed,
            "match": False,
            "reason": f"claimed {claimed!r} was not among fitted candidates",
        }

    best_residual = fit_result["best_residual"]
    claimed_residual = fits[claimed]["residual"]
    match = claimed_residual <= best_residual * residual_slack
    return {
        "claimed": claimed,
        "match": match,
        "best_fit": fit_result["best_fit"],
        "empirical_label": fit_result["empirical_label"],
        "claimed_residual": claimed_residual,
        "best_residual": best_residual,
    }


def predict_curve(
    sizes: Sequence[float],
    edges: Sequence[float],
    complexity_name: str,
    param: float,
) -> list[float]:
    """Evaluate a fitted complexity model at the given sizes."""
    catalog = _complexity_catalog()
    model = catalog[complexity_name]
    n = np.asarray(sizes, dtype=float)
    m = np.asarray(edges, dtype=float)
    return model(n, m, param).tolist()


def _complexity_catalog() -> dict[str, ComplexityFn]:
    def o_n(n: np.ndarray, m: np.ndarray, a: float) -> np.ndarray:
        return a * n

    def o_n_log_n(n: np.ndarray, m: np.ndarray, a: float) -> np.ndarray:
        return a * n * np.log(np.maximum(n, 2.0))

    def o_n2(n: np.ndarray, m: np.ndarray, a: float) -> np.ndarray:
        return a * n * n

    def o_v_plus_e(n: np.ndarray, m: np.ndarray, a: float) -> np.ndarray:
        return a * (n + m)

    def o_e_log_v(n: np.ndarray, m: np.ndarray, a: float) -> np.ndarray:
        return a * m * np.log(np.maximum(n, 2.0))

    def o_e_log_e(n: np.ndarray, m: np.ndarray, a: float) -> np.ndarray:
        return a * m * np.log(np.maximum(m, 2.0))

    def o_v_e2(n: np.ndarray, m: np.ndarray, a: float) -> np.ndarray:
        return a * n * (m * m)

    def o_k_v_plus_e(n: np.ndarray, m: np.ndarray, a: float) -> np.ndarray:
        # PageRank: k iterations × O(V+E); k treated as absorbed in ``a``.
        return a * (n + m)

    return {
        "O(n)": o_n,
        "O(n log n)": o_n_log_n,
        "O(n^2)": o_n2,
        "O(V+E)": o_v_plus_e,
        "O(E log V)": o_e_log_v,
        "O(E log E)": o_e_log_e,
        "O(V E^2)": o_v_e2,
        "O(k(V+E))": o_k_v_plus_e,
    }


def _fit_scale(
    model: ComplexityFn,
    n: np.ndarray,
    m: np.ndarray,
    t: np.ndarray,
) -> tuple[float, float]:
    """Fit scale ``a`` in ``T ≈ a · f(n, m)``; return ``(a, sse)``."""

    def wrapped(xdata: np.ndarray, a: float) -> np.ndarray:
        # xdata unused; n, m closed over — curve_fit needs (x, *params).
        return model(n, m, a)

    # Closed-form LS: a* = (f·t) / (f·f)
    f = model(n, m, 1.0)
    denom = float(np.dot(f, f))
    if denom <= 0:
        return 0.0, float(np.sum(t * t))
    a0 = float(np.dot(f, t) / denom)

    if curve_fit is not None:
        try:
            popt, _ = curve_fit(
                wrapped,
                n,
                t,
                p0=(max(a0, 1e-18),),
                bounds=(0.0, np.inf),
                maxfev=5000,
            )
            a = float(popt[0])
        except Exception:
            a = max(a0, 0.0)
    else:
        a = max(a0, 0.0)

    pred = model(n, m, a)
    residual = float(np.sum((t - pred) ** 2))
    return a, residual


def _loglog_exponent(n: np.ndarray, t: np.ndarray) -> tuple[float, float]:
    """Ordinary least squares on ``log t = b log n + c``."""
    log_n = np.log(n)
    log_t = np.log(t)
    b, c = np.polyfit(log_n, log_t, 1)
    return float(b), float(c)
