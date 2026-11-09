from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.endpoints._docs import ERROR_RESPONSES
from app.db import get_db
from app.schemas.api import PaymentResponse
from app.services import api as service

router = APIRouter(tags=["payments"])


@router.get(
    "/sessions/{session_id}/payments",
    response_model=list[PaymentResponse],
    summary="List session payment records",
    description="Returns stored payment records; no payment status can be changed.",
    responses={**ERROR_RESPONSES},
)
def list_session_payments(
    session_id: UUID,
    db: Session = Depends(get_db),
) -> list[PaymentResponse]:
    return [
        PaymentResponse.model_validate(row)
        for row in service.list_session_payments(db, session_id)
    ]
