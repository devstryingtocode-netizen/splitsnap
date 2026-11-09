from fastapi import APIRouter
from fastapi import Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_session_owner
from uuid import UUID

from app.api.v1.endpoints._docs import ERROR_RESPONSES
from app.db import get_db
from app.schemas.api import ReceiptCreate, ReceiptResponse, ReceiptUpdate
from app.services import api as service

router = APIRouter(tags=["receipts"])


@router.post(
    "/sessions/{session_id}/receipts",
    response_model=ReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create receipt metadata",
    description=(
        "Stores a receipt storage reference and metadata only. It does not upload "
        "or process an image; extraction status remains pending."
    ),
    responses={**ERROR_RESPONSES},
)
def create_session_receipt(
    session_id: UUID,
    payload: ReceiptCreate,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> ReceiptResponse:
    receipt = service.create_receipt(db, owner_id, session_id, payload)
    return ReceiptResponse.model_validate(receipt)


@router.get(
    "/sessions/{session_id}/receipts",
    response_model=ReceiptResponse,
    summary="Get session receipt metadata",
    responses={**ERROR_RESPONSES},
)
def get_session_receipt(
    session_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> ReceiptResponse:
    receipt = service.get_receipt_for_session(db, owner_id, session_id)
    return ReceiptResponse.model_validate(receipt)


@router.get(
    "/receipts/{receipt_id}",
    response_model=ReceiptResponse,
    summary="Get receipt and items",
    responses={**ERROR_RESPONSES},
)
def get_receipt(
    receipt_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> ReceiptResponse:
    receipt = service.get_receipt(db, owner_id, receipt_id)
    return ReceiptResponse.model_validate(receipt)


@router.patch(
    "/receipts/{receipt_id}",
    response_model=ReceiptResponse,
    summary="Update receipt metadata",
    description=(
        "Updates stored metadata. Extraction status is not client-editable; this "
        "API does not claim that a receipt has been scanned."
    ),
    responses={**ERROR_RESPONSES},
)
def update_receipt(
    receipt_id: UUID,
    payload: ReceiptUpdate,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> ReceiptResponse:
    receipt = service.update_receipt(db, owner_id, receipt_id, payload)
    return ReceiptResponse.model_validate(receipt)
