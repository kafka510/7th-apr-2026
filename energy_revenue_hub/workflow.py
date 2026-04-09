"""
Billing workflow state machine – forward transitions.

States: DRAFT → FILTER_VALIDATED → PDF_UPLOADED → PARSED → REVIEWED → GENERATED → POSTED

Includes pragmatic shortcuts so `services/billing_service.py` and `services/invoice_service.py`
can run end-to-end without forcing upload/parse steps (e.g. FILTER_VALIDATED → REVIEWED).
"""

from energy_revenue_hub.models import BillingSession

TRANSITIONS = {
    BillingSession.Status.DRAFT: [BillingSession.Status.FILTER_VALIDATED],
    BillingSession.Status.FILTER_VALIDATED: [
        BillingSession.Status.PDF_UPLOADED,
        # Pragmatic: build billing line items without PDF upload/parse (peakpulse billing_service).
        BillingSession.Status.REVIEWED,
    ],
    BillingSession.Status.PDF_UPLOADED: [BillingSession.Status.PARSED],
    BillingSession.Status.PARSED: [BillingSession.Status.REVIEWED],
    BillingSession.Status.REVIEWED: [BillingSession.Status.GENERATED],
    # Allow return to REVIEWED after invoice (unfreeze / recompute before re-issuing).
    BillingSession.Status.GENERATED: [BillingSession.Status.POSTED, BillingSession.Status.REVIEWED],
    BillingSession.Status.POSTED: [],
}


def can_transition(session: BillingSession, target_status: str) -> bool:
    """Check if transition from current status to target_status is allowed."""
    if not session or not target_status:
        return False
    allowed = TRANSITIONS.get(session.status, [])
    return target_status in allowed


def transition_to(session: BillingSession, target_status: str) -> bool:
    """
    Attempt to transition session to target_status.
    Returns True if transition was applied, False otherwise.
    """
    if not can_transition(session, target_status):
        return False
    session.status = target_status
    session.save(update_fields=["status", "updated_at"])
    return True
