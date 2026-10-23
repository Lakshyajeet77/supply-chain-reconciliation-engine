"""Run deterministic reconciliation against structured payloads."""

import time
import uuid

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.logging_config import get_logger
from app.schemas.reconciliation import ReconciliationInput, ReconciliationResult
from app.services.reconciliation.engine import reconcile
from app.services.reconciliation.policies import ReconciliationPolicies

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])
logger = get_logger(__name__)


@router.post("/run", response_model=ReconciliationResult)
def run_reconciliation(
    payload: ReconciliationInput,
    settings: Settings = Depends(get_settings),
) -> ReconciliationResult:
    """
    Compare provided structured documents using deterministic rules.

    This endpoint does not authorize payments. MATCHED requires a purchase
    order and invoice (and successful rule checks); an invoice alone never matches.
    """
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    policies = ReconciliationPolicies(
        money_decimal_places=settings.money_decimal_places,
        price_tolerance=settings.price_tolerance,
        quantity_tolerance=settings.quantity_tolerance,
    )
    result = reconcile(payload, policies=policies)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "Reconciliation completed run_id=%s status=%s discrepancies=%s duration_ms=%.1f",
        run_id,
        result.status.value,
        len(result.discrepancies),
        elapsed_ms,
    )
    return result
