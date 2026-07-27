"""Core Graph data structure with adjacency-list representation."""

from __future__ import annotations

from typing import Any, Hashable


class Graph:
    """Directed or undirected graph with optional edge weights.

    Internal representation is an adjacency list as a dict of dicts:
        {node: {neighbor: weight}}
    """

    def __init__(self, directed: bool = False, weighted: bool = False) -> None:
        self.directed = directed
        self.weighted = weighted
        self._adj: dict[Hashable, dict[Hashable, float]] = {}

    def add_node(self, node: Hashable) -> None:
        if node not in self._adj:
            self._adj[node] = {}

    def add_edge(
        self,
        u: Hashable,
        v: Hashable,
        weight: float = 1.0,
    ) -> None:
        self.add_node(u)
        self.add_node(v)
        w = float(weight) if self.weighted else 1.0
        self._adj[u][v] = w
        if not self.directed:
            self._adj[v][u] = w

    def remove_node(self, node: Hashable) -> None:
        if node not in self._adj:
            return
        del self._adj[node]
        for neighbors in self._adj.values():
            neighbors.pop(node, None)

    def remove_edge(self, u: Hashable, v: Hashable) -> None:
        if u in self._adj:
            self._adj[u].pop(v, None)
        if not self.directed and v in self._adj:
            self._adj[v].pop(u, None)

    def get_neighbors(self, node: Hashable) -> dict[Hashable, float]:
        return dict(self._adj.get(node, {}))

    def get_nodes(self) -> list[Hashable]:
        return list(self._adj.keys())

    def get_edges(self) -> list[tuple[Hashable, Hashable, float]]:
        edges: list[tuple[Hashable, Hashable, float]] = []
        if self.directed:
            for u, neighbors in self._adj.items():
                for v, weight in neighbors.items():
                    edges.append((u, v, weight))
            return edges

        seen: set[frozenset] = set()
        for u, neighbors in self._adj.items():
            for v, weight in neighbors.items():
                key = frozenset((u, v))
                if key in seen:
                    continue
                seen.add(key)
                edges.append((u, v, weight))
        return edges

    @property
    def num_nodes(self) -> int:
        return len(self._adj)

    @property
    def num_edges(self) -> int:
        total = sum(len(neighbors) for neighbors in self._adj.values())
        return total if self.directed else total // 2

    def to_networkx(self) -> Any:
        """Convert to a NetworkX graph for validation only (not for solving)."""
        import networkx as nx

        g = nx.DiGraph() if self.directed else nx.Graph()
        g.add_nodes_from(self.get_nodes())
        if self.weighted:
            g.add_weighted_edges_from(self.get_edges())
        else:
            g.add_edges_from((u, v) for u, v, _ in self.get_edges())
        return g

    def __repr__(self) -> str:
        kind = "directed" if self.directed else "undirected"
        weight = "weighted" if self.weighted else "unweighted"
        return (
            f"Graph({kind}, {weight}, "
            f"nodes={self.num_nodes}, edges={self.num_edges})"
        )
