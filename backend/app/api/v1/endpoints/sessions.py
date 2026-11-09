from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_session_owner
from app.api.v1.endpoints._docs import ERROR_RESPONSES
from app.db import get_db
from app.schemas.api import (
    SessionCreate,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)
from app.services import api as service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a bill session",
    description=(
        "Creates a draft session owned by the authenticated user. "
        "Ownership is never accepted from the request."
    ),
    responses={**ERROR_RESPONSES},
)
def create_session(
    payload: SessionCreate,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> SessionResponse:
    return SessionResponse.model_validate(
        service.create_session(db, owner_id, payload)
    )


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List bill sessions",
    responses={**ERROR_RESPONSES},
)
def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> SessionListResponse:
    return SessionListResponse.model_validate(
        service.list_sessions(db, owner_id, limit=limit, offset=offset)
    )


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get a bill session",
    responses={**ERROR_RESPONSES},
)
def get_session(
    session_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> SessionDetailResponse:
    return SessionDetailResponse.model_validate(
        service.get_session(db, owner_id, session_id)
    )


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Update a bill session",
    description="Updates its title or currency while financial records permit it.",
    responses={**ERROR_RESPONSES},
)
def update_session(
    session_id: UUID,
    payload: SessionUpdate,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> SessionResponse:
    return SessionResponse.model_validate(
        service.update_session(db, owner_id, session_id, payload)
    )


@router.post(
    "/{session_id}/cancel",
    response_model=SessionResponse,
    summary="Cancel a bill session",
    description="Cancels only sessions in an eligible pre-invoice state.",
    responses={**ERROR_RESPONSES},
)
def cancel_session(
    session_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> SessionResponse:
    return SessionResponse.model_validate(
        service.cancel_session(db, owner_id, session_id)
    )
