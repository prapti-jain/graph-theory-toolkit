"""HTTP routes for graph algorithms."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Hashable, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from algorithms.centrality import (
    betweenness_centrality,
    closeness_centrality,
    eigenvector_centrality,
    pagerank,
)
from algorithms.flows import (
    bipartite_matching,
    ford_fulkerson,
    hopcroft_karp,
    min_cut,
)
from algorithms.mst import compare_mst_algorithms, kruskals, prims
from algorithms.shortest_paths import (
    a_star,
    bellman_ford,
    dijkstra,
    euclidean_heuristic,
    floyd_warshall,
    johnsons,
    reconstruct_path,
)
from algorithms.traversal import (
    bfs,
    dfs,
    find_articulation_points,
    find_bridges,
    tarjan_scc,
)
from datasets.loader import load_karate_club
from graph_core.generators import grid_graph, random_graph, random_weighted_graph
from graph_core.graph import Graph

BENCHMARK_RESULTS_PATH = (
    Path(__file__).resolve().parents[1] / "benchmarks" / "results" / "benchmark_results.json"
)

router = APIRouter()

NodeId = Union[int, str]


class GraphBody(BaseModel):
    """Shared request body for graph algorithm endpoints."""

    edges: list[list[Any]] = Field(
        ...,
        description="Edge list: [u, v] or [u, v, weight]",
    )
    nodes: Optional[list[NodeId]] = Field(
        default=None,
        description="Optional explicit node list (isolated nodes included)",
    )
    directed: bool = False
    weighted: bool = False
    start: Optional[NodeId] = None
    goal: Optional[NodeId] = None
    source: Optional[NodeId] = None
    sink: Optional[NodeId] = None
    left_nodes: Optional[list[NodeId]] = None
    right_nodes: Optional[list[NodeId]] = None
    damping: float = 0.85
    max_iterations: int = 100
    tolerance: float = 1e-6
    coordinates: Optional[dict[str, list[float]]] = Field(
        default=None,
        description='Optional node coordinates: {"node_id": [x, y]}',
    )


def _build_graph(
    body: GraphBody,
    *,
    directed: Optional[bool] = None,
    weighted: Optional[bool] = None,
) -> Graph:
    is_directed = body.directed if directed is None else directed
    is_weighted = body.weighted if weighted is None else weighted
    graph = Graph(directed=is_directed, weighted=is_weighted)
    if body.nodes:
        for node in body.nodes:
            graph.add_node(node)
    for edge in body.edges:
        if len(edge) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid edge {edge!r}; expected [u, v] or [u, v, w]",
            )
        u, v = edge[0], edge[1]
        weight = float(edge[2]) if len(edge) >= 3 else 1.0
        graph.add_edge(u, v, weight)

    if body.coordinates:
        for key, coords in body.coordinates.items():
            if len(coords) < 2:
                raise HTTPException(
                    status_code=400,
                    detail=f"coordinates[{key!r}] must be [x, y]",
                )
            node: NodeId = int(key) if key.lstrip("-").isdigit() else key
            graph.set_node_attr(node, "x", float(coords[0]))
            graph.set_node_attr(node, "y", float(coords[1]))
    return graph


def _require_start(body: GraphBody) -> Hashable:
    if body.start is None:
        raise HTTPException(status_code=400, detail="'start' node is required")
    return body.start


def _require_goal(body: GraphBody) -> Hashable:
    if body.goal is None:
        raise HTTPException(status_code=400, detail="'goal' node is required")
    return body.goal


def _json_number(value: float) -> Optional[float]:
    if math.isinf(value) or math.isnan(value):
        return None
    return value


def _json_dist_map(distances: dict[Hashable, float]) -> dict[str, Optional[float]]:
    return {str(k): _json_number(v) for k, v in distances.items()}


def _json_matrix(
    matrix: dict[Hashable, dict[Hashable, float]],
) -> dict[str, dict[str, Optional[float]]]:
    return {
        str(u): {str(v): _json_number(d) for v, d in row.items()}
        for u, row in matrix.items()
    }


@router.post("/api/traversal/bfs")
def traversal_bfs(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body)
    start = _require_start(body)
    steps: list[dict[str, Any]] = []
    try:
        distances, order = bfs(graph, start, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "distances": {str(k): v for k, v in distances.items()},
        "order": order,
        "steps": steps,
    }


@router.post("/api/traversal/dfs")
def traversal_dfs(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body)
    start = _require_start(body)
    steps: list[dict[str, Any]] = []
    try:
        order = dfs(graph, start, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "order": order,
        "steps": steps,
    }


@router.post("/api/traversal/scc")
def traversal_scc(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, directed=True)
    steps: list[dict[str, Any]] = []
    try:
        components = tarjan_scc(graph, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "components": components,
        "steps": steps,
    }


@router.post("/api/traversal/bridges")
def traversal_bridges(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, directed=False)
    steps: list[dict[str, Any]] = []
    try:
        bridges = find_bridges(graph, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "bridges": [[u, v] for u, v in bridges],
        "steps": steps,
    }


@router.post("/api/traversal/articulation-points")
def traversal_articulation_points(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, directed=False)
    steps: list[dict[str, Any]] = []
    try:
        points = find_articulation_points(graph, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "articulation_points": points,
        "steps": steps,
    }


@router.post("/api/shortest-path/dijkstra")
def shortest_dijkstra(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, weighted=True)
    start = _require_start(body)
    steps: list[dict[str, Any]] = []
    try:
        distances, predecessors = dijkstra(graph, start, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    path: Optional[list[Hashable]] = None
    if body.goal is not None:
        try:
            path = reconstruct_path(predecessors, start, body.goal)
        except ValueError:
            path = None

    return {
        "distances": _json_dist_map(distances),
        "predecessors": {
            str(k): (None if v is None else v) for k, v in predecessors.items()
        },
        "path": path,
        "steps": steps,
    }


@router.post("/api/shortest-path/bellman-ford")
def shortest_bellman_ford(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, weighted=True)
    start = _require_start(body)
    steps: list[dict[str, Any]] = []
    try:
        distances, predecessors = bellman_ford(
            graph, start, record_steps=steps
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    path: Optional[list[Hashable]] = None
    if body.goal is not None:
        try:
            path = reconstruct_path(predecessors, start, body.goal)
        except ValueError:
            path = None

    return {
        "distances": _json_dist_map(distances),
        "predecessors": {
            str(k): (None if v is None else v) for k, v in predecessors.items()
        },
        "path": path,
        "steps": steps,
    }


@router.post("/api/shortest-path/floyd-warshall")
def shortest_floyd_warshall(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, weighted=True)
    steps: list[dict[str, Any]] = []
    try:
        matrix = floyd_warshall(graph, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    path_distance: Optional[float] = None
    if body.start is not None and body.goal is not None:
        path_distance = _json_number(matrix[body.start][body.goal])

    return {
        "distances": _json_matrix(matrix),
        "path_distance": path_distance,
        "steps": steps,
    }


@router.post("/api/shortest-path/a-star")
def shortest_a_star(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, weighted=True)
    start = _require_start(body)
    goal = _require_goal(body)
    steps: list[dict[str, Any]] = []
    try:
        heuristic = euclidean_heuristic(graph, goal)
        distances, predecessors = a_star(
            graph, start, goal, heuristic, record_steps=steps
        )
        path = reconstruct_path(predecessors, start, goal)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "distances": _json_dist_map(distances),
        "predecessors": {
            str(k): (None if v is None else v) for k, v in predecessors.items()
        },
        "path": path,
        "distance": _json_number(distances.get(goal, math.inf)),
        "steps": steps,
    }


@router.post("/api/shortest-path/johnsons")
def shortest_johnsons(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, weighted=True)
    steps: list[dict[str, Any]] = []
    try:
        matrix = johnsons(graph, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    path_distance: Optional[float] = None
    if body.start is not None and body.goal is not None:
        path_distance = _json_number(matrix[body.start][body.goal])

    return {
        "distances": _json_matrix(matrix),
        "path_distance": path_distance,
        "steps": steps,
    }


def _json_mst_edges(edges: list[tuple]) -> list[dict[str, Any]]:
    return [
        {"u": u, "v": v, "weight": weight}
        for u, v, weight in edges
    ]


@router.post("/api/mst/kruskals")
def mst_kruskals(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, directed=False, weighted=True)
    steps: list[dict[str, Any]] = []
    try:
        edges, total = kruskals(graph, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "edges": _json_mst_edges(edges),
        "total_weight": total,
        "steps": steps,
    }


@router.post("/api/mst/prims")
def mst_prims(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, directed=False, weighted=True)
    steps: list[dict[str, Any]] = []
    try:
        edges, total = prims(graph, start=body.start, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "edges": _json_mst_edges(edges),
        "total_weight": total,
        "steps": steps,
    }


@router.post("/api/mst/compare")
def mst_compare(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, directed=False, weighted=True)
    steps: list[dict[str, Any]] = []
    try:
        result = compare_mst_algorithms(graph, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AssertionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "kruskals": {
            "edges": _json_mst_edges(result["kruskals"]["edges"]),
            "total_weight": result["kruskals"]["total_weight"],
            "time_ms": result["kruskals"]["time_ms"],
            "steps": result["kruskals"]["steps"],
        },
        "prims": {
            "edges": _json_mst_edges(result["prims"]["edges"]),
            "total_weight": result["prims"]["total_weight"],
            "time_ms": result["prims"]["time_ms"],
            "steps": result["prims"]["steps"],
        },
        "total_weight": result["total_weight"],
        "faster": result["faster"],
        "note": result["note"],
        "steps": steps,
    }


def _require_source_sink(body: GraphBody) -> tuple[Hashable, Hashable]:
    source = body.source if body.source is not None else body.start
    sink = body.sink if body.sink is not None else body.goal
    if source is None or sink is None:
        raise HTTPException(
            status_code=400,
            detail="'source' and 'sink' (or start/goal) are required",
        )
    return source, sink


def _require_bipartition(body: GraphBody) -> tuple[list[NodeId], list[NodeId]]:
    if not body.left_nodes or not body.right_nodes:
        raise HTTPException(
            status_code=400,
            detail="'left_nodes' and 'right_nodes' are required",
        )
    return body.left_nodes, body.right_nodes


def _json_flow(flow: dict) -> list[dict[str, Any]]:
    return [
        {"u": u, "v": v, "flow": amount}
        for (u, v), amount in flow.items()
    ]


@router.post("/api/flows/max-flow")
def flows_max_flow(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, directed=True, weighted=True)
    source, sink = _require_source_sink(body)
    steps: list[dict[str, Any]] = []
    try:
        value, flow = ford_fulkerson(
            graph, source, sink, record_steps=steps
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "max_flow": value,
        "flow": _json_flow(flow),
        "steps": steps,
    }


@router.post("/api/flows/min-cut")
def flows_min_cut(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, directed=True, weighted=True)
    source, sink = _require_source_sink(body)
    steps: list[dict[str, Any]] = []
    try:
        value, cut_edges = min_cut(graph, source, sink, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "cut_value": value,
        "cut_edges": [
            {"u": u, "v": v, "capacity": cap} for u, v, cap in cut_edges
        ],
        "steps": steps,
    }


@router.post("/api/flows/bipartite-matching")
def flows_bipartite_matching(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, weighted=False)
    left, right = _require_bipartition(body)
    steps: list[dict[str, Any]] = []
    try:
        pairs, size = bipartite_matching(
            graph, left, right, record_steps=steps
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "matching": [{"left": u, "right": v} for u, v in pairs],
        "size": size,
        "steps": steps,
    }


@router.post("/api/flows/hopcroft-karp")
def flows_hopcroft_karp(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body, weighted=False)
    left, right = _require_bipartition(body)
    steps: list[dict[str, Any]] = []
    try:
        pairs, size = hopcroft_karp(graph, left, right, record_steps=steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "matching": [{"left": u, "right": v} for u, v in pairs],
        "size": size,
        "steps": steps,
    }


def _json_score_map(scores: dict[Hashable, float]) -> dict[str, float]:
    return {str(k): float(v) for k, v in scores.items()}


@router.post("/api/centrality/pagerank")
def centrality_pagerank(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body)
    steps: list[dict[str, Any]] = []
    try:
        ranks, iterations, history = pagerank(
            graph,
            damping=body.damping,
            max_iterations=body.max_iterations,
            tolerance=body.tolerance,
            record_steps=steps,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "ranks": _json_score_map(ranks),
        "iterations": iterations,
        "convergence_history": history,
        "steps": steps,
    }


@router.post("/api/centrality/betweenness")
def centrality_betweenness(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body)
    steps: list[dict[str, Any]] = []
    scores = betweenness_centrality(graph, record_steps=steps)
    return {
        "scores": _json_score_map(scores),
        "steps": steps,
    }


@router.post("/api/centrality/closeness")
def centrality_closeness(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body)
    steps: list[dict[str, Any]] = []
    scores = closeness_centrality(graph, record_steps=steps)
    return {
        "scores": _json_score_map(scores),
        "steps": steps,
    }


@router.post("/api/centrality/eigenvector")
def centrality_eigenvector(body: GraphBody) -> dict[str, Any]:
    graph = _build_graph(body)
    steps: list[dict[str, Any]] = []
    try:
        scores, iterations, history = eigenvector_centrality(
            graph,
            max_iterations=body.max_iterations,
            tolerance=body.tolerance,
            record_steps=steps,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "scores": _json_score_map(scores),
        "iterations": iterations,
        "convergence_history": history,
        "steps": steps,
    }


@router.get("/api/datasets/karate-club")
def dataset_karate_club() -> dict[str, Any]:
    graph = load_karate_club()
    return {
        "name": "Zachary's Karate Club",
        "directed": graph.directed,
        "weighted": graph.weighted,
        "nodes": [
            {
                "id": node,
                **graph.get_node_attrs(node),
            }
            for node in graph.get_nodes()
        ],
        "edges": [
            {"u": u, "v": v, "weight": w}
            for u, v, w in graph.get_edges()
        ],
        "num_nodes": graph.num_nodes,
        "num_edges": graph.num_edges,
    }


class GenerateGraphBody(BaseModel):
    """Request body for synthetic graph generation."""

    type: str = Field(..., description="'random' or 'grid'")
    directed: bool = False
    weighted: bool = False
    n: int = Field(default=12, ge=1, le=500)
    p: float = Field(default=0.25, ge=0.0, le=1.0)
    rows: int = Field(default=4, ge=1, le=50)
    cols: int = Field(default=4, ge=1, le=50)
    min_weight: float = 1.0
    max_weight: float = 10.0


def _serialize_graph(graph: Graph, *, name: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "directed": graph.directed,
        "weighted": graph.weighted,
        "nodes": [
            {"id": node, **graph.get_node_attrs(node)}
            for node in graph.get_nodes()
        ],
        "edges": [
            {"u": u, "v": v, "weight": w}
            for u, v, w in graph.get_edges()
        ],
        "num_nodes": graph.num_nodes,
        "num_edges": graph.num_edges,
    }
    if name is not None:
        payload["name"] = name
    return payload


@router.post("/api/graphs/generate")
def graphs_generate(body: GenerateGraphBody) -> dict[str, Any]:
    try:
        if body.type == "random":
            if body.weighted and not body.directed:
                graph = random_weighted_graph(
                    body.n, body.p, body.min_weight, body.max_weight
                )
            else:
                graph = random_graph(
                    body.n,
                    body.p,
                    directed=body.directed,
                    weighted=body.weighted,
                )
            name = f"Random ER (n={body.n}, p={body.p})"
        elif body.type == "grid":
            graph = grid_graph(body.rows, body.cols)
            # Grid generator is undirected/unweighted; surface that clearly.
            name = f"Grid ({body.rows}×{body.cols})"
        else:
            raise HTTPException(
                status_code=400,
                detail="type must be 'random' or 'grid'",
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _serialize_graph(graph, name=name)


@router.get("/api/benchmarks/results")
def benchmarks_results() -> dict[str, Any]:
    if not BENCHMARK_RESULTS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "No benchmark results found. Run "
                "`python -m benchmarks.benchmark_suite` from the backend "
                "directory first."
            ),
        )
    try:
        return json.loads(BENCHMARK_RESULTS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse benchmark results: {exc}",
        ) from exc
