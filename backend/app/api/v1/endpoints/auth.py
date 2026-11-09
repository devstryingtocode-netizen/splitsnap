from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_active_user
from app.db import get_db
from app.models import User
from app.schemas.api import (
    AuthTokenResponse,
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    UserResponse,
)
from app.services import auth as service

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an account",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    user = service.register_user(db, payload)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="Log in with email and password",
    description=(
        "Accepts a JSON email/password body and returns a short-lived OAuth2 "
        "bearer access token."
    ),
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    return service.authenticate_user(db, payload)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated profile",
)
def me(user: User = Depends(get_active_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Log out the current client",
    description=(
        "Stateless access tokens remain valid until expiry. The client must "
        "discard its token; this endpoint does not revoke copied tokens."
    ),
)
def logout(user: User = Depends(get_active_user)) -> LogoutResponse:
    return LogoutResponse(
        message="Logged out locally. Discard the access token; it remains valid until expiry."
    )
