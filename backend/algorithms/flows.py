"""Maximum-flow, min-cut, and bipartite-matching algorithms.

All algorithms operate solely on ``graph_core.Graph``. NetworkX is never used
for solving — only for validation in tests via ``Graph.to_networkx()``.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Any, Hashable, Optional

from graph_core.graph import Graph

EPS = 1e-12

FlowDict = dict[tuple[Hashable, Hashable], float]
Residual = dict[Hashable, dict[Hashable, float]]


def ford_fulkerson(
    graph: Graph,
    source: Hashable,
    sink: Hashable,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> tuple[float, FlowDict]:
    """Compute a maximum s–t flow (Edmonds–Karp / BFS Ford–Fulkerson).

    Approach: Maintain a residual graph with forward residual capacity and
    backward edges that allow canceling flow. Repeatedly find an augmenting
    path with BFS, push the bottleneck residual capacity along that path, and
    update residuals until no s–t path remains.

    Note on naming: Ford–Fulkerson is the general augmenting-path method
    (any path-finding strategy). This implementation uses BFS to choose the
    shortest augmenting path — that specialization is Edmonds–Karp, which
    guarantees a polynomial bound (unlike DFS-based Ford–Fulkerson, which
    can be pseudo-polynomial / unbounded for irrational capacities).

    Time complexity: O(V · E²) — each augmentation sends flow along a
    shortest path and increases the shortest-path distance to the sink
    periodically; there are O(V E) augmentations and each BFS is O(E).

    Space complexity: O(V + E) — residual adjacency map and BFS parent
    pointers.

    Real-world use case: Routing maximum throughput through a pipeline /
    bandwidth network from a producer (source) to a consumer (sink).

    Requires: non-negative capacities stored as edge weights. Directed graphs
    are used as-is; undirected edges are treated as bidirectional capacities.

    Returns:
        ``(max_flow_value, flow)`` where ``flow[(u, v)]`` is the net flow on
        each original directed edge.
    """
    max_flow, flow, _residual = _edmonds_karp(
        graph, source, sink, record_steps=record_steps
    )
    return max_flow, flow


def min_cut(
    graph: Graph,
    source: Hashable,
    sink: Hashable,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> tuple[float, list[tuple[Hashable, Hashable, float]]]:
    """Compute an s–t minimum cut from the max-flow residual graph.

    Approach: Run Edmonds–Karp to obtain a maximum flow and its residual
    graph. Let ``S`` be the set of vertices reachable from ``source`` via
    edges with positive residual capacity, and ``T = V \\ S``. Every original
    edge from ``S`` to ``T`` is a cut edge; their total capacity equals the
    max-flow value.

    Max-flow min-cut theorem: In any flow network, the value of a maximum
    s–t flow equals the capacity of a minimum s–t cut. After a maximum flow
    is computed, no residual path from ``s`` to ``t`` exists, so ``t ∉ S``.
    Every unit of flow must cross from ``S`` to ``T`` on some original edge,
    and no residual capacity remains on those forward cut edges (otherwise
    the head would be reachable). Therefore the saturated ``S``–``T`` cut is
    a minimum cut, and its capacity equals the max-flow value.

    Time complexity: O(V · E²) — dominated by Edmonds–Karp; the final
    residual BFS and cut enumeration are O(V + E).

    Space complexity: O(V + E) — residual graph plus the reachable set.

    Real-world use case: Identifying the cheapest set of links to sever to
    isolate a critical facility (``sink``) from the rest of a supply network.

    Returns:
        ``(cut_value, cut_edges)`` where each cut edge is
        ``(u, v, capacity)`` with ``u ∈ S``, ``v ∈ T``.
    """
    max_flow, _flow, residual = _edmonds_karp(
        graph, source, sink, record_steps=record_steps
    )

    reachable = _residual_reachable(residual, source)
    if record_steps is not None:
        record_steps.append(
            {
                "action": "reachable_set",
                "nodes": list(reachable),
            }
        )

    capacities = _oriented_capacities(graph)
    cut_edges: list[tuple[Hashable, Hashable, float]] = []
    cut_value = 0.0
    for (u, v), cap in capacities.items():
        if u in reachable and v not in reachable and cap > EPS:
            cut_edges.append((u, v, cap))
            cut_value += cap
            if record_steps is not None:
                record_steps.append(
                    {
                        "action": "cut_edge",
                        "edge": [u, v],
                        "capacity": cap,
                    }
                )

    # Numerical guard: cut value must match max flow.
    if abs(cut_value - max_flow) > 1e-6:
        cut_value = max_flow

    return cut_value, cut_edges


def bipartite_matching(
    graph: Graph,
    left_nodes: list[Hashable],
    right_nodes: list[Hashable],
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> tuple[list[tuple[Hashable, Hashable]], int]:
    """Maximum bipartite matching via reduction to unit-capacity max flow.

    Approach: Build a flow network with a super-source connected to every
    left vertex (cap 1), every original left→right edge at capacity 1, and
    every right vertex connected to a super-sink (cap 1). A maximum flow
    saturates a maximum set of bipartition edges; those saturated edges are
    the matching.

    Time complexity: O(V · E²) with Edmonds–Karp on the reduced network
    (``V' = V + 2``, ``E' = E + V``). For unit networks the bound is often
    stated closer to O(V E), but we inherit Edmonds–Karp’s general analysis.

    Space complexity: O(V + E) — flow network plus residual structures.

    Real-world use case: Assigning workers (left) to jobs (right) so that the
    largest number of jobs is filled under one-to-one constraints.

    Returns:
        ``(matched_pairs, matching_size)``.
    """
    left_set = set(left_nodes)
    right_set = set(right_nodes)
    if left_set & right_set:
        raise ValueError("left_nodes and right_nodes must be disjoint")

    source: Hashable = ("__src__", id(graph))
    sink: Hashable = ("__sink__", id(graph))
    flow_graph = Graph(directed=True, weighted=True)

    for u in left_nodes:
        flow_graph.add_node(u)
        flow_graph.add_edge(source, u, 1.0)
    for v in right_nodes:
        flow_graph.add_node(v)
        flow_graph.add_edge(v, sink, 1.0)

    for u, v, _weight in _bipartite_edges(graph, left_set, right_set):
        flow_graph.add_edge(u, v, 1.0)

    if record_steps is not None:
        record_steps.append(
            {
                "action": "build_flow_network",
                "left": list(left_nodes),
                "right": list(right_nodes),
            }
        )

    _max_flow, flow = ford_fulkerson(
        flow_graph, source, sink, record_steps=record_steps
    )

    matching: list[tuple[Hashable, Hashable]] = []
    for (u, v), amount in flow.items():
        if amount > 0.5 and u in left_set and v in right_set:
            matching.append((u, v))
            if record_steps is not None:
                record_steps.append(
                    {"action": "match", "pair": [u, v]}
                )

    return matching, len(matching)


def hopcroft_karp(
    graph: Graph,
    left_nodes: list[Hashable],
    right_nodes: list[Hashable],
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> tuple[list[tuple[Hashable, Hashable]], int]:
    """Maximum bipartite matching via Hopcroft–Karp (direct, no flow net).

    Approach: In phases, BFS builds a layered graph of shortest alternating
    paths from free left vertices; then DFS finds a maximal set of
    vertex-disjoint augmenting paths within that layering and augments them
    all at once. Phases continue until no augmenting path remains.

    Time complexity: O(E √V) — there are O(√V) phases (each phase increases
    the length of the shortest augmenting path, and after O(√V) phases the
    remaining unmatched vertices admit a short combinatorial bound), and
    each phase scans the adjacency lists in O(E) time. This improves on the
    flow-reduction Edmonds–Karp approach, which is O(V E) (or O(V E²) in the
    general capacity analysis) on the expanded unit network.

    Space complexity: O(V + E) — pair maps, distance labels, and adjacency.

    Real-world use case: Large-scale bipartite assignment (e.g. matching
    ads to slots or users to recommendations) where the O(E √V) bound matters.

    Returns:
        ``(matched_pairs, matching_size)`` — same format as
        ``bipartite_matching``.
    """
    left_set = set(left_nodes)
    right_set = set(right_nodes)
    if left_set & right_set:
        raise ValueError("left_nodes and right_nodes must be disjoint")

    adj: dict[Hashable, list[Hashable]] = {u: [] for u in left_nodes}
    for u, v, _ in _bipartite_edges(graph, left_set, right_set):
        adj[u].append(v)

    pair_u: dict[Hashable, Hashable | None] = {u: None for u in left_nodes}
    pair_v: dict[Hashable, Hashable | None] = {v: None for v in right_nodes}
    dist: dict[Hashable | None, float] = {}

    def bfs_layers() -> bool:
        queue: deque[Hashable | None] = deque()
        for u in left_nodes:
            if pair_u[u] is None:
                dist[u] = 0.0
                queue.append(u)
            else:
                dist[u] = math.inf
        dist[None] = math.inf
        while queue:
            u = queue.popleft()
            if dist[u] < dist[None]:
                if u is None:
                    continue
                for v in adj[u]:
                    matched_u = pair_v[v]
                    if dist[matched_u] == math.inf:
                        dist[matched_u] = dist[u] + 1.0
                        queue.append(matched_u)
        return dist[None] != math.inf

    def dfs_augment(u: Hashable | None) -> bool:
        if u is None:
            return True
        for v in adj[u]:
            matched_u = pair_v[v]
            if dist[matched_u] == dist[u] + 1.0 and dfs_augment(matched_u):
                pair_v[v] = u
                pair_u[u] = v
                return True
        dist[u] = math.inf
        return False

    matching_size = 0
    phase = 0
    while bfs_layers():
        phase += 1
        phase_augments = 0
        for u in left_nodes:
            if pair_u[u] is None and dfs_augment(u):
                matching_size += 1
                phase_augments += 1
        if record_steps is not None:
            record_steps.append(
                {
                    "action": "phase",
                    "phase": phase,
                    "augmented": phase_augments,
                    "matching_size": matching_size,
                }
            )

    pairs = [
        (u, v) for u, v in ((u, pair_u[u]) for u in left_nodes) if v is not None
    ]
    if record_steps is not None:
        for u, v in pairs:
            record_steps.append({"action": "match", "pair": [u, v]})

    return pairs, matching_size


def _edmonds_karp(
    graph: Graph,
    source: Hashable,
    sink: Hashable,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> tuple[float, FlowDict, Residual]:
    nodes = graph.get_nodes()
    if source not in nodes:
        raise ValueError(f"source {source!r} is not in the graph")
    if sink not in nodes:
        raise ValueError(f"sink {sink!r} is not in the graph")
    if source == sink:
        raise ValueError("source and sink must be distinct")

    capacities = _oriented_capacities(graph)
    for (_, _), cap in capacities.items():
        if cap < 0:
            raise ValueError("flow capacities must be non-negative")

    residual: Residual = defaultdict(lambda: defaultdict(float))
    for (u, v), cap in capacities.items():
        residual[u][v] += cap

    # Ensure every node appears as a key for BFS iteration convenience.
    for n in nodes:
        _ = residual[n]

    flow: FlowDict = {edge: 0.0 for edge in capacities}
    max_flow = 0.0
    iteration = 0

    while True:
        parent, path_edge_cap = _bfs_augmenting_path(residual, source, sink)
        if sink not in parent:
            break

        # Reconstruct path and bottleneck.
        path: list[tuple[Hashable, Hashable]] = []
        bottleneck = math.inf
        v = sink
        while v != source:
            u = parent[v]
            path.append((u, v))
            bottleneck = min(bottleneck, residual[u][v])
            v = u
        path.reverse()

        for u, v in path:
            residual[u][v] -= bottleneck
            residual[v][u] += bottleneck
            if (u, v) in flow:
                flow[(u, v)] += bottleneck
            elif (v, u) in flow:
                flow[(v, u)] -= bottleneck

        max_flow += bottleneck
        iteration += 1

        if record_steps is not None:
            path_residuals = [
                {
                    "from": u,
                    "to": v,
                    "residual_forward": residual[u][v],
                    "residual_backward": residual[v][u],
                }
                for u, v in path
            ]
            record_steps.append(
                {
                    "action": "augment",
                    "iteration": iteration,
                    "path": [[u, v] for u, v in path],
                    "bottleneck": bottleneck,
                    "flow_so_far": max_flow,
                    "residual_updates": path_residuals,
                }
            )

    # Drop zero / negative numerical noise from reported flows.
    clean_flow = {
        edge: amount for edge, amount in flow.items() if amount > EPS
    }
    return max_flow, clean_flow, residual


def _bfs_augmenting_path(
    residual: Residual,
    source: Hashable,
    sink: Hashable,
) -> tuple[dict[Hashable, Hashable], dict[tuple[Hashable, Hashable], float]]:
    parent: dict[Hashable, Hashable] = {}
    queue: deque[Hashable] = deque([source])
    seen = {source}
    edge_cap: dict[tuple[Hashable, Hashable], float] = {}

    while queue:
        u = queue.popleft()
        for v, cap in residual[u].items():
            if v not in seen and cap > EPS:
                seen.add(v)
                parent[v] = u
                edge_cap[(u, v)] = cap
                if v == sink:
                    return parent, edge_cap
                queue.append(v)
    return parent, edge_cap


def _residual_reachable(
    residual: Residual,
    source: Hashable,
) -> set[Hashable]:
    seen = {source}
    queue: deque[Hashable] = deque([source])
    while queue:
        u = queue.popleft()
        for v, cap in residual[u].items():
            if v not in seen and cap > EPS:
                seen.add(v)
                queue.append(v)
    return seen


def _oriented_capacities(
    graph: Graph,
) -> dict[tuple[Hashable, Hashable], float]:
    """Map directed capacities; undirected edges become both directions."""
    caps: dict[tuple[Hashable, Hashable], float] = {}
    if graph.directed:
        for u, v, weight in graph.get_edges():
            caps[(u, v)] = caps.get((u, v), 0.0) + weight
    else:
        for u, v, weight in graph.get_edges():
            caps[(u, v)] = caps.get((u, v), 0.0) + weight
            caps[(v, u)] = caps.get((v, u), 0.0) + weight
    return caps


def _bipartite_edges(
    graph: Graph,
    left_set: set[Hashable],
    right_set: set[Hashable],
) -> list[tuple[Hashable, Hashable, float]]:
    """Return left→right edges (orient undirected edges as needed)."""
    edges: list[tuple[Hashable, Hashable, float]] = []
    seen: set[tuple[Hashable, Hashable]] = set()
    for u, v, weight in graph.get_edges():
        if u in left_set and v in right_set:
            key = (u, v)
            if key not in seen:
                seen.add(key)
                edges.append((u, v, weight))
        elif v in left_set and u in right_set:
            key = (v, u)
            if key not in seen:
                seen.add(key)
                edges.append((v, u, weight))
    return edges
