from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_session_owner
from app.api.v1.endpoints._docs import ERROR_RESPONSES
from app.db import get_db
from app.schemas.api import ParticipantCreate, ParticipantResponse, ParticipantUpdate
from app.services import api as service

router = APIRouter(tags=["participants"])


@router.post(
    "/sessions/{session_id}/participants",
    response_model=ParticipantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a participant",
    responses={**ERROR_RESPONSES},
)
def create_participant(
    session_id: UUID,
    payload: ParticipantCreate,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> ParticipantResponse:
    return ParticipantResponse.model_validate(
        service.add_participant(db, owner_id, session_id, payload)
    )


@router.get(
    "/sessions/{session_id}/participants",
    response_model=list[ParticipantResponse],
    summary="List session participants",
    responses={**ERROR_RESPONSES},
)
def list_participants(
    session_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> list[ParticipantResponse]:
    return [
        ParticipantResponse.model_validate(row)
        for row in service.list_participants(db, owner_id, session_id)
    ]


@router.get(
    "/participants/{participant_id}",
    response_model=ParticipantResponse,
    summary="Get a participant",
    responses={**ERROR_RESPONSES},
)
def get_participant(
    participant_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> ParticipantResponse:
    return ParticipantResponse.model_validate(
        service.get_participant(db, owner_id, participant_id)
    )


@router.patch(
    "/participants/{participant_id}",
    response_model=ParticipantResponse,
    summary="Update a participant",
    responses={**ERROR_RESPONSES},
)
def update_participant(
    participant_id: UUID,
    payload: ParticipantUpdate,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> ParticipantResponse:
    return ParticipantResponse.model_validate(
        service.update_participant(db, owner_id, participant_id, payload)
    )


@router.delete(
    "/participants/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a participant",
    description="Refuses deletion when historical split or invoice records exist.",
    responses={
        **ERROR_RESPONSES,
        204: {"description": "Participant removed."},
    },
)
def delete_participant(
    participant_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> Response:
    service.delete_participant(db, owner_id, participant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
