"""Validate MST algorithms and Union–Find against NetworkX / structure checks."""

from __future__ import annotations

import math
import random

import networkx as nx
import pytest

from algorithms.mst import compare_mst_algorithms, kruskals, prims
from algorithms.union_find import UnionFind
from graph_core.generators import random_weighted_graph
from graph_core.graph import Graph


def _connected_weighted(n: int = 20, p: float = 0.35) -> Graph:
    """Generate a connected undirected weighted graph (retry if needed)."""
    for _ in range(50):
        g = random_weighted_graph(n, p, 0.5, 20.0)
        if nx.is_connected(g.to_networkx()):
            return g
    # Fallback: dense enough to be connected w.h.p.
    return random_weighted_graph(n, 0.8, 0.5, 20.0)


def _nx_mst_weight(graph: Graph) -> float:
    tree = nx.minimum_spanning_tree(graph.to_networkx(), weight="weight")
    return sum(data.get("weight", 1.0) for _, _, data in tree.edges(data=True))


def test_kruskals_matches_networkx_weight():
    g = _connected_weighted()
    edges, total = kruskals(g)
    assert len(edges) == g.num_nodes - 1
    assert total == pytest.approx(_nx_mst_weight(g), abs=1e-9)


def test_prims_matches_networkx_weight():
    g = _connected_weighted()
    edges, total = prims(g)
    assert len(edges) == g.num_nodes - 1
    assert total == pytest.approx(_nx_mst_weight(g), abs=1e-9)

    # Explicit start should not change the MST weight.
    start = random.choice(g.get_nodes())
    _, total2 = prims(g, start=start)
    assert total2 == pytest.approx(total, abs=1e-9)


def test_kruskals_raises_on_directed_graph():
    g = Graph(directed=True, weighted=True)
    g.add_edge(0, 1, 1.0)
    g.add_edge(1, 2, 2.0)
    with pytest.raises(ValueError, match="undirected"):
        kruskals(g)


def test_kruskals_raises_on_disconnected_graph():
    g = Graph(directed=False, weighted=True)
    g.add_edge(0, 1, 1.0)
    g.add_edge(2, 3, 1.0)  # separate component
    with pytest.raises(ValueError, match="disconnected"):
        kruskals(g)


def test_union_find_path_compression_flattens_tree():
    uf = UnionFind(["a", "b", "c", "d", "e"])
    # Force a chain a <- b <- c <- d <- e without union-by-rank balancing.
    uf.parent = {"a": "a", "b": "a", "c": "b", "d": "c", "e": "d"}
    uf.rank = {x: 0 for x in uf.parent}

    root = uf.find("e")
    assert root == "a"
    # Path compression should make every node on the path point at the root.
    assert uf.parent["e"] == "a"
    assert uf.parent["d"] == "a"
    assert uf.parent["c"] == "a"
    assert uf.parent["b"] == "a"


def test_union_find_union_by_rank_bounds_height():
    n = 64
    uf = UnionFind(range(n))
    # Pairwise union in an order that would form a linked list without ranks.
    for i in range(1, n):
        uf.union(0, i)

    max_rank = max(uf.rank.values())
    assert max_rank <= math.ceil(math.log2(n))

    # After finds, every element should hang directly under the root.
    root = uf.find(0)
    for i in range(n):
        uf.find(i)
        assert uf.parent[i] == root


def test_duplicate_weights_equal_mst_weight_possibly_different_edges():
    g = Graph(directed=False, weighted=True)
    # Several MSTs of weight 3 exist (any spanning tree of three weight-1 edges).
    g.add_edge(0, 1, 1.0)
    g.add_edge(1, 2, 1.0)
    g.add_edge(2, 3, 1.0)
    g.add_edge(3, 0, 1.0)
    g.add_edge(0, 2, 1.0)
    g.add_edge(1, 3, 5.0)

    k_edges, k_weight = kruskals(g)
    p_edges, p_weight = prims(g, start=0)

    assert k_weight == pytest.approx(p_weight, abs=1e-9)
    assert k_weight == pytest.approx(3.0, abs=1e-9)
    assert len(k_edges) == len(p_edges) == 3
    assert k_weight == pytest.approx(_nx_mst_weight(g), abs=1e-9)

    # Edge sets may differ under ties; weights must still match.
    k_set = {frozenset((u, v)) for u, v, _ in k_edges}
    p_set = {frozenset((u, v)) for u, v, _ in p_edges}
    assert isinstance(k_set, set) and isinstance(p_set, set)


def test_compare_mst_algorithms_agrees_and_reports_faster():
    g = _connected_weighted(n=25, p=0.4)
    result = compare_mst_algorithms(g)
    assert result["kruskals"]["total_weight"] == pytest.approx(
        result["prims"]["total_weight"], abs=1e-9
    )
    assert result["faster"] in {"kruskals", "prims"}
    assert "ms" in result["note"]
