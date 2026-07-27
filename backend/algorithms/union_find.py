"""Disjoint-set (Union–Find) data structure with path compression and union by rank."""

from __future__ import annotations

from typing import Hashable, Iterable


class UnionFind:
    """Disjoint-set union with path compression and union by rank.

    ``find`` and ``union`` run in amortized ``O(α(n))`` time, where ``α`` is
    the inverse Ackermann function. ``α(n)`` grows so extremely slowly that it
    is at most 4 for any practical ``n`` (far beyond the number of atoms in
    the observable universe), so the cost is effectively constant in practice.
    """

    def __init__(self, elements: Iterable[Hashable] | None = None) -> None:
        self.parent: dict[Hashable, Hashable] = {}
        self.rank: dict[Hashable, int] = {}
        if elements is not None:
            for x in elements:
                self.make_set(x)

    def make_set(self, x: Hashable) -> None:
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0

    def find(self, x: Hashable) -> Hashable:
        """Return the representative of ``x``, compressing the path."""
        if x not in self.parent:
            self.make_set(x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a: Hashable, b: Hashable) -> bool:
        """Merge the sets containing ``a`` and ``b`` by rank.

        Returns:
            ``True`` if the sets were disjoint and a merge occurred,
            otherwise ``False``.
        """
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a == root_b:
            return False

        if self.rank[root_a] < self.rank[root_b]:
            root_a, root_b = root_b, root_a
        self.parent[root_b] = root_a
        if self.rank[root_a] == self.rank[root_b]:
            self.rank[root_a] += 1
        return True

    def connected(self, a: Hashable, b: Hashable) -> bool:
        return self.find(a) == self.find(b)
