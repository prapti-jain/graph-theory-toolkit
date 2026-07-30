# Graph Theory Toolkit — Project Overview

## What this is

This project is a from-scratch implementation and interactive visualizer for
sixteen classical graph algorithms spanning five major areas of graph theory:
traversal and connectivity, shortest paths, minimum spanning trees, network
flows and matching, and centrality analysis. Every algorithm is implemented
independently (no `networkx` calls in the algorithm logic itself) and
validated against `networkx` as a ground-truth oracle in an automated test
suite. A benchmarking harness then checks whether each implementation's
*measured* runtime growth matches its *claimed* theoretical time complexity,
and an interactive web visualizer animates each algorithm step by step on
graphs the user can generate, edit, or load from a real dataset.

The goal was not just to implement these algorithms correctly, but to
demonstrate, empirically, that they behave the way the theory predicts —
and to be honest about the places where theory and practice diverge.

## Why this structure

Each algorithm family gets its own document (`01`–`05`), and each follows the
same skeleton so they can be read independently or together:

1. **Problem statement** — what question the algorithm answers
2. **Algorithm description** — the approach, in plain language
3. **Correctness sketch** — why it produces the right answer
4. **Complexity derivation** — where the time/space bounds actually come from
5. **Real-world application** — why anyone would want this
6. **Empirical validation** — what the test suite and benchmarks actually showed

`06-benchmarking.md` covers the methodology behind the empirical complexity
validation in more depth, including a worked example (Ford-Fulkerson) where
the *worst-case* bound and the *observed* runtime tell two different, both
correct, stories.

`07-references.md` lists the primary sources (CLRS, original papers) that
the implementations and proofs draw on.

## System architecture

```
backend/
  graph_core/       Graph class (adjacency dict-of-dicts), random/grid generators
  algorithms/        traversal.py, shortest_paths.py, mst.py, flows.py, centrality.py
  benchmarks/        empirical complexity validation harness
  datasets/          real-world dataset loader (Zachary's Karate Club)
  tests/             pytest suite, validated against networkx
  api/                FastAPI routes exposing every algorithm with step-by-step
                      "animation" traces for the frontend
frontend/
  React + vis-network canvas, algorithm control panel, step player,
  results panel, and (for PageRank) a live convergence chart
```

The backend and frontend communicate over a REST API. Every algorithm
endpoint returns not just the final answer but a `steps` array recording
the algorithm's internal decisions in order (nodes visited, edges relaxed,
augmenting paths found, etc.), which the frontend replays as an animation.
This was a deliberate design choice: the same trace data that makes a good
demo also makes debugging and grading easier, since the *process*, not just
the *output*, is inspectable.

## Validation methodology, in brief

Two independent layers of validation were used throughout:

**Correctness** — every algorithm's output is compared against the
equivalent `networkx` function on many randomly generated graphs (and, for
deterministic edge cases like negative-weight cycles or disconnected
graphs, on hand-constructed inputs). 112 tests pass across the five
algorithm families.

**Complexity** — a separate benchmarking harness measures wall-clock time
across a range of graph sizes and fits the data against the algorithm's
claimed theoretical complexity (e.g. `O(E log V)` for Dijkstra) using
log-log regression. This surfaced a genuine methodological subtlety: fitting
runtime against node count `n` alone can be misleading when the claimed
complexity is actually a function of edge count `E`, since `E` doesn't
always scale as a clean power of `n`. Re-fitting against the actual
graph-theoretic term (e.g. `E·log(V)` computed directly from each run's edge
count) resolved this and produced clean matches. Details and full results
are in `06-benchmarking.md`.

## A note on honesty over polish

Not every result was a clean confirmation, and this document set doesn't
pretend otherwise. Ford-Fulkerson's measured runtime does *not* match its
`O(V·E²)` worst-case bound — because that bound is a pessimistic guarantee,
and random sparse graphs rarely approach it. That mismatch, properly
explained, is a more interesting and more honest empirical finding than a
clean match would have been, and it's documented as such in
`06-benchmarking.md` rather than hidden.
