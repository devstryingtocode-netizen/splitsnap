from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_session_owner
from app.api.v1.endpoints._docs import ERROR_RESPONSES
from app.db import get_db
from app.schemas.api import PayPalInvoiceResponse, PaymentResponse
from app.services import api as service

router = APIRouter(tags=["invoices"])


@router.get(
    "/sessions/{session_id}/invoices",
    response_model=list[PayPalInvoiceResponse],
    summary="List stored session invoices",
    description="Returns database records only; this endpoint does not create invoices.",
    responses={**ERROR_RESPONSES},
)
def list_session_invoices(
    session_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> list[PayPalInvoiceResponse]:
    return [
        PayPalInvoiceResponse.model_validate(row)
        for row in service.list_session_invoices(db, owner_id, session_id)
    ]


@router.get(
    "/invoices/{invoice_id}",
    response_model=PayPalInvoiceResponse,
    summary="Get a stored invoice",
    responses={**ERROR_RESPONSES},
)
def get_invoice(
    invoice_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> PayPalInvoiceResponse:
    return PayPalInvoiceResponse.model_validate(
        service.get_invoice(db, owner_id, invoice_id)
    )


@router.get(
    "/invoices/{invoice_id}/payments",
    response_model=list[PaymentResponse],
    summary="List an invoice's payment records",
    description="Returns stored payment events; invoice status cannot be set here.",
    responses={**ERROR_RESPONSES},
)
def list_invoice_payments(
    invoice_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> list[PaymentResponse]:
    return [
        PaymentResponse.model_validate(row)
        for row in service.list_invoice_payments(db, owner_id, invoice_id)
    ]
