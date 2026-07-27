"""Validate flow / matching algorithms against NetworkX and hand examples."""

from __future__ import annotations

import random
from collections import deque

import networkx as nx
import pytest
from networkx.algorithms import bipartite as nx_bipartite

from algorithms.flows import (
    bipartite_matching,
    ford_fulkerson,
    hopcroft_karp,
    min_cut,
)
from graph_core.generators import random_graph
from graph_core.graph import Graph


def _random_flow_network(n: int = 12, p: float = 0.35) -> tuple[Graph, int, int]:
    """Directed capacity network with a reachable source→sink pair."""
    for _ in range(40):
        g = random_graph(n, p, directed=True, weighted=True)
        # Scale capacities to be positive and a bit larger.
        scaled = Graph(directed=True, weighted=True)
        for node in g.get_nodes():
            scaled.add_node(node)
        for u, v, w in g.get_edges():
            scaled.add_edge(u, v, max(w, 0.05) * 10.0)

        nxg = scaled.to_networkx()
        for source in range(n):
            reachable = set(nx.descendants(nxg, source)) | {source}
            sinks = [t for t in reachable if t != source]
            if sinks:
                sink = random.choice(sinks)
                return scaled, source, sink
    raise RuntimeError("failed to build a flow network")


def _random_bipartite(n_left: int = 8, n_right: int = 8, p: float = 0.35) -> tuple[Graph, list[int], list[int]]:
    left = list(range(n_left))
    right = list(range(n_left, n_left + n_right))
    g = Graph(directed=False, weighted=False)
    for u in left:
        g.add_node(u)
    for v in right:
        g.add_node(v)
    for u in left:
        for v in right:
            if random.random() < p:
                g.add_edge(u, v)
    return g, left, right


def _reachable_after_removal(graph: Graph, source, sink, removed: set[tuple]) -> bool:
    """BFS on directed capacities with ``removed`` original edges deleted."""
    adj = {n: {} for n in graph.get_nodes()}
    for u, v, w in graph.get_edges():
        if graph.directed:
            if (u, v) not in removed:
                adj[u][v] = w
        else:
            if (u, v) not in removed and (v, u) not in removed:
                adj[u][v] = w
                adj[v][u] = w

    seen = {source}
    queue = deque([source])
    while queue:
        u = queue.popleft()
        if u == sink:
            return True
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                queue.append(v)
    return False


def test_classic_four_node_flow_network():
    """Hand-checked example independent of NetworkX.

    Capacities:
        0→1:3, 0→2:2, 1→2:5, 1→3:2, 2→3:3
    Max flow is 5 (e.g. 0-1-3:2, 0-1-2-3:1, 0-2-3:2).
    """
    g = Graph(directed=True, weighted=True)
    g.add_edge(0, 1, 3)
    g.add_edge(0, 2, 2)
    g.add_edge(1, 2, 5)
    g.add_edge(1, 3, 2)
    g.add_edge(2, 3, 3)

    value, flow = ford_fulkerson(g, 0, 3)
    assert value == pytest.approx(5.0, abs=1e-9)
    assert sum(flow.get((0, v), 0.0) for v in (1, 2)) == pytest.approx(5.0)
    assert sum(flow.get((u, 3), 0.0) for u in (1, 2)) == pytest.approx(5.0)

    cut_value, cut_edges = min_cut(g, 0, 3)
    assert cut_value == pytest.approx(5.0, abs=1e-9)
    assert cut_edges


def test_ford_fulkerson_matches_networkx():
    g, source, sink = _random_flow_network()
    value, _flow = ford_fulkerson(g, source, sink)
    nx_value = nx.maximum_flow_value(g.to_networkx(), source, sink, capacity="weight")
    assert value == pytest.approx(nx_value, abs=1e-6)


def test_min_cut_equals_max_flow_theorem():
    for _ in range(5):
        g, source, sink = _random_flow_network(n=10, p=0.4)
        flow_value, _ = ford_fulkerson(g, source, sink)
        cut_value, cut_edges = min_cut(g, source, sink)
        assert cut_value == pytest.approx(flow_value, abs=1e-6)
        assert cut_value == pytest.approx(
            nx.maximum_flow_value(g.to_networkx(), source, sink, capacity="weight"),
            abs=1e-6,
        )
        assert cut_edges or flow_value == pytest.approx(0.0)


def test_min_cut_edges_disconnect_source_from_sink():
    g, source, sink = _random_flow_network(n=14, p=0.35)
    cut_value, cut_edges = min_cut(g, source, sink)
    if cut_value == 0:
        return

    removed = {(u, v) for u, v, _ in cut_edges}
    assert not _reachable_after_removal(g, source, sink, removed)

    # Leaving one cut edge should not be required to stay disconnected for
    # every graph (alternate paths may exist through other cut edges only),
    # but removing all cut edges must separate source from sink — checked above.


def test_bipartite_matching_matches_networkx():
    g, left, right = _random_bipartite()
    pairs, size = bipartite_matching(g, left, right)

    nxg = g.to_networkx()
    matching = nx_bipartite.maximum_matching(nxg, top_nodes=left)
    nx_size = len(matching) // 2
    assert size == nx_size
    assert len(pairs) == size
    # Valid matching: endpoints unique.
    used = [n for pair in pairs for n in pair]
    assert len(used) == len(set(used))


def test_hopcroft_karp_matches_networkx():
    g, left, right = _random_bipartite()
    pairs, size = hopcroft_karp(g, left, right)

    matching = nx_bipartite.maximum_matching(g.to_networkx(), top_nodes=left)
    assert size == len(matching) // 2
    assert len(pairs) == size


def test_bipartite_methods_agree_on_matching_size():
    for _ in range(5):
        g, left, right = _random_bipartite(
            n_left=random.randint(5, 10),
            n_right=random.randint(5, 10),
            p=random.uniform(0.2, 0.6),
        )
        _, size_ff = bipartite_matching(g, left, right)
        _, size_hk = hopcroft_karp(g, left, right)
        assert size_ff == size_hk
