"""Lightweight feeder plausibility checks, not electrical load-flow simulation."""

from __future__ import annotations

import networkx as nx
import polars as pl
from pydantic import BaseModel, ConfigDict


class TopologyIssue(BaseModel):
    """One actionable network-model defect."""

    model_config = ConfigDict(frozen=True)

    code: str
    detail: str
    asset_id: str | None = None


class TopologyResult(BaseModel):
    """Aggregate feeder graph health for safety gating and reports."""

    model_config = ConfigDict(frozen=True)

    valid: bool
    issues: list[TopologyIssue]
    energized_nodes: int
    energized_edges: int


def validate_topology(
    nodes: pl.DataFrame,
    edges: pl.DataFrame,
    substation_node: str = "N-SUB",
) -> TopologyResult:
    """Return all dangling, cycle, and energized-connectivity defects."""

    node_ids = {str(value) for value in nodes["node_id"].to_list()}
    graph: nx.Graph[str] = nx.Graph()
    graph.add_nodes_from(node_ids)
    issues: list[TopologyIssue] = []

    for edge in edges.to_dicts():
        if edge.get("status") != "energized":
            continue
        start = str(edge["from_node"])
        end = str(edge["to_node"])
        missing = sorted({node for node in (start, end) if node not in node_ids})
        if missing:
            issues.append(
                TopologyIssue(
                    code="GIS_DANGLING_NODE",
                    asset_id=str(edge.get("asset_id")),
                    detail=f"edge references missing nodes: {', '.join(missing)}",
                )
            )
            continue
        graph.add_edge(start, end, asset_id=str(edge.get("asset_id")))

    if nx.cycle_basis(graph):
        issues.append(
            TopologyIssue(
                code="GIS_UNEXPECTED_CYCLE",
                detail="energized feeder expected to be radial contains a cycle",
            )
        )

    if substation_node not in graph:
        issues.append(
            TopologyIssue(
                code="GIS_SUBSTATION_MISSING",
                detail=f"substation node {substation_node} is absent",
            )
        )
        reachable: set[str] = set()
    else:
        reachable = set(nx.node_connected_component(graph, substation_node))
        disconnected = sorted(node_ids - reachable)
        if disconnected:
            issues.append(
                TopologyIssue(
                    code="GIS_DISCONNECTED_NODE",
                    detail=f"nodes have no energized path to substation: {', '.join(disconnected)}",
                )
            )

    return TopologyResult(
        valid=not issues,
        issues=issues,
        energized_nodes=len(reachable),
        energized_edges=graph.subgraph(reachable).number_of_edges(),
    )
