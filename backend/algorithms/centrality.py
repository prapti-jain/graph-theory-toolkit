"""Node centrality measures.

All algorithms operate solely on ``graph_core.Graph``. NetworkX is never used
for solving — only for validation in tests via ``Graph.to_networkx()``.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Any, Hashable, Optional

from graph_core.graph import Graph


def pagerank(
    graph: Graph,
    damping: float = 0.85,
    max_iterations: int = 100,
    tolerance: float = 1e-6,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> tuple[dict[Hashable, float], int, list[float]]:
    """PageRank via power iteration with dangling-node redistribution.

    Mathematical formulation::

        PR(v) = (1 - d) / N + d * (
            sum_{u → v} PR(u) / out(u)  +  sum_{dangling u} PR(u) / N
        )

    where ``d`` is the damping factor and dangling nodes (out-degree 0)
    redistribute their mass uniformly so the rank vector stays a
    probability distribution.

    Approach: Start from the uniform vector ``1/N`` and iterate the
    PageRank linear map until the L1 change falls below ``tolerance`` (or
    ``max_iterations`` is reached).

    Time complexity: O(k (V + E)) for ``k`` iterations — each iteration
    scans every edge once plus O(V) dangling / normalization work.

    Space complexity: O(V) — current and previous rank vectors.

    Real-world question: Which nodes are important because *important*
    nodes point to them? (The classic “authority by endorsement” score
    used originally to rank web pages.)

    Connection to eigenvector centrality: PageRank is a damped,
    column-stochastic variant of eigenvector centrality on the
    out-normalized adjacency matrix (see ``eigenvector_centrality``).

    Returns:
        ``(ranks, iterations, convergence_history)`` where
        ``convergence_history[i]`` is the L1 delta after iteration ``i+1``.
    """
    if not 0.0 <= damping <= 1.0:
        raise ValueError("damping must be in [0, 1]")

    nodes = graph.get_nodes()
    n = len(nodes)
    if n == 0:
        return {}, 0, []

    # Build incoming adjacency and out-degrees (directed sense).
    incoming: dict[Hashable, list[Hashable]] = {v: [] for v in nodes}
    out_degree: dict[Hashable, int] = {v: 0 for v in nodes}

    for u in nodes:
        neighbors = list(graph.get_neighbors(u).keys())
        # For undirected graphs, neighbors already include both directions.
        out_degree[u] = len(neighbors)
        for v in neighbors:
            incoming[v].append(u)

    dangling = [u for u in nodes if out_degree[u] == 0]

    ranks: dict[Hashable, float] = {v: 1.0 / n for v in nodes}
    history: list[float] = []
    base = (1.0 - damping) / n
    iterations = 0

    for iteration in range(1, max_iterations + 1):
        dangling_mass = damping * sum(ranks[u] for u in dangling) / n
        new_ranks: dict[Hashable, float] = {}
        for v in nodes:
            inbound = 0.0
            for u in incoming[v]:
                deg = out_degree[u]
                if deg > 0:
                    inbound += ranks[u] / deg
            new_ranks[v] = base + dangling_mass + damping * inbound

        delta = sum(abs(new_ranks[v] - ranks[v]) for v in nodes)
        history.append(delta)
        ranks = new_ranks
        iterations = iteration

        if record_steps is not None:
            record_steps.append(
                {
                    "action": "iteration",
                    "iteration": iteration,
                    "l1_delta": delta,
                }
            )

        if delta < tolerance:
            break

    return ranks, iterations, history


def betweenness_centrality(
    graph: Graph,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> dict[Hashable, float]:
    """Betweenness centrality via Brandes' algorithm.

    Mathematical formulation (unnormalized)::

        C_B(v) = sum_{s ≠ v ≠ t}  σ(s, t | v) / σ(s, t)

    where ``σ(s, t)`` is the number of shortest ``s``–``t`` paths and
    ``σ(s, t | v)`` counts those that pass through ``v``.

    Approach (Brandes, 2001): For each source ``s``, run a BFS to obtain
    shortest-path distances / dependency precursors, then accumulate
    pair-dependencies in reverse BFS order. This computes the full
    betweenness vector in O(V E) for unweighted graphs, versus the naive
    all-pairs enumeration which is O(V³) (or worse with path listing).
    Brandes' algorithm is the standard approach because it reuses BFS
    layering to accumulate dependencies in linear work per source without
    materializing every shortest path.

    Time complexity: O(V · E) unweighted (one BFS + dependency sweep per
    source).

    Space complexity: O(V + E) — BFS queues, predecessor lists, and
    dependency arrays per source.

    Real-world question: Which nodes act as bridges / brokers that control
    information flow between other pairs of nodes?
    """
    nodes = graph.get_nodes()
    centrality: dict[Hashable, float] = {v: 0.0 for v in nodes}

    for s in nodes:
        stack: list[Hashable] = []
        predecessors: dict[Hashable, list[Hashable]] = {v: [] for v in nodes}
        sigma: dict[Hashable, float] = {v: 0.0 for v in nodes}
        sigma[s] = 1.0
        dist: dict[Hashable, int] = {v: -1 for v in nodes}
        dist[s] = 0
        queue: deque[Hashable] = deque([s])

        while queue:
            v = queue.popleft()
            stack.append(v)
            for w in graph.get_neighbors(v):
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    predecessors[w].append(v)

        delta: dict[Hashable, float] = {v: 0.0 for v in nodes}
        while stack:
            w = stack.pop()
            for v in predecessors[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                centrality[w] += delta[w]

        if record_steps is not None:
            record_steps.append(
                {
                    "action": "source_done",
                    "source": s,
                    "reached": sum(1 for v in nodes if dist[v] >= 0),
                }
            )

    # Match NetworkX default: undirected graphs count each pair once,
    # so Brandes' directed accumulation double-counts — halve it.
    if not graph.directed:
        for v in nodes:
            centrality[v] /= 2.0

    # Match NetworkX betweenness_centrality(..., normalized=True) default.
    n = len(nodes)
    if n > 2:
        if graph.directed:
            scale = 1.0 / ((n - 1) * (n - 2))
        else:
            scale = 2.0 / ((n - 1) * (n - 2))
        for v in nodes:
            centrality[v] *= scale

    return centrality


def closeness_centrality(
    graph: Graph,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> dict[Hashable, float]:
    """Closeness centrality with Wasserman–Faust reachability normalization.

    Mathematical formulation::

        C_C(u) = ((r - 1) / (N - 1)) * (r - 1) / sum_{v reachable} d(u, v)

    equivalently ``(r - 1)^2 / ((N - 1) * sum d(u, v))`` for ``r > 1``,
    where ``r`` is the number of nodes reachable from ``u`` (including
    ``u``). This matches NetworkX’s normalization for disconnected graphs.

    Approach: From each node, BFS to obtain unweighted distances; score
    nodes by inverse total distance, scaled by the reachable fraction.

    Time complexity: O(V · (V + E)) — a BFS from every vertex.

    Space complexity: O(V) per BFS.

    Real-world question: Which nodes can reach the rest of the network
    most efficiently (smallest average shortest-path distance)?
    """
    nodes = graph.get_nodes()
    n = len(nodes)
    closeness: dict[Hashable, float] = {v: 0.0 for v in nodes}
    if n <= 1:
        return {v: 0.0 for v in nodes}

    for u in nodes:
        dist = _bfs_distances(graph, u)
        reachable = [v for v, d in dist.items() if v != u]
        r = len(reachable) + 1  # include u
        if len(reachable) == 0:
            closeness[u] = 0.0
        else:
            total = sum(dist[v] for v in reachable)
            closeness[u] = ((r - 1) / (n - 1)) * ((r - 1) / total)

        if record_steps is not None:
            record_steps.append(
                {
                    "action": "node_closeness",
                    "node": u,
                    "reachable": r - 1,
                    "score": closeness[u],
                }
            )

    return closeness


def eigenvector_centrality(
    graph: Graph,
    max_iterations: int = 100,
    tolerance: float = 1e-6,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> tuple[dict[Hashable, float], int, list[float]]:
    """Eigenvector centrality via power iteration on the adjacency matrix.

    Mathematical formulation: Find the principal eigenvector ``x`` of the
    (possibly asymmetric) adjacency matrix ``A``::

        A x = λ x,   x_v ≥ 0,   ||x||_2 = 1

    so a node’s score is proportional to the sum of its neighbors’ scores.

    Approach: Power iteration — repeatedly multiply the current vector by
    ``A`` and L2-normalize until consecutive iterates differ by less than
    ``tolerance`` in L1 (or ``max_iterations`` is hit).

    Connection to PageRank (course note): PageRank is essentially a
    *modified* eigenvector centrality. Instead of using the raw adjacency
    matrix ``A``, PageRank uses a column-stochastic matrix derived from
    out-degree normalization of ``A``, plus a damping teleport term
    ``(1-d)/N``. Both are principal-eigenvector / stationary-distribution
    ideas; PageRank’s damping guarantees uniqueness and handles dangling
    nodes, while classic eigenvector centrality answers “who is connected
    to other high-scoring nodes?” without the random-surfer teleport.

    Time complexity: O(k (V + E)) for ``k`` iterations.

    Space complexity: O(V).

    Real-world question: Which nodes are influential because they are
    linked to other influential nodes (recursive prestige)?

    Returns:
        ``(scores, iterations, convergence_history)``.
    """
    nodes = graph.get_nodes()
    n = len(nodes)
    if n == 0:
        return {}, 0, []

    scores: dict[Hashable, float] = {v: 1.0 / math.sqrt(n) for v in nodes}
    history: list[float] = []
    iterations = 0

    for iteration in range(1, max_iterations + 1):
        new_scores: dict[Hashable, float] = {v: 0.0 for v in nodes}
        # x' = A x  (for undirected A is symmetric; for directed use out-neighbors
        # as NetworkX eigenvector_centrality does on the adjacency matrix).
        for u in nodes:
            for v in graph.get_neighbors(u):
                new_scores[v] += scores[u]

        norm = math.sqrt(sum(val * val for val in new_scores.values()))
        if norm < 1e-18:
            # Disconnected / zero graph — fall back to uniform.
            new_scores = {v: 1.0 / math.sqrt(n) for v in nodes}
            history.append(0.0)
            scores = new_scores
            iterations = iteration
            break

        new_scores = {v: val / norm for v, val in new_scores.items()}
        delta = sum(abs(new_scores[v] - scores[v]) for v in nodes)
        history.append(delta)
        scores = new_scores
        iterations = iteration

        if record_steps is not None:
            record_steps.append(
                {
                    "action": "iteration",
                    "iteration": iteration,
                    "l1_delta": delta,
                }
            )

        if delta < tolerance:
            break

    return scores, iterations, history


def _bfs_distances(
    graph: Graph,
    start: Hashable,
) -> dict[Hashable, int]:
    dist: dict[Hashable, int] = {start: 0}
    queue: deque[Hashable] = deque([start])
    while queue:
        u = queue.popleft()
        for v in graph.get_neighbors(u):
            if v not in dist:
                dist[v] = dist[u] + 1
                queue.append(v)
    return dist
