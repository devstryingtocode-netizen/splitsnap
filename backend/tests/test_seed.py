import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    BillSession,
    ItemAssignment,
    Participant,
    Receipt,
    ReceiptItem,
    User,
)
from app.seed import main, seed_development_data


def test_development_seed_is_idempotent(db_session: Session) -> None:
    seed_development_data(db_session)
    db_session.commit()
    seed_development_data(db_session)
    db_session.commit()

    assert db_session.scalar(select(func.count()).select_from(User)) == 1
    assert db_session.scalar(select(func.count()).select_from(BillSession)) == 1
    assert db_session.scalar(select(func.count()).select_from(Participant)) == 3
    assert db_session.scalar(select(func.count()).select_from(Receipt)) == 1
    assert db_session.scalar(select(func.count()).select_from(ReceiptItem)) == 4
    assert db_session.scalar(select(func.count()).select_from(ItemAssignment)) == 6


def test_seed_refuses_non_development_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        with pytest.raises(SystemExit, match="Refusing to seed"):
            main()
    finally:
        get_settings.cache_clear()
