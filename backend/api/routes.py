"""HTTP routes for graph algorithms."""

from __future__ import annotations

from typing import Any, Hashable, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from algorithms.traversal import (
    bfs,
    dfs,
    find_articulation_points,
    find_bridges,
    tarjan_scc,
)
from graph_core.graph import Graph

router = APIRouter()

NodeId = Union[int, str]


class GraphBody(BaseModel):
    """Shared request body for traversal endpoints."""

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


def _build_graph(
    body: GraphBody,
    *,
    directed: Optional[bool] = None,
) -> Graph:
    is_directed = body.directed if directed is None else directed
    graph = Graph(directed=is_directed, weighted=body.weighted)
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
    return graph


def _require_start(body: GraphBody) -> Hashable:
    if body.start is None:
        raise HTTPException(status_code=400, detail="'start' node is required")
    return body.start


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
