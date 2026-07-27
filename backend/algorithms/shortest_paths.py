"""Single-source and all-pairs shortest-path algorithms.

All algorithms operate solely on ``graph_core.Graph``. NetworkX is never used
for solving — only for validation in tests via ``Graph.to_networkx()``.
"""

from __future__ import annotations

import math
from heapq import heappop, heappush
from typing import Any, Callable, Hashable, Optional

from graph_core.graph import Graph


def reconstruct_path(
    predecessors: dict[Hashable, Hashable | None],
    start: Hashable,
    end: Hashable,
) -> list[Hashable]:
    """Rebuild a path from ``start`` to ``end`` using a predecessor map.

    Works with the predecessor dictionaries produced by ``dijkstra``,
    ``bellman_ford``, and ``a_star``.

    Raises:
        ValueError: If ``end`` is unreachable from ``start``.
    """
    if end != start and end not in predecessors:
        raise ValueError(f"No path from {start!r} to {end!r}")

    path: list[Hashable] = [end]
    while path[-1] != start:
        pred = predecessors.get(path[-1])
        if pred is None:
            raise ValueError(f"No path from {start!r} to {end!r}")
        path.append(pred)
    path.reverse()
    return path


def euclidean_heuristic(
    graph: Graph,
    goal: Hashable,
) -> Callable[[Hashable], float]:
    """Build a Euclidean heuristic ``h(n)`` toward ``goal``.

    Nodes are expected to store coordinates as attributes ``x`` and ``y``,
    or a single ``pos`` / ``coords`` attribute holding ``(x, y)``.
    """
    goal_x, goal_y = _node_coords(graph, goal)

    def heuristic(node: Hashable) -> float:
        x, y = _node_coords(graph, node)
        return math.hypot(x - goal_x, y - goal_y)

    return heuristic


def dijkstra(
    graph: Graph,
    start: Hashable,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> tuple[dict[Hashable, float], dict[Hashable, Hashable | None]]:
    """Single-source shortest paths via a binary min-heap.

    Approach: Maintain a min-heap of tentative distances; repeatedly settle
    the unsettled node with the smallest distance and relax its outgoing
    edges (classic Dijkstra with ``heapq``).

    Time complexity: O((V + E) log V) — each node is inserted/decreased in
    the binary heap O(log V) times in the worst case and each edge triggers
    at most one heap push, giving O(E log V) with the common lazy-decrease
    implementation used here.

    Space complexity: O(V + E) — distance/predecessor maps are O(V); the
    heap may hold O(E) pending entries under lazy updates.

    Requires: non-negative edge weights. Undirected edges are treated as
    bidirectional with the stored weight.

    Returns:
        ``(distances, predecessors)`` for nodes reachable from ``start``.
    """
    _ensure_node(graph, start)
    _ensure_non_negative(graph)

    distances: dict[Hashable, float] = {start: 0.0}
    predecessors: dict[Hashable, Hashable | None] = {start: None}
    heap: list[tuple[float, Hashable]] = [(0.0, start)]
    settled: set[Hashable] = set()

    while heap:
        dist_u, u = heappop(heap)
        if u in settled:
            continue
        settled.add(u)
        if record_steps is not None:
            record_steps.append(
                {"action": "settle", "node": u, "distance": dist_u}
            )

        for v, weight in graph.get_neighbors(u).items():
            if v in settled:
                continue
            candidate = dist_u + weight
            if candidate < distances.get(v, math.inf):
                distances[v] = candidate
                predecessors[v] = u
                heappush(heap, (candidate, v))
                if record_steps is not None:
                    record_steps.append(
                        {
                            "action": "relax",
                            "from": u,
                            "to": v,
                            "distance": candidate,
                        }
                    )

    return distances, predecessors


def bellman_ford(
    graph: Graph,
    start: Hashable,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> tuple[dict[Hashable, float], dict[Hashable, Hashable | None]]:
    """Single-source shortest paths with support for negative weights.

    Approach: Initialize ``dist[start] = 0`` and relax every edge ``|V| - 1``
    times (Bellman–Ford). A further successful relaxation proves a
    negative-weight cycle reachable from ``start``.

    Time complexity: O(V · E) — ``|V| - 1`` full passes over all edges, plus
    one detection pass.

    Space complexity: O(V) — distance and predecessor maps.

    Requires: no negative-weight cycle reachable from ``start``. Works with
    negative edge weights otherwise. Undirected edges are expanded to both
    directions for relaxation.

    Returns:
        ``(distances, predecessors)`` for nodes reachable from ``start``.

    Raises:
        ValueError: If a negative-weight cycle is detected.
    """
    _ensure_node(graph, start)
    nodes = graph.get_nodes()
    edges = _oriented_edges(graph)

    distances: dict[Hashable, float] = {n: math.inf for n in nodes}
    distances[start] = 0.0
    predecessors: dict[Hashable, Hashable | None] = {start: None}

    for iteration in range(max(len(nodes) - 1, 0)):
        updated = False
        for u, v, weight in edges:
            if distances[u] == math.inf:
                continue
            candidate = distances[u] + weight
            if candidate < distances[v]:
                distances[v] = candidate
                predecessors[v] = u
                updated = True
                if record_steps is not None:
                    record_steps.append(
                        {
                            "action": "relax",
                            "iteration": iteration,
                            "from": u,
                            "to": v,
                            "distance": candidate,
                        }
                    )
        if not updated:
            break

    for u, v, weight in edges:
        if distances[u] == math.inf:
            continue
        if distances[u] + weight < distances[v]:
            raise ValueError("Graph contains a negative-weight cycle")

    reachable = {
        n: d for n, d in distances.items() if d != math.inf
    }
    preds = {
        n: predecessors[n]
        for n in reachable
        if n in predecessors
    }
    return reachable, preds


def floyd_warshall(
    graph: Graph,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> dict[Hashable, dict[Hashable, float]]:
    """All-pairs shortest paths via dynamic programming.

    Approach: Initialize a dense distance matrix from direct edges, then for
    every intermediate vertex ``k`` try improving ``i → j`` through ``k``
    (Floyd–Warshall). A negative diagonal entry signals a negative cycle.

    Time complexity: O(V³) — three nested loops over the vertex set;
    independent of ``|E|`` once the matrix is built.

    Space complexity: O(V²) — the dense distance matrix.

    Requires: no negative-weight cycles. Supports negative edge weights.
    Undirected edges are stored symmetrically in the matrix.

    Returns:
        ``dist`` where ``dist[u][v]`` is the shortest-path distance (or
        ``math.inf`` if unreachable).

    Raises:
        ValueError: If a negative-weight cycle is detected.
    """
    nodes = graph.get_nodes()
    dist: dict[Hashable, dict[Hashable, float]] = {
        u: {v: (0.0 if u == v else math.inf) for v in nodes} for u in nodes
    }

    for u, v, weight in _oriented_edges(graph):
        if weight < dist[u][v]:
            dist[u][v] = weight

    for k in nodes:
        for i in nodes:
            dik = dist[i][k]
            if dik == math.inf:
                continue
            for j in nodes:
                candidate = dik + dist[k][j]
                if candidate < dist[i][j]:
                    dist[i][j] = candidate
                    if record_steps is not None:
                        record_steps.append(
                            {
                                "action": "update",
                                "i": i,
                                "j": j,
                                "via": k,
                                "distance": candidate,
                            }
                        )

    for v in nodes:
        if dist[v][v] < 0:
            raise ValueError("Graph contains a negative-weight cycle")

    return dist


def a_star(
    graph: Graph,
    start: Hashable,
    goal: Hashable,
    heuristic_fn: Callable[[Hashable], float],
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> tuple[dict[Hashable, float], dict[Hashable, Hashable | None]]:
    """A* point-to-point shortest path with an admissible heuristic.

    Approach: Best-first search ordered by ``f(n) = g(n) + h(n)``, where
    ``g`` is the path cost from ``start`` and ``h`` estimates remaining cost
    to ``goal``. Settling ``goal`` yields an optimal path when ``h`` is
    admissible (and consistent for the usual early-stop guarantee).

    Time complexity: O((V + E) log V) in the worst case (same heap bound as
    Dijkstra); with a strong heuristic the explored subgraph is typically
    much smaller than V.

    Space complexity: O(V) — open-set heap plus g-score / predecessor maps.

    Requires: non-negative edge weights and an admissible heuristic
    (``h(n) ≤`` true remaining cost). Undirected edges are bidirectional.

    Returns:
        ``(distances, predecessors)`` for nodes reached during the search
        (always includes ``start``; includes ``goal`` when reachable).
    """
    _ensure_node(graph, start)
    _ensure_node(graph, goal)
    _ensure_non_negative(graph)

    g_score: dict[Hashable, float] = {start: 0.0}
    predecessors: dict[Hashable, Hashable | None] = {start: None}
    open_heap: list[tuple[float, float, Hashable]] = [
        (heuristic_fn(start), 0.0, start)
    ]
    settled: set[Hashable] = set()

    while open_heap:
        f_u, dist_u, u = heappop(open_heap)
        if u in settled:
            continue
        settled.add(u)
        if record_steps is not None:
            record_steps.append(
                {
                    "action": "settle",
                    "node": u,
                    "distance": dist_u,
                    "f": f_u,
                }
            )

        if u == goal:
            break

        for v, weight in graph.get_neighbors(u).items():
            if v in settled:
                continue
            candidate = dist_u + weight
            if candidate < g_score.get(v, math.inf):
                g_score[v] = candidate
                predecessors[v] = u
                f_v = candidate + heuristic_fn(v)
                heappush(open_heap, (f_v, candidate, v))
                if record_steps is not None:
                    record_steps.append(
                        {
                            "action": "relax",
                            "from": u,
                            "to": v,
                            "distance": candidate,
                            "f": f_v,
                        }
                    )

    return g_score, predecessors


def johnsons(
    graph: Graph,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> dict[Hashable, dict[Hashable, float]]:
    """All-pairs shortest paths for sparse graphs (Johnson's algorithm).

    Approach: Add a virtual source ``s`` with zero-weight edges to every
    vertex; run Bellman–Ford from ``s`` to obtain potentials ``h(v)``;
    reweight each edge to ``w'(u,v) = w(u,v) + h(u) - h(v)`` (non-negative
    when no negative cycle exists); run Dijkstra from every vertex on the
    reweighted graph; convert distances back via
    ``d(u,v) = d'(u,v) - h(u) + h(v)``.

    Time complexity: O(V · E + V² log V) with binary-heap Dijkstra —
    one Bellman–Ford in O(V E) plus V Dijkstra runs each O((V + E) log V).
    Preferable to Floyd–Warshall when ``E ≪ V²``.

    Space complexity: O(V²) — the returned distance matrix dominates;
    auxiliary reweighted graph and potentials are O(V + E).

    Requires: no negative-weight cycles; negative edges are allowed.
    Undirected inputs are expanded to bidirectional digraphs internally.

    Returns:
        Distance matrix ``dist[u][v]`` (``math.inf`` if unreachable), same
        format as ``floyd_warshall``.

    Raises:
        ValueError: If a negative-weight cycle is detected.
    """
    nodes = graph.get_nodes()
    if not nodes:
        return {}

    # Directed working copy (bidirect undirected edges).
    work = Graph(directed=True, weighted=True)
    for n in nodes:
        work.add_node(n)
    for u, v, weight in _oriented_edges(graph):
        work.add_edge(u, v, weight)

    source = object()
    work.add_node(source)
    for n in nodes:
        work.add_edge(source, n, 0.0)

    if record_steps is not None:
        record_steps.append({"action": "potentials_start", "source": "virtual"})

    try:
        h, _ = bellman_ford(work, source)
    except ValueError as exc:
        raise ValueError("Graph contains a negative-weight cycle") from exc

    # Drop the virtual source from potentials.
    h = {n: h[n] for n in nodes}

    if record_steps is not None:
        record_steps.append(
            {
                "action": "potentials",
                "h": {str(k): v for k, v in h.items()},
            }
        )

    reweighted = Graph(directed=True, weighted=True)
    for n in nodes:
        reweighted.add_node(n)
    for u, v, weight in work.get_edges():
        if u is source or v is source:
            continue
        new_w = weight + h[u] - h[v]
        # Clamp tiny negatives from floating-point error.
        if new_w < 0:
            if new_w < -1e-9:
                raise ValueError("Graph contains a negative-weight cycle")
            new_w = 0.0
        reweighted.add_edge(u, v, new_w)

    dist: dict[Hashable, dict[Hashable, float]] = {
        u: {v: math.inf for v in nodes} for u in nodes
    }
    for u in nodes:
        dist[u][u] = 0.0

    for u in nodes:
        d_prime, _ = dijkstra(reweighted, u)
        for v, d_uv in d_prime.items():
            dist[u][v] = d_uv - h[u] + h[v]
        if record_steps is not None:
            record_steps.append(
                {
                    "action": "dijkstra_source",
                    "source": u,
                    "reachable": len(d_prime),
                }
            )

    for v in nodes:
        if dist[v][v] < -1e-9:
            raise ValueError("Graph contains a negative-weight cycle")

    return dist


def _ensure_node(graph: Graph, node: Hashable) -> None:
    if node not in graph.get_nodes():
        raise ValueError(f"node {node!r} is not in the graph")


def _ensure_non_negative(graph: Graph) -> None:
    for _, _, weight in graph.get_edges():
        if weight < 0:
            raise ValueError(
                "algorithm requires non-negative edge weights"
            )


def _oriented_edges(
    graph: Graph,
) -> list[tuple[Hashable, Hashable, float]]:
    """Edge list with undirected edges expanded to both directions."""
    edges = list(graph.get_edges())
    if graph.directed:
        return edges
    both: list[tuple[Hashable, Hashable, float]] = []
    for u, v, weight in edges:
        both.append((u, v, weight))
        both.append((v, u, weight))
    return both


def _node_coords(graph: Graph, node: Hashable) -> tuple[float, float]:
    attrs = graph.get_node_attrs(node)
    if "x" in attrs and "y" in attrs:
        return float(attrs["x"]), float(attrs["y"])
    for key in ("pos", "coords", "xy"):
        if key in attrs:
            pos = attrs[key]
            return float(pos[0]), float(pos[1])
    raise ValueError(
        f"node {node!r} has no coordinates (expected x/y or pos attributes)"
    )
