"""Graph generators for common synthetic topologies."""

from __future__ import annotations

import random

from .graph import Graph


def random_graph(
    n: int,
    p: float,
    directed: bool = False,
    weighted: bool = False,
) -> Graph:
    """Erdős–Rényi G(n, p) random graph.

    Each possible edge is included independently with probability ``p``.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if not 0.0 <= p <= 1.0:
        raise ValueError("p must be in [0, 1]")

    g = Graph(directed=directed, weighted=weighted)
    for i in range(n):
        g.add_node(i)

    if directed:
        for u in range(n):
            for v in range(n):
                if u == v:
                    continue
                if random.random() < p:
                    weight = random.random() if weighted else 1.0
                    g.add_edge(u, v, weight)
    else:
        for u in range(n):
            for v in range(u + 1, n):
                if random.random() < p:
                    weight = random.random() if weighted else 1.0
                    g.add_edge(u, v, weight)
    return g


def grid_graph(rows: int, cols: int) -> Graph:
    """Undirected unweighted grid graph with ``rows * cols`` nodes."""
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be at least 1")

    g = Graph(directed=False, weighted=False)
    for r in range(rows):
        for c in range(cols):
            node = r * cols + c
            g.add_node(node)
            if c + 1 < cols:
                g.add_edge(node, node + 1)
            if r + 1 < rows:
                g.add_edge(node, node + cols)
    return g


def random_weighted_graph(
    n: int,
    edge_prob: float,
    min_weight: float,
    max_weight: float,
) -> Graph:
    """Undirected Erdős–Rényi graph with random edge weights in a range."""
    if min_weight > max_weight:
        raise ValueError("min_weight must be <= max_weight")

    g = Graph(directed=False, weighted=True)
    for i in range(n):
        g.add_node(i)

    for u in range(n):
        for v in range(u + 1, n):
            if random.random() < edge_prob:
                weight = random.uniform(min_weight, max_weight)
                g.add_edge(u, v, weight)
    return g
