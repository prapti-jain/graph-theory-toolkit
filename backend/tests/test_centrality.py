"""Validate centrality algorithms against NetworkX."""

from __future__ import annotations

import random

import networkx as nx
import pytest

from algorithms.centrality import (
    betweenness_centrality,
    closeness_centrality,
    eigenvector_centrality,
    pagerank,
)
from datasets.loader import load_karate_club
from graph_core.generators import random_graph
from graph_core.graph import Graph


def _approx_maps(a: dict, b: dict, rel: float = 1e-5, abs_: float = 1e-6) -> None:
    assert set(a) == set(b)
    for key in a:
        assert a[key] == pytest.approx(b[key], rel=rel, abs=abs_)


def test_pagerank_matches_networkx():
    g = random_graph(20, 0.25, directed=True, weighted=False)
    ranks, _iters, _hist = pagerank(g, damping=0.85, tolerance=1e-8)
    nx_ranks = nx.pagerank(g.to_networkx(), alpha=0.85, tol=1e-8)
    _approx_maps(ranks, nx_ranks, rel=1e-4, abs_=1e-5)


def test_betweenness_centrality_matches_networkx():
    g = random_graph(18, 0.3, directed=False, weighted=False)
    mine = betweenness_centrality(g)
    theirs = nx.betweenness_centrality(g.to_networkx())
    _approx_maps(mine, theirs, rel=1e-6, abs_=1e-8)


def test_closeness_centrality_matches_networkx():
    g = random_graph(18, 0.3, directed=False, weighted=False)
    mine = closeness_centrality(g)
    theirs = nx.closeness_centrality(g.to_networkx())
    _approx_maps(mine, theirs, rel=1e-6, abs_=1e-8)


def test_eigenvector_centrality_matches_networkx():
    # Prefer a connected graph so the principal eigenvector is well-defined.
    g = None
    for _ in range(30):
        candidate = random_graph(15, 0.4, directed=False, weighted=False)
        if nx.is_connected(candidate.to_networkx()):
            g = candidate
            break
    assert g is not None

    mine, _iters, _hist = eigenvector_centrality(g, tolerance=1e-8, max_iterations=200)
    theirs = nx.eigenvector_centrality(
        g.to_networkx(), tol=1e-8, max_iter=200
    )
    # Eigenvectors are unique up to sign; NetworkX returns non-negative.
    _approx_maps(mine, theirs, rel=1e-3, abs_=1e-4)


def test_pagerank_convergence_history():
    g = random_graph(25, 0.2, directed=True, weighted=False)
    ranks, iterations, history = pagerank(
        g, max_iterations=100, tolerance=1e-8
    )
    assert iterations <= 100
    assert len(history) == iterations
    assert history[-1] < 1e-8 or iterations == 100
    # Mostly monotonically decreasing: allow a few tiny numerical bumps.
    increases = sum(
        1 for i in range(1, len(history)) if history[i] > history[i - 1] * 1.01
    )
    assert increases <= max(2, len(history) // 10)
    assert sum(ranks.values()) == pytest.approx(1.0, abs=1e-6)


def test_pagerank_ranks_sum_to_one():
    g = random_graph(16, 0.25, directed=True, weighted=False)
    ranks, _, _ = pagerank(g)
    assert sum(ranks.values()) == pytest.approx(1.0, abs=1e-6)


def test_pagerank_dangling_node_handling():
    g = Graph(directed=True, weighted=False)
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_node(3)  # dangling: no outgoing edges
    g.add_edge(2, 0)
    # Node 3 is reachable from nowhere and has no out-edges; still must work.
    ranks, _, _ = pagerank(g)
    assert sum(ranks.values()) == pytest.approx(1.0, abs=1e-6)
    assert set(ranks) == {0, 1, 2, 3}
    assert all(r >= 0 for r in ranks.values())


def test_load_karate_club():
    g = load_karate_club()
    assert g.num_nodes == 34
    assert not g.directed
    assert g.num_edges == 78
    # Spot-check a known club attribute from the NetworkX dataset.
    assert g.get_node_attr(0, "club") in {"Mr. Hi", "Officer"}
