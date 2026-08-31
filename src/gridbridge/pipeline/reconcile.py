"""Fail-closed source-to-canonical row reconciliation."""

from gridbridge.models import ReconciliationResult, SourceName


class ReconciliationError(RuntimeError):
    """Raised when landed rows cannot be accounted for exactly."""


def reconcile_source(
    source: SourceName,
    landed: int,
    accepted: int,
    quarantined: int,
    loaded: int,
) -> ReconciliationResult:
    """Require both source resolution and accepted-to-loaded equality."""

    balanced = landed == accepted + quarantined and accepted == loaded
    if not balanced:
        raise ReconciliationError(
            f"{source.value} reconciliation failed: landed={landed}, accepted={accepted}, "
            f"quarantined={quarantined}, loaded={loaded}"
        )
    return ReconciliationResult(
        source=source,
        landed=landed,
        accepted=accepted,
        quarantined=quarantined,
        loaded=loaded,
        balanced=True,
    )
