import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.api import AuthTokenResponse, LoginRequest, RegisterRequest, UserResponse

logger = logging.getLogger(__name__)
_DUMMY_PASSWORD_HASH = hash_password("not-a-real-user-password")


def register_user(db: Session, payload: RegisterRequest) -> User:
    normalized_email = payload.email.strip().lower()
    existing = db.scalar(
        select(User.id).where(func.lower(User.email) == normalized_email)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        name=payload.name,
        email=normalized_email,
        password_hash=hash_password(payload.password),
        is_active=True,
        email_verified=False,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("User registration database operation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The account could not be created.",
        ) from exc
    return user


def authenticate_user(db: Session, payload: LoginRequest) -> AuthTokenResponse:
    normalized_email = payload.email.strip().lower()
    user = db.scalar(
        select(User).where(func.lower(User.email) == normalized_email)
    )
    password_is_valid = verify_password(
        payload.password,
        (
            user.password_hash
            if user is not None and user.password_hash is not None
            else _DUMMY_PASSWORD_HASH
        ),
    )
    if (
        user is None
        or not user.is_active
        or not password_is_valid
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)
    user.last_login_at = datetime.now(UTC)
    try:
        db.commit()
        db.refresh(user)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("User login database operation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The login could not be completed.",
        ) from exc

    return AuthTokenResponse(
        access_token=access_token,
        expires_in=get_settings().access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )
