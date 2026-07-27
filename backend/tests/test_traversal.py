"""Validate traversal algorithms against NetworkX on random graphs."""

from __future__ import annotations

import random

import networkx as nx
import pytest

from algorithms.traversal import (
    bfs,
    connected_components,
    dfs,
    dfs_iterative,
    find_articulation_points,
    find_bridges,
    is_bipartite,
    tarjan_scc,
    topological_sort,
)
from graph_core.generators import random_graph


def _pick_start(graph):
    nodes = graph.get_nodes()
    assert nodes, "expected a non-empty graph"
    return random.choice(nodes)


def test_bfs_matches_networkx_reachability_and_distances():
    g = random_graph(20, 0.25, directed=False)
    start = _pick_start(g)
    distances, order = bfs(g, start)

    nxg = g.to_networkx()
    nx_reachable = set(nx.bfs_tree(nxg, start).nodes())
    nx_distances = nx.single_source_shortest_path_length(nxg, start)

    assert set(distances.keys()) == nx_reachable
    assert set(order) == nx_reachable
    assert distances == nx_distances


def test_dfs_matches_networkx_reachability():
    g = random_graph(20, 0.25, directed=False)
    start = _pick_start(g)
    order = dfs(g, start)

    nxg = g.to_networkx()
    nx_reachable = set(nx.dfs_tree(nxg, start).nodes())
    assert set(order) == nx_reachable


def test_dfs_iterative_matches_networkx_reachability():
    g = random_graph(20, 0.25, directed=False)
    start = _pick_start(g)
    order = dfs_iterative(g, start)

    nxg = g.to_networkx()
    nx_reachable = set(nx.dfs_tree(nxg, start).nodes())
    assert set(order) == nx_reachable


def test_topological_sort_matches_networkx_dag_or_cycle():
    g = random_graph(15, 0.15, directed=True)
    nxg = g.to_networkx()

    if nx.is_directed_acyclic_graph(nxg):
        result = topological_sort(g)
        assert set(result) == set(nxg.nodes())
        position = {node: i for i, node in enumerate(result)}
        for u, v in nxg.edges():
            assert position[u] < position[v]
        # NetworkX also produces a valid order (may differ)
        nx_order = list(nx.topological_sort(nxg))
        assert set(nx_order) == set(result)
    else:
        with pytest.raises(ValueError, match="cycle"):
            topological_sort(g)
        with pytest.raises(nx.NetworkXUnfeasible):
            list(nx.topological_sort(nxg))


def test_is_bipartite_matches_networkx():
    g = random_graph(20, 0.2, directed=False)
    assert is_bipartite(g) == nx.is_bipartite(g.to_networkx())


def test_connected_components_matches_networkx():
    g = random_graph(25, 0.08, directed=False)
    mine = connected_components(g)
    theirs = list(nx.connected_components(g.to_networkx()))

    assert {frozenset(c) for c in mine} == {frozenset(c) for c in theirs}


def test_tarjan_scc_matches_networkx():
    g = random_graph(18, 0.2, directed=True)
    mine = tarjan_scc(g)
    theirs = list(nx.strongly_connected_components(g.to_networkx()))

    assert {frozenset(c) for c in mine} == {frozenset(c) for c in theirs}


def test_find_bridges_matches_networkx():
    g = random_graph(20, 0.15, directed=False)
    mine = find_bridges(g)
    theirs = list(nx.bridges(g.to_networkx()))

    assert {frozenset(e) for e in mine} == {frozenset(e) for e in theirs}


def test_find_articulation_points_matches_networkx():
    g = random_graph(20, 0.15, directed=False)
    mine = find_articulation_points(g)
    theirs = list(nx.articulation_points(g.to_networkx()))

    assert set(mine) == set(theirs)


@pytest.mark.parametrize("seed", range(5))
def test_traversal_suite_multiple_seeds(seed):
    """Re-run key comparisons across several RNG seeds for stability."""
    random.seed(seed)
    undirected = random_graph(16, 0.2, directed=False)
    directed = random_graph(16, 0.2, directed=True)

    start = _pick_start(undirected)
    distances, order = bfs(undirected, start)
    nxu = undirected.to_networkx()
    assert set(distances) == set(nx.bfs_tree(nxu, start).nodes())
    assert set(dfs(undirected, start)) == set(nx.dfs_tree(nxu, start).nodes())

    assert {frozenset(c) for c in connected_components(undirected)} == {
        frozenset(c) for c in nx.connected_components(nxu)
    }
    assert {frozenset(e) for e in find_bridges(undirected)} == {
        frozenset(e) for e in nx.bridges(nxu)
    }
    assert set(find_articulation_points(undirected)) == set(
        nx.articulation_points(nxu)
    )
    assert is_bipartite(undirected) == nx.is_bipartite(nxu)

    nxd = directed.to_networkx()
    assert {frozenset(c) for c in tarjan_scc(directed)} == {
        frozenset(c) for c in nx.strongly_connected_components(nxd)
    }
