from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.endpoints._docs import ERROR_RESPONSES
from app.db import get_db
from app.schemas.api import BillSplitResponse
from app.services import api as service

router = APIRouter(tags=["splits"])


@router.get(
    "/sessions/{session_id}/splits",
    response_model=list[BillSplitResponse],
    summary="List stored bill splits",
    description="Returns stored records only; this API does not calculate shares.",
    responses={**ERROR_RESPONSES},
)
def list_splits(
    session_id: UUID,
    db: Session = Depends(get_db),
) -> list[BillSplitResponse]:
    return [
        BillSplitResponse.model_validate(row)
        for row in service.list_session_splits(db, session_id)
    ]
