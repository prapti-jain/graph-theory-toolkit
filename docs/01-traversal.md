# Traversal & Connectivity

This module answers a family of related questions: *which nodes can I reach,
in what order, and what does the reachability structure of this graph look
like?* Five algorithms are covered here: Breadth-First Search (BFS),
Depth-First Search (DFS), Topological Sort, Tarjan's Strongly Connected
Components, and the shared low-link technique behind bridge-finding and
articulation-point detection.

---

## Breadth-First Search (BFS)

### Problem statement
Given a graph and a start node, find the shortest path (by number of edges)
from the start to every reachable node, and the order in which nodes are
first discovered.

### Algorithm description
BFS explores the graph in layers. It maintains a queue, initially containing
only the start node, and a `visited` set. On each step, it dequeues a node,
marks it visited, and enqueues all of its unvisited neighbors. Because the
queue is FIFO, all nodes at distance *k* from the start are dequeued before
any node at distance *k+1* — this is what guarantees shortest paths in an
unweighted graph.

### Correctness sketch
By induction on distance layers: assume every node at distance ≤ k has
already been correctly assigned that distance and enqueued in order. When a
distance-*k* node is dequeued, all of its unvisited neighbors are at distance
*k+1* (they can't be closer, since BFS already exhausted all closer nodes;
they can't be assigned a larger distance later, since this is the first time
they're discovered). This holds for k+1 by the same argument, so the
invariant holds for all reachable nodes.

### Complexity
**Time:** O(V + E). Each node is enqueued and dequeued exactly once (O(V)),
and each edge is examined exactly once per direction it's traversed (O(E)
for a directed graph, or effectively O(2E) for undirected, still O(E)
asymptotically).

**Space:** O(V) for the visited set and queue in the worst case (e.g. a
star graph where every node is at distance 1 from the center).

### Real-world application
Shortest path in unweighted networks (e.g. degrees of separation in a social
graph), level-order traversal, and as a subroutine inside more complex
algorithms — including Edmonds-Karp's max-flow algorithm, covered in
`04-flows.md`, which is literally "run BFS repeatedly to find augmenting
paths."

### Empirical validation
BFS was validated against `networkx.bfs_tree` reachability sets (and
distances) on randomly generated graphs across multiple runs, all passing.
In the benchmarking suite, BFS showed the expected near-linear growth: on
graphs from 50 to 1600 nodes, measured runtime grew from 0.024 ms to 0.748
ms — an empirical fit of roughly `O(n^1.02)`, consistent with `O(V+E)` since
sparse Erdős–Rényi graphs have edge counts that scale close to linearly with
node count in this regime. See `06-benchmarking.md` for the full discussion
of why distinguishing `O(n)` from `O(V+E)` from `O(E log V)` empirically is
harder than it sounds when edge growth tracks node growth closely.

---

## Depth-First Search (DFS)

### Problem statement
Explore as far as possible along each branch before backtracking; used both
as a traversal in its own right and as the substrate for several other
algorithms (topological sort, SCC, bridges, articulation points).

### Algorithm description
Two implementations exist: a recursive version, which uses the call stack
implicitly, and an iterative version using an explicit stack — included
specifically because deep graphs can exceed a language's recursion limit,
and because making the stack explicit is a useful exercise in understanding
what recursion is actually doing under the hood.

### Correctness sketch
DFS's correctness (as a traversal that visits every reachable node exactly
once) follows directly from marking nodes visited before recursing into
their neighbors — this guarantees no node is processed twice and no
reachable node is skipped, since every unvisited neighbor of a visited node
is eventually explored.

### Complexity
**Time:** O(V + E), same reasoning as BFS — every node and edge is examined
a constant number of times.

**Space:** O(V) worst case for the recursion/explicit stack (e.g. a path
graph, where the entire graph is on the stack at once at maximum depth).

### Real-world application
DFS underlies cycle detection, topological sorting, and connected component
analysis — it's less about "the shortest way to get somewhere" and more
about "the structure of how things connect."

### Empirical validation
Validated against `networkx.dfs_tree` reachability sets. Since DFS visit
*order* can legitimately differ from `networkx`'s implementation (multiple
valid DFS orderings exist for the same graph), the test suite compares
reachability sets rather than exact sequences — the correct comparison for
an algorithm whose output isn't uniquely determined by the input.

---

## Topological Sort

### Problem statement
Given a Directed Acyclic Graph (DAG), produce a linear ordering of nodes
such that for every directed edge (u, v), u appears before v in the
ordering.

### Algorithm description
Implemented via DFS: recursively visit each node's neighbors first, then
prepend the node to the result list once all its neighbors are fully
processed (a "post-order" DFS, reversed). If a cycle exists, no valid
ordering can exist, so the algorithm raises an error.

### Correctness sketch
The key invariant is that a node is only added to the ordering after
*all* nodes reachable from it have already been added. Since edges only
ever point to nodes with *smaller or equal* finish times in this scheme,
reversing the finish order guarantees every edge points forward.

### Complexity
**Time:** O(V + E), same DFS traversal cost.

**Space:** O(V) for the recursion stack and result list.

### Real-world application
Build systems (compile dependencies before dependents), course prerequisite
ordering, task scheduling.

### Empirical validation
Tested for two properties: (1) on randomly generated DAGs, the returned
order is verified to satisfy the "every edge points forward" property
directly, and (2) on graphs with an injected cycle, the function is
confirmed to raise a `ValueError` rather than silently returning a
nonsensical order.

---

## Bipartiteness Check

### Problem statement
Can the graph's nodes be 2-colored such that no edge connects two nodes of
the same color?

### Algorithm description
BFS 2-coloring: start from any node, color it, and color every neighbor the
opposite color. If a neighbor is ever found already colored the *same*
color as the current node, the graph is not bipartite.

### Correctness sketch
A graph is bipartite if and only if it contains no odd-length cycle. BFS
2-coloring directly detects a same-color edge, which can only occur if an
odd cycle exists (walking around an odd cycle, colors must eventually
collide).

### Complexity
**Time:** O(V + E) — one BFS pass.
**Space:** O(V) for the color assignment.

---

## Connected Components (undirected graphs)

### Problem statement
Partition an undirected graph's nodes into maximal sets where every pair of
nodes in the same set is connected by some path.

### Algorithm description
Repeatedly run BFS (or DFS) from any unvisited node; everything reached in
that pass forms one component. Repeat from the next unvisited node until
all nodes are assigned to a component.

### Complexity
**Time:** O(V + E) total across all components combined, since each node
and edge is still only visited once overall.
**Space:** O(V).

---

## Tarjan's Strongly Connected Components (directed graphs)

### Problem statement
In a directed graph, partition nodes into maximal sets where every node in
a set can reach every other node in that same set (via directed paths in
both directions).

### Algorithm description
Tarjan's algorithm runs a single DFS pass while tracking two values per
node: its **discovery time** (when DFS first visits it) and its **low-link
value** (the smallest discovery time reachable from that node via the DFS
tree plus at most one back-edge). Nodes are pushed onto an explicit stack as
they're discovered. When a node's low-link value equals its own discovery
time, it is the "root" of an SCC, and every node still on the stack above
it (inclusive) is popped off and forms that SCC.

### Correctness sketch
The low-link value propagates the earliest-reachable ancestor information
up through the DFS tree. A node whose low-link equals its own discovery
time cannot reach any node discovered *before* it — meaning it's the entry
point of its SCC, and everything discovered after it on the stack that can
still reach back to it belongs in the same component. This is a subtle
argument, and its rigorous form (via the properties of DFS forests and back
edges) is standard in algorithms textbooks (see `07-references.md`); this
document gives the intuition rather than a full formal proof.

### Complexity
**Time:** O(V + E), a single DFS pass with constant-time bookkeeping per
node/edge.
**Space:** O(V) for the stack, discovery times, and low-link array.

### Real-world application
Detecting cyclic dependency clusters in directed graphs, e.g. mutually
dependent software modules, or identifying tightly-knit communities in a
citation/follower network where influence flows in both directions.

### Empirical validation
Validated against `networkx.strongly_connected_components` on random
directed graphs, comparing the resulting *sets* of components (not their
order, since SCC labeling order is implementation-defined).

---

## Bridges and Articulation Points

### Problem statement
**Bridges**: which edges, if removed, would disconnect the graph (increase
the number of connected components)? **Articulation points**: which nodes,
if removed, would do the same?

### Algorithm description
Both use the same low-link DFS technique as Tarjan's SCC algorithm, applied
to undirected graphs. An edge (u, v) is a bridge if there is no back-edge
from v's subtree to u or any ancestor of u — i.e., `low[v] > discovery[u]`.
A node u (non-root) is an articulation point if it has some child v in the
DFS tree with `low[v] >= discovery[u]` — meaning v's subtree has no way
back to u's ancestors without going through u. The root is a special case:
it's an articulation point if and only if it has more than one child in the
DFS tree.

### Correctness sketch
`low[v] > discovery[u]` for edge (u,v) means nothing in v's subtree can
reach back to u or earlier — so removing that single edge genuinely
disconnects the subtree. The articulation point condition is the node-level
analogue: `low[v] >= discovery[u]` (not strict) because even a back-edge
reaching exactly u itself doesn't help v's subtree survive u's removal.

### Complexity
**Time:** O(V + E), one DFS pass.
**Space:** O(V).

### Real-world application
Network reliability analysis — identifying single points of failure in
infrastructure (power grids, computer networks, road systems) where losing
one connection or one hub fragments the system.

### Empirical validation
Validated against `networkx.bridges` and `networkx.articulation_points` as
set comparisons on random undirected graphs.
