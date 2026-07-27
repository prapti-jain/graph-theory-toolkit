"""Validate shortest-path algorithms against NetworkX."""

from __future__ import annotations

import math
import random

import networkx as nx
import pytest

from algorithms.shortest_paths import (
    a_star,
    bellman_ford,
    dijkstra,
    euclidean_heuristic,
    floyd_warshall,
    johnsons,
    reconstruct_path,
)
from graph_core.generators import grid_graph, random_graph, random_weighted_graph
from graph_core.graph import Graph


def _approx_dist_dicts(a: dict, b: dict, rel: float = 1e-9) -> None:
    assert set(a) == set(b)
    for key in a:
        assert a[key] == pytest.approx(b[key], rel=rel, abs=1e-9)


def _approx_matrices(a: dict, b: dict, rel: float = 1e-9) -> None:
    assert set(a) == set(b)
    for u in a:
        assert set(a[u]) == set(b[u])
        for v in a[u]:
            av, bv = a[u][v], b[u][v]
            if math.isinf(av) or math.isinf(bv):
                assert math.isinf(av) and math.isinf(bv)
            else:
                assert av == pytest.approx(bv, rel=rel, abs=1e-9)


def _dag_with_mixed_weights(n: int = 12, p: float = 0.35) -> Graph:
    """Directed acyclic graph with positive and negative edge weights."""
    g = Graph(directed=True, weighted=True)
    for i in range(n):
        g.add_node(i)
    for u in range(n):
        for v in range(u + 1, n):
            if random.random() < p:
                g.add_edge(u, v, random.uniform(-4.0, 8.0))
    return g


def test_dijkstra_matches_networkx():
    g = random_weighted_graph(18, 0.3, 0.5, 12.0)
    start = random.choice(g.get_nodes())
    distances, predecessors = dijkstra(g, start)

    nx_dist, _nx_paths = nx.single_source_dijkstra(g.to_networkx(), start)
    _approx_dist_dicts(distances, nx_dist)

    # Spot-check path reconstruction cost against NetworkX distance.
    target = max(distances, key=distances.get)
    path = reconstruct_path(predecessors, start, target)
    assert path[0] == start and path[-1] == target
    path_cost = sum(
        g.get_neighbors(path[i])[path[i + 1]] for i in range(len(path) - 1)
    )
    assert path_cost == pytest.approx(distances[target], abs=1e-9)


def test_bellman_ford_matches_networkx():
    g = _dag_with_mixed_weights()
    start = 0
    distances, _predecessors = bellman_ford(g, start)

    nx_dist = nx.single_source_bellman_ford_path_length(g.to_networkx(), start)
    # Also exercise the named bellman_ford_path_length helper per target.
    for target, dist in distances.items():
        assert dist == pytest.approx(
            nx.bellman_ford_path_length(g.to_networkx(), start, target),
            abs=1e-9,
        )
    _approx_dist_dicts(distances, dict(nx_dist))


def test_bellman_ford_raises_on_negative_cycle():
    g = Graph(directed=True, weighted=True)
    g.add_edge(0, 1, 1.0)
    g.add_edge(1, 2, -3.0)
    g.add_edge(2, 0, 1.0)  # cycle weight -1
    g.add_edge(2, 3, 2.0)

    with pytest.raises(ValueError, match="negative-weight cycle"):
        bellman_ford(g, 0)


def test_floyd_warshall_matches_networkx():
    g = random_weighted_graph(10, 0.35, 1.0, 9.0)
    mine = floyd_warshall(g)
    theirs = {u: dict(v) for u, v in nx.floyd_warshall(g.to_networkx()).items()}
    _approx_matrices(mine, theirs)


def test_johnsons_matches_networkx():
    g = _dag_with_mixed_weights(n=10, p=0.4)
    mine = johnsons(g)
    theirs = {u: dict(v) for u, v in nx.floyd_warshall(g.to_networkx()).items()}
    _approx_matrices(mine, theirs)


def test_floyd_warshall_and_johnsons_agree():
    g = _dag_with_mixed_weights(n=11, p=0.4)
    fw = floyd_warshall(g)
    jh = johnsons(g)
    _approx_matrices(fw, jh)

    # Non-negative undirected case as well.
    ug = random_weighted_graph(10, 0.4, 0.5, 7.0)
    _approx_matrices(floyd_warshall(ug), johnsons(ug))


def test_a_star_matches_dijkstra_and_explores_fewer_nodes():
    rows, cols = 12, 12
    trials = 8
    astar_settles: list[int] = []
    dijkstra_settles: list[int] = []

    for _ in range(trials):
        g = grid_graph(rows, cols)
        for r in range(rows):
            for c in range(cols):
                node = r * cols + c
                g.set_node_attr(node, "x", float(c))
                g.set_node_attr(node, "y", float(r))

        start = 0
        goal = rows * cols - 1
        # Occasional alternate target still far from start.
        if random.random() < 0.5:
            goal = (rows - 1) * cols + cols // 2

        heuristic = euclidean_heuristic(g, goal)
        a_steps: list[dict] = []
        d_steps: list[dict] = []

        a_dist, a_pred = a_star(
            g, start, goal, heuristic, record_steps=a_steps
        )
        d_dist, d_pred = dijkstra(g, start, record_steps=d_steps)

        assert a_dist[goal] == pytest.approx(d_dist[goal], abs=1e-9)
        assert reconstruct_path(a_pred, start, goal)[0] == start
        assert len(reconstruct_path(a_pred, start, goal)) == len(
            reconstruct_path(d_pred, start, goal)
        )

        astar_settles.append(
            sum(1 for s in a_steps if s.get("action") == "settle")
        )
        dijkstra_settles.append(
            sum(1 for s in d_steps if s.get("action") == "settle")
        )

    assert sum(astar_settles) / trials < sum(dijkstra_settles) / trials


def test_reconstruct_path_raises_when_unreachable():
    g = random_graph(6, 0.0, directed=False, weighted=False)
    for i in range(6):
        g.add_node(i)
    distances, predecessors = dijkstra(g, 0)
    assert distances == {0: 0.0}
    with pytest.raises(ValueError, match="No path"):
        reconstruct_path(predecessors, 0, 3)
