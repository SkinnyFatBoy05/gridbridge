import polars as pl

from gridbridge.topology.validate import validate_topology


def _nodes(*node_ids: str) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "node_id": list(node_ids),
            "node_type": ["substation" if node == "N-SUB" else "network" for node in node_ids],
            "nominal_voltage_v": [11_000 for _ in node_ids],
        }
    )


def _edges(rows: list[tuple[str, str, str]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "asset_id": [f"LINE-{index:03d}" for index in range(1, len(rows) + 1)],
            "from_node": [row[0] for row in rows],
            "to_node": [row[1] for row in rows],
            "asset_type": ["line" for _ in rows],
            "status": [row[2] for row in rows],
        }
    )


def test_dangling_edge_is_reported_without_crashing_graph_checks() -> None:
    """A client GIS export often references assets absent from the node layer."""
    result = validate_topology(
        _nodes("N-SUB", "N-001"),
        _edges([("N-SUB", "N-001", "energized"), ("N-001", "MISSING", "energized")]),
    )

    assert not result.valid
    assert {issue.code for issue in result.issues} == {"GIS_DANGLING_NODE"}
    assert result.energized_nodes == 2


def test_radial_feeder_cycle_and_disconnected_node_are_both_reported() -> None:
    """Returning all topology defects avoids a fix-one-rerun-one client loop."""
    result = validate_topology(
        _nodes("N-SUB", "N-001", "N-002", "N-ORPHAN"),
        _edges(
            [
                ("N-SUB", "N-001", "energized"),
                ("N-001", "N-002", "energized"),
                ("N-002", "N-SUB", "energized"),
            ]
        ),
    )

    assert {issue.code for issue in result.issues} == {
        "GIS_UNEXPECTED_CYCLE",
        "GIS_DISCONNECTED_NODE",
    }


def test_deenergized_segment_is_modelled_but_not_available_path() -> None:
    """A valid asset can be unavailable operationally without being deleted."""
    result = validate_topology(
        _nodes("N-SUB", "N-001"),
        _edges([("N-SUB", "N-001", "deenergized")]),
    )

    assert not result.valid
    assert result.energized_edges == 0
    assert [issue.code for issue in result.issues] == ["GIS_DISCONNECTED_NODE"]
