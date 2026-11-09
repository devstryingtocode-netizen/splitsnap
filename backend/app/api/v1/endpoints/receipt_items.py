from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_session_owner
from app.api.v1.endpoints._docs import ERROR_RESPONSES
from app.db import get_db
from app.schemas.api import ReceiptItemCreate, ReceiptItemResponse, ReceiptItemUpdate
from app.services import api as service

router = APIRouter(tags=["receipt items"])


@router.post(
    "/receipts/{receipt_id}/items",
    response_model=ReceiptItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a receipt item",
    responses={**ERROR_RESPONSES},
)
def create_receipt_item(
    receipt_id: UUID,
    payload: ReceiptItemCreate,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> ReceiptItemResponse:
    return ReceiptItemResponse.model_validate(
        service.create_receipt_item(db, owner_id, receipt_id, payload)
    )


@router.get(
    "/receipts/{receipt_id}/items",
    response_model=list[ReceiptItemResponse],
    summary="List receipt items",
    responses={**ERROR_RESPONSES},
)
def list_receipt_items(
    receipt_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> list[ReceiptItemResponse]:
    return [
        ReceiptItemResponse.model_validate(row)
        for row in service.list_receipt_items(db, owner_id, receipt_id)
    ]


@router.patch(
    "/receipt-items/{item_id}",
    response_model=ReceiptItemResponse,
    summary="Update a receipt item",
    description="Assigned items cannot be edited until their assignments are removed.",
    responses={**ERROR_RESPONSES},
)
def update_receipt_item(
    item_id: UUID,
    payload: ReceiptItemUpdate,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> ReceiptItemResponse:
    return ReceiptItemResponse.model_validate(
        service.update_receipt_item(db, owner_id, item_id, payload)
    )


@router.delete(
    "/receipt-items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a receipt item",
    description="Assigned items cannot be deleted until their assignments are removed.",
    responses={
        **ERROR_RESPONSES,
        204: {"description": "Receipt item removed."},
    },
)
def delete_receipt_item(
    item_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> Response:
    service.delete_receipt_item(db, owner_id, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
