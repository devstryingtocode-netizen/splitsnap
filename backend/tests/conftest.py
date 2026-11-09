from collections.abc import Iterator

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db import get_db
from app.db.session import create_database_engine
from app.models import Base
from app.main import app
from app.models import User


@pytest.fixture
def db_engine() -> Iterator[Engine]:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    with Session(db_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def api_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, Engine, UUID]]:
    owner_id = uuid4()
    monkeypatch.setenv("DEVELOPMENT_OWNER_ID", str(owner_id))
    get_settings.cache_clear()

    engine = create_database_engine(f"sqlite:///{tmp_path / 'api-test.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with factory() as session:
        session.add(
            User(
                id=owner_id,
                name="API Test Owner",
                email="api-owner@example.test",
            )
        )
        session.commit()

    def override_get_db() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, engine, owner_id
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
        get_settings.cache_clear()
