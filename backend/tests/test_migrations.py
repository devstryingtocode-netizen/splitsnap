from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import create_database_engine
from app.models import BillSession, BillSplit, Participant, Payment, PayPalInvoice, User


def test_migration_upgrade_downgrade_and_reupgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))

    try:
        command.upgrade(config, "head")
        engine = create_database_engine(database_url)
        try:
            inspector = inspect(engine)
            assert {
                "users",
                "bill_sessions",
                "participants",
                "receipts",
                "receipt_items",
                "item_assignments",
                "bill_splits",
                "paypal_invoices",
                "payments",
            }.issubset(set(inspector.get_table_names()))
            assert inspector.get_foreign_keys("payments")
            assert inspector.get_indexes("users")
        finally:
            engine.dispose()

        command.downgrade(config, "base")
        engine = create_database_engine(database_url)
        try:
            assert inspect(engine).get_table_names() == ["alembic_version"]
        finally:
            engine.dispose()

        command.upgrade(config, "head")
        engine = create_database_engine(database_url)
        try:
            assert "paypal_invoices" in inspect(engine).get_table_names()
        finally:
            engine.dispose()
    finally:
        get_settings.cache_clear()


def test_history_migration_preserves_records_and_blocks_participant_delete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{tmp_path / 'history-migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    engine = create_database_engine(database_url)

    try:
        command.upgrade(config, "f0bafed4c28a")
        with Session(engine) as session:
            owner = User(name="History owner", email="history-owner@example.test")
            bill_session = BillSession(
                owner=owner,
                title="Historical dinner",
                currency="USD",
            )
            participant = Participant(
                bill_session=bill_session,
                name="Billed participant",
            )
            bill_split = BillSplit(
                bill_session=bill_session,
                participant=participant,
                subtotal=Decimal("10.00"),
                tax_share=Decimal("0.80"),
                tip_share=Decimal("2.00"),
                service_charge_share=Decimal("0.00"),
                total_owed=Decimal("12.80"),
                currency="USD",
                calculation_version="test-v1",
            )
            session.add(bill_split)
            session.flush()
            invoice = PayPalInvoice(
                bill_session=bill_session,
                participant=participant,
                bill_split=bill_split,
                paypal_invoice_id="MIGRATION-HISTORY-INV",
                amount=Decimal("12.80"),
                currency="USD",
            )
            session.add(invoice)
            session.flush()
            payment = Payment(
                paypal_invoice=invoice,
                external_payment_id="MIGRATION-HISTORY-PAY",
                amount=Decimal("12.80"),
                currency="USD",
            )
            session.add(payment)
            session.commit()
            participant_id = participant.id

        command.upgrade(config, "head")
        with Session(engine) as session:
            assert session.query(BillSplit).count() == 1
            assert session.query(PayPalInvoice).count() == 1
            assert session.query(Payment).count() == 1
            participant = session.get(Participant, participant_id)
            assert participant is not None
            session.delete(participant)
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
            assert session.query(BillSplit).count() == 1
            assert session.query(PayPalInvoice).count() == 1
            assert session.query(Payment).count() == 1
    finally:
        engine.dispose()
        get_settings.cache_clear()
