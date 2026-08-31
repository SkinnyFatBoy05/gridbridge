import pytest

from gridbridge.models import SourceName
from gridbridge.pipeline.reconcile import ReconciliationError, reconcile_source


def test_reconciliation_balances_landed_accepted_and_quarantined_rows() -> None:
    """Every landed row must resolve to accepted or quarantined evidence."""
    result = reconcile_source(
        SourceName.METER,
        landed=10,
        accepted=8,
        quarantined=2,
        loaded=8,
    )

    assert result.balanced
    assert result.model_dump() == {
        "source": "meter",
        "landed": 10,
        "accepted": 8,
        "quarantined": 2,
        "loaded": 8,
        "balanced": True,
    }


def test_reconciliation_rejects_unaccounted_source_rows() -> None:
    """A missing row is an integrity failure, not an acceptable warning."""
    with pytest.raises(ReconciliationError, match=r"meter.*landed=10.*accepted=8.*quarantined=1"):
        reconcile_source(
            SourceName.METER,
            landed=10,
            accepted=8,
            quarantined=1,
            loaded=8,
        )


def test_reconciliation_rejects_loaded_count_different_from_accepted() -> None:
    """A load that silently drops an accepted row must fail closed."""
    with pytest.raises(ReconciliationError, match="loaded=7"):
        reconcile_source(
            SourceName.DER,
            landed=10,
            accepted=8,
            quarantined=2,
            loaded=7,
        )
