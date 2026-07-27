"""Real-world graph dataset loaders."""

from __future__ import annotations

import networkx as nx

from graph_core.graph import Graph


def load_karate_club() -> Graph:
    """Load Zachary's Karate Club as a ``graph_core.Graph``.

    The classic 34-node social network of a university karate club, observed
    by Wayne Zachary (1977). It is a standard benchmark for community
    detection and centrality validation. Source data comes from
    ``networkx.karate_club_graph()`` and is converted into our adjacency-list
    ``Graph`` (NetworkX is used only as a dataset source here, not for
    algorithm execution).
    """
    nxg = nx.karate_club_graph()
    graph = Graph(directed=False, weighted=False)

    for node, attrs in nxg.nodes(data=True):
        graph.add_node(node, **dict(attrs))

    for u, v in nxg.edges():
        graph.add_edge(u, v)

    return graph
