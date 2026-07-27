"""Graph traversal and connectivity algorithms.

All algorithms operate solely on ``graph_core.Graph``. NetworkX is never used
for solving — only for validation in tests via ``Graph.to_networkx()``.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Hashable, Optional

from graph_core.graph import Graph


def bfs(
    graph: Graph,
    start: Hashable,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> tuple[dict[Hashable, int], list[Hashable]]:
    """Breadth-first search from ``start``.

    Approach: Explore the graph level by level with a FIFO queue, recording
    each node's first-visit distance from the source.

    Time complexity: O(V + E) — each vertex and each adjacency-list edge is
    examined at most once.

    Space complexity: O(V) — distance map, visit order, and the queue each
    hold at most O(V) entries.

    Returns:
        ``(distances, order)`` where ``distances`` maps each reachable node to
        its unweighted distance from ``start``, and ``order`` is the BFS
        visit sequence.
    """
    _ensure_start(graph, start)

    distances: dict[Hashable, int] = {start: 0}
    order: list[Hashable] = [start]
    queue: deque[Hashable] = deque([start])

    if record_steps is not None:
        record_steps.append(
            {"action": "visit", "node": start, "distance": 0}
        )

    while queue:
        u = queue.popleft()
        for v in graph.get_neighbors(u):
            if v not in distances:
                distances[v] = distances[u] + 1
                queue.append(v)
                order.append(v)
                if record_steps is not None:
                    record_steps.append(
                        {
                            "action": "visit",
                            "node": v,
                            "distance": distances[v],
                            "via": u,
                        }
                    )
            elif record_steps is not None:
                record_steps.append(
                    {"action": "skip", "node": v, "from": u}
                )

    return distances, order


def dfs(
    graph: Graph,
    start: Hashable,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> list[Hashable]:
    """Recursive depth-first search from ``start``.

    Approach: Recursively dive along unused edges before backtracking,
    recording nodes in pre-order (first discovery time).

    Time complexity: O(V + E) — each vertex and edge is processed once across
    the recursive exploration of the reachable component.

    Space complexity: O(V) — the recursion stack and visited set are O(V) in
    the worst case (e.g. a path graph).

    Returns:
        Pre-order traversal sequence of nodes reachable from ``start``.
    """
    _ensure_start(graph, start)
    visited: set[Hashable] = set()
    order: list[Hashable] = []

    def visit(u: Hashable) -> None:
        visited.add(u)
        order.append(u)
        if record_steps is not None:
            record_steps.append({"action": "visit", "node": u})
        for v in graph.get_neighbors(u):
            if v not in visited:
                if record_steps is not None:
                    record_steps.append(
                        {"action": "traverse", "from": u, "to": v}
                    )
                visit(v)
            elif record_steps is not None:
                record_steps.append(
                    {"action": "skip", "from": u, "to": v}
                )

    visit(start)
    return order


def dfs_iterative(
    graph: Graph,
    start: Hashable,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> list[Hashable]:
    """Iterative depth-first search from ``start`` using an explicit stack.

    Approach: Mimic recursive DFS with an explicit LIFO stack, pushing
    unvisited neighbors and recording nodes on first pop/discovery.

    Time complexity: O(V + E) — every vertex is pushed/popped a constant
    number of times and every adjacency entry is scanned once when its
    source is processed.

    Space complexity: O(V) — the explicit stack and visited set store at
    most O(V) nodes.

    Returns:
        Discovery-order traversal sequence of nodes reachable from ``start``.
    """
    _ensure_start(graph, start)
    visited: set[Hashable] = set()
    order: list[Hashable] = []
    stack: list[Hashable] = [start]

    while stack:
        u = stack.pop()
        if u in visited:
            continue
        visited.add(u)
        order.append(u)
        if record_steps is not None:
            record_steps.append({"action": "visit", "node": u})

        neighbors = list(graph.get_neighbors(u).keys())
        for v in reversed(neighbors):
            if v not in visited:
                stack.append(v)
                if record_steps is not None:
                    record_steps.append(
                        {"action": "push", "from": u, "to": v}
                    )

    return order


def topological_sort(graph: Graph) -> list[Hashable]:
    """DFS-based topological ordering of a directed acyclic graph.

    Approach: Run a 3-color DFS; append each node after exploring its
    outbound edges (post-order), then reverse the post-order list. A
    back-edge to a gray node proves a cycle.

    Time complexity: O(V + E) — standard DFS over all vertices and edges.

    Space complexity: O(V) — color map, recursion stack, and result list.

    Returns:
        A list of nodes in topological order.

    Raises:
        ValueError: If the graph is undirected or contains a directed cycle.
    """
    if not graph.directed:
        raise ValueError("topological_sort requires a directed graph")

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[Hashable, int] = {n: WHITE for n in graph.get_nodes()}
    result: list[Hashable] = []

    def visit(u: Hashable) -> None:
        color[u] = GRAY
        for v in graph.get_neighbors(u):
            if color[v] == GRAY:
                raise ValueError("Graph contains a cycle")
            if color[v] == WHITE:
                visit(v)
        color[u] = BLACK
        result.append(u)

    for node in graph.get_nodes():
        if color[node] == WHITE:
            visit(node)

    result.reverse()
    return result


def is_bipartite(graph: Graph) -> bool:
    """Decide whether ``graph`` is bipartite via BFS 2-coloring.

    Approach: Attempt to 2-color every connected component; a conflict
    (neighbor sharing the same color) means an odd cycle exists.

    Time complexity: O(V + E) — each vertex and edge is examined at most
    once across all component BFS runs.

    Space complexity: O(V) — color assignment and BFS queue.

    Returns:
        ``True`` if the graph is bipartite, otherwise ``False``.
    """
    color: dict[Hashable, int] = {}

    for start in graph.get_nodes():
        if start in color:
            continue
        color[start] = 0
        queue: deque[Hashable] = deque([start])
        while queue:
            u = queue.popleft()
            for v in graph.get_neighbors(u):
                if v not in color:
                    color[v] = 1 - color[u]
                    queue.append(v)
                elif color[v] == color[u]:
                    return False
    return True


def connected_components(graph: Graph) -> list[list[Hashable]]:
    """Find connected components of an undirected graph.

    Approach: Repeated BFS/DFS from unvisited nodes; each search yields one
    component of mutually reachable vertices.

    Time complexity: O(V + E) — the whole adjacency structure is scanned a
    constant number of times.

    Space complexity: O(V) — visited set plus component storage.

    Returns:
        A list of components, each a list of node ids.

    Raises:
        ValueError: If ``graph`` is directed.
    """
    if graph.directed:
        raise ValueError("connected_components requires an undirected graph")

    visited: set[Hashable] = set()
    components: list[list[Hashable]] = []

    for start in graph.get_nodes():
        if start in visited:
            continue
        component: list[Hashable] = []
        queue: deque[Hashable] = deque([start])
        visited.add(start)
        while queue:
            u = queue.popleft()
            component.append(u)
            for v in graph.get_neighbors(u):
                if v not in visited:
                    visited.add(v)
                    queue.append(v)
        components.append(component)

    return components


def tarjan_scc(
    graph: Graph,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> list[list[Hashable]]:
    """Tarjan's strongly connected components on a directed graph.

    Approach: Single DFS assigning discovery times and low-link values; a
    node is an SCC root when ``low[u] == disc[u]``, at which point the stack
    is popped down to ``u``.

    Time complexity: O(V + E) — one DFS pass; each edge updates low-link
    values in amortized O(1).

    Space complexity: O(V) — discovery/low arrays, recursion stack, and the
    explicit node stack.

    Returns:
        A list of strongly connected components (each a list of nodes).

    Raises:
        ValueError: If ``graph`` is undirected.
    """
    if not graph.directed:
        raise ValueError("tarjan_scc requires a directed graph")

    nodes = graph.get_nodes()
    disc: dict[Hashable, int] = {}
    low: dict[Hashable, int] = {}
    on_stack: set[Hashable] = set()
    stack: list[Hashable] = []
    components: list[list[Hashable]] = []
    time = 0

    def strongconnect(u: Hashable) -> None:
        nonlocal time
        disc[u] = low[u] = time
        time += 1
        stack.append(u)
        on_stack.add(u)
        if record_steps is not None:
            record_steps.append(
                {
                    "action": "discover",
                    "node": u,
                    "disc": disc[u],
                    "low": low[u],
                }
            )

        for v in graph.get_neighbors(u):
            if v not in disc:
                if record_steps is not None:
                    record_steps.append(
                        {"action": "traverse", "from": u, "to": v}
                    )
                strongconnect(v)
                low[u] = min(low[u], low[v])
                if record_steps is not None:
                    record_steps.append(
                        {
                            "action": "update_low",
                            "node": u,
                            "low": low[u],
                            "via": v,
                        }
                    )
            elif v in on_stack:
                low[u] = min(low[u], disc[v])
                if record_steps is not None:
                    record_steps.append(
                        {
                            "action": "back_edge",
                            "from": u,
                            "to": v,
                            "low": low[u],
                        }
                    )

        if low[u] == disc[u]:
            component: list[Hashable] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                component.append(w)
                if w == u:
                    break
            components.append(component)
            if record_steps is not None:
                record_steps.append(
                    {"action": "scc", "nodes": list(component)}
                )

    for node in nodes:
        if node not in disc:
            strongconnect(node)

    return components


def find_bridges(
    graph: Graph,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> list[tuple[Hashable, Hashable]]:
    """Find bridges (cut-edges) via Tarjan's low-link DFS.

    Approach: In an undirected DFS tree, edge ``(u, v)`` is a bridge iff
    ``low[v] > disc[u]`` (no back-edge from ``v``'s subtree reaches ``u``
    or an ancestor).

    Time complexity: O(V + E) — a single DFS computes discovery and low-link
    values for every vertex/edge.

    Space complexity: O(V) — discovery/low maps, parent pointers, and the
    recursion stack.

    Returns:
        A list of bridge edges ``(u, v)``.

    Raises:
        ValueError: If ``graph`` is directed.
    """
    if graph.directed:
        raise ValueError("find_bridges requires an undirected graph")

    disc: dict[Hashable, int] = {}
    low: dict[Hashable, int] = {}
    parent: dict[Hashable, Hashable | None] = {}
    bridges: list[tuple[Hashable, Hashable]] = []
    time = 0

    def dfs_bridge(u: Hashable) -> None:
        nonlocal time
        disc[u] = low[u] = time
        time += 1
        if record_steps is not None:
            record_steps.append(
                {
                    "action": "discover",
                    "node": u,
                    "disc": disc[u],
                    "low": low[u],
                }
            )

        for v in graph.get_neighbors(u):
            if v not in disc:
                parent[v] = u
                if record_steps is not None:
                    record_steps.append(
                        {"action": "traverse", "from": u, "to": v}
                    )
                dfs_bridge(v)
                low[u] = min(low[u], low[v])
                if record_steps is not None:
                    record_steps.append(
                        {
                            "action": "update_low",
                            "node": u,
                            "low": low[u],
                            "via": v,
                        }
                    )
                if low[v] > disc[u]:
                    bridges.append((u, v))
                    if record_steps is not None:
                        record_steps.append(
                            {"action": "bridge", "edge": [u, v]}
                        )
            elif v != parent.get(u):
                low[u] = min(low[u], disc[v])
                if record_steps is not None:
                    record_steps.append(
                        {
                            "action": "back_edge",
                            "from": u,
                            "to": v,
                            "low": low[u],
                        }
                    )

    for node in graph.get_nodes():
        if node not in disc:
            parent[node] = None
            dfs_bridge(node)

    return bridges


def find_articulation_points(
    graph: Graph,
    *,
    record_steps: Optional[list[dict[str, Any]]] = None,
) -> list[Hashable]:
    """Find articulation points (cut-vertices) via low-link DFS.

    Approach: A non-root ``u`` is an articulation point if some child ``v``
    satisfies ``low[v] >= disc[u]``; the DFS root is one iff it has two or
    more children in the DFS forest.

    Time complexity: O(V + E) — one DFS computes discovery times, low-link
    values, and child counts.

    Space complexity: O(V) — discovery/low/parent maps and recursion stack.

    Returns:
        A list of articulation-point node ids.

    Raises:
        ValueError: If ``graph`` is directed.
    """
    if graph.directed:
        raise ValueError(
            "find_articulation_points requires an undirected graph"
        )

    disc: dict[Hashable, int] = {}
    low: dict[Hashable, int] = {}
    parent: dict[Hashable, Hashable | None] = {}
    ap: set[Hashable] = set()
    time = 0

    def dfs_ap(u: Hashable) -> None:
        nonlocal time
        children = 0
        disc[u] = low[u] = time
        time += 1
        if record_steps is not None:
            record_steps.append(
                {
                    "action": "discover",
                    "node": u,
                    "disc": disc[u],
                    "low": low[u],
                }
            )

        for v in graph.get_neighbors(u):
            if v not in disc:
                parent[v] = u
                children += 1
                if record_steps is not None:
                    record_steps.append(
                        {"action": "traverse", "from": u, "to": v}
                    )
                dfs_ap(v)
                low[u] = min(low[u], low[v])
                if record_steps is not None:
                    record_steps.append(
                        {
                            "action": "update_low",
                            "node": u,
                            "low": low[u],
                            "via": v,
                        }
                    )

                if parent.get(u) is None and children > 1:
                    ap.add(u)
                    if record_steps is not None:
                        record_steps.append(
                            {
                                "action": "articulation_point",
                                "node": u,
                                "reason": "root_with_multiple_children",
                            }
                        )
                if parent.get(u) is not None and low[v] >= disc[u]:
                    ap.add(u)
                    if record_steps is not None:
                        record_steps.append(
                            {
                                "action": "articulation_point",
                                "node": u,
                                "reason": "low_link",
                                "child": v,
                            }
                        )
            elif v != parent.get(u):
                low[u] = min(low[u], disc[v])
                if record_steps is not None:
                    record_steps.append(
                        {
                            "action": "back_edge",
                            "from": u,
                            "to": v,
                            "low": low[u],
                        }
                    )

    for node in graph.get_nodes():
        if node not in disc:
            parent[node] = None
            dfs_ap(node)

    return list(ap)


def _ensure_start(graph: Graph, start: Hashable) -> None:
    if start not in graph.get_nodes():
        raise ValueError(f"start node {start!r} is not in the graph")
