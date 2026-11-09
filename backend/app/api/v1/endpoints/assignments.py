from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_session_owner
from app.api.v1.endpoints._docs import ERROR_RESPONSES
from app.db import get_db
from app.schemas.api import AssignmentCreate, AssignmentResponse, AssignmentUpdate
from app.services import api as service

router = APIRouter(tags=["assignments"])


@router.post(
    "/receipt-items/{item_id}/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign an item to a participant",
    description="The participant must belong to the same bill session as the item.",
    responses={**ERROR_RESPONSES},
)
def create_assignment(
    item_id: UUID,
    payload: AssignmentCreate,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> AssignmentResponse:
    return AssignmentResponse.model_validate(
        service.create_assignment(db, owner_id, item_id, payload)
    )


@router.get(
    "/receipt-items/{item_id}/assignments",
    response_model=list[AssignmentResponse],
    summary="List assignments for an item",
    responses={**ERROR_RESPONSES},
)
def list_assignments(
    item_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> list[AssignmentResponse]:
    return [
        AssignmentResponse.model_validate(row)
        for row in service.list_assignments(db, owner_id, item_id)
    ]


@router.patch(
    "/assignments/{assignment_id}",
    response_model=AssignmentResponse,
    summary="Update an assignment",
    description="Any replacement participant must belong to the item's session.",
    responses={**ERROR_RESPONSES},
)
def update_assignment(
    assignment_id: UUID,
    payload: AssignmentUpdate,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> AssignmentResponse:
    return AssignmentResponse.model_validate(
        service.update_assignment(db, owner_id, assignment_id, payload)
    )


@router.delete(
    "/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an assignment",
    responses={
        **ERROR_RESPONSES,
        204: {"description": "Assignment removed."},
    },
)
def delete_assignment(
    assignment_id: UUID,
    owner_id: UUID = Depends(get_current_session_owner),
    db: Session = Depends(get_db),
) -> Response:
    service.delete_assignment(db, owner_id, assignment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
