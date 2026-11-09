from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    BillSession,
    BillSessionStatus,
    BillSplit,
    ItemAssignment,
    ItemShareType,
    Participant,
    Payment,
    PaymentStatus,
    PayPalInvoice,
    PayPalInvoiceStatus,
    Receipt,
    ReceiptExtractionStatus,
    ReceiptItem,
    User,
)


def create_bill(session: Session) -> tuple[User, BillSession, Participant, Receipt, ReceiptItem]:
    user = User(name="Taylor", email="taylor@example.test")
    bill_session = BillSession(owner=user, title="Dinner", currency="EUR")
    participant = Participant(
        bill_session=bill_session,
        name="Morgan",
        email="morgan@example.test",
        paypal_email="morgan-payments@example.test",
    )
    receipt = Receipt(
        bill_session=bill_session,
        original_filename="dinner.png",
        mime_type="image/png",
        storage_key="receipts/dinner.png",
        extraction_status=ReceiptExtractionStatus.COMPLETED,
        currency="EUR",
        subtotal=Decimal("25.10"),
        tax_amount=Decimal("2.01"),
        tip_amount=Decimal("3.00"),
        total_amount=Decimal("30.11"),
    )
    item = ReceiptItem(
        receipt=receipt,
        name="Pasta",
        quantity=Decimal("1.000"),
        unit_price=Decimal("25.10"),
        total_price=Decimal("25.10"),
    )
    session.add(user)
    session.flush()
    return user, bill_session, participant, receipt, item


def test_user_creation_and_unique_email(db_session: Session) -> None:
    user = User(name="Taylor", email="taylor@example.test")
    db_session.add(user)
    db_session.commit()

    loaded = db_session.scalar(select(User).where(User.email == user.email))
    assert loaded is not None
    assert loaded.id is not None
    assert loaded.created_at.tzinfo == timezone.utc
    assert loaded.updated_at.tzinfo == timezone.utc

    db_session.add(User(name="Another Taylor", email="taylor@example.test"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_bill_participants_receipt_and_items_relationships(db_session: Session) -> None:
    user, bill_session, participant, receipt, item = create_bill(db_session)

    assert bill_session.owner is user
    assert user.bill_sessions == [bill_session]
    assert bill_session.participants == [participant]
    assert participant.bill_session is bill_session
    assert participant.email != participant.paypal_email
    assert bill_session.receipt is receipt
    assert receipt.bill_session is bill_session
    assert receipt.items == [item]
    assert item.receipt is receipt
    assert receipt.storage_key == "receipts/dinner.png"


def test_item_assignment_relationship_and_duplicate_constraint(
    db_session: Session,
) -> None:
    _, _, participant, _, item = create_bill(db_session)
    assignment = ItemAssignment(
        receipt_item=item,
        participant=participant,
        quantity=Decimal("1.250"),
        share_type=ItemShareType.QUANTITY_BASED,
    )
    db_session.add(assignment)
    db_session.commit()

    assert item.assignments == [assignment]
    assert participant.item_assignments == [assignment]
    assert assignment.receipt_item is item
    assert assignment.participant is participant
    assert assignment.quantity == Decimal("1.250")

    db_session.add(
        ItemAssignment(
            receipt_item=item,
            participant=participant,
            quantity=Decimal("1"),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_split_invoice_and_payment_relationships(db_session: Session) -> None:
    _, bill_session, participant, _, _ = create_bill(db_session)
    split = BillSplit(
        bill_session=bill_session,
        participant=participant,
        subtotal=Decimal("25.10"),
        tax_share=Decimal("2.01"),
        tip_share=Decimal("3.00"),
        service_charge_share=Decimal("0.00"),
        total_owed=Decimal("30.11"),
        currency="EUR",
        calculation_version="v1",
    )
    invoice = PayPalInvoice(
        bill_session=bill_session,
        participant=participant,
        bill_split=split,
        paypal_invoice_id="PAYPAL-INV-001",
        invoice_number="INV-001",
        invoice_status=PayPalInvoiceStatus.SENT,
        amount=Decimal("30.11"),
        currency="EUR",
        invoice_url="https://example.test/invoice",
        sent_at=datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc),
    )
    payment = Payment(
        paypal_invoice=invoice,
        external_payment_id="PAYMENT-001",
        amount=Decimal("30.11"),
        currency="EUR",
        status=PaymentStatus.COMPLETED,
        payment_method="paypal",
        paid_at=datetime(2026, 11, 8, 13, 0, tzinfo=timezone.utc),
    )
    db_session.add(split)
    db_session.flush()
    db_session.add(invoice)
    db_session.flush()
    db_session.add(payment)
    db_session.commit()

    assert bill_session.bill_splits == [split]
    assert participant.bill_splits == [split]
    assert split.paypal_invoice is invoice
    assert invoice.bill_session is bill_session
    assert invoice.participant is participant
    assert invoice.bill_split is split
    assert invoice.payments == [payment]
    assert payment.paypal_invoice is invoice
    assert invoice.sent_at is not None
    assert invoice.sent_at.tzinfo == timezone.utc
    assert payment.paid_at is not None
    assert payment.paid_at.tzinfo == timezone.utc


def test_unique_split_constraint(db_session: Session) -> None:
    _, bill_session, participant, _, _ = create_bill(db_session)
    split = BillSplit(
        bill_session=bill_session,
        participant=participant,
        subtotal=Decimal("1.00"),
        tax_share=Decimal("0.00"),
        tip_share=Decimal("0.00"),
        service_charge_share=Decimal("0.00"),
        total_owed=Decimal("1.00"),
        currency="USD",
        calculation_version="v1",
    )
    db_session.add(split)
    db_session.commit()

    duplicate = BillSplit(
        bill_session=bill_session,
        participant=participant,
        subtotal=Decimal("1.00"),
        tax_share=Decimal("0.00"),
        tip_share=Decimal("0.00"),
        service_charge_share=Decimal("0.00"),
        total_owed=Decimal("1.00"),
        currency="USD",
        calculation_version="v1",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_paypal_invoice_and_payment_external_ids_are_unique(
    db_session: Session,
) -> None:
    _, bill_session, participant, _, _ = create_bill(db_session)
    split = BillSplit(
        bill_session=bill_session,
        participant=participant,
        subtotal=Decimal("25.10"),
        tax_share=Decimal("2.01"),
        tip_share=Decimal("3.00"),
        service_charge_share=Decimal("0.00"),
        total_owed=Decimal("30.11"),
        currency="EUR",
        calculation_version="v1",
    )
    second_participant = Participant(bill_session=bill_session, name="Casey")
    second_split = BillSplit(
        bill_session=bill_session,
        participant=second_participant,
        subtotal=Decimal("25.10"),
        tax_share=Decimal("2.01"),
        tip_share=Decimal("3.00"),
        service_charge_share=Decimal("0.00"),
        total_owed=Decimal("30.11"),
        currency="EUR",
        calculation_version="v1",
    )
    invoice = PayPalInvoice(
        bill_session=bill_session,
        participant=participant,
        bill_split=split,
        paypal_invoice_id="PAYPAL-UNIQUE-001",
        amount=Decimal("30.11"),
        currency="EUR",
    )
    payment = Payment(
        paypal_invoice=invoice,
        external_payment_id="PAYMENT-UNIQUE-001",
        amount=Decimal("30.11"),
        currency="EUR",
    )
    db_session.add_all([split, second_split, invoice, payment])
    db_session.commit()

    duplicate_invoice = PayPalInvoice(
        bill_session=bill_session,
        participant=second_participant,
        bill_split=second_split,
        paypal_invoice_id="PAYPAL-UNIQUE-001",
        amount=Decimal("30.11"),
        currency="EUR",
    )
    db_session.add(duplicate_invoice)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    db_session.add(
        Payment(
            paypal_invoice=invoice,
            external_payment_id="PAYMENT-UNIQUE-001",
            amount=Decimal("30.11"),
            currency="EUR",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_decimal_precision_and_sqlite_foreign_key_integrity(db_session: Session) -> None:
    user, bill_session, _, receipt, item = create_bill(db_session)
    bill_session.total_amount = Decimal("1234567890.12")
    item.unit_price = Decimal("1234567890.12")
    item.total_price = Decimal("1234567890.12")
    db_session.commit()
    db_session.expire_all()

    assert db_session.get(BillSession, bill_session.id).total_amount == Decimal(
        "1234567890.12"
    )
    assert db_session.get(ReceiptItem, item.id).unit_price == Decimal("1234567890.12")
    assert db_session.get(Receipt, receipt.id).total_amount == Decimal("30.11")
    assert db_session.get(User, user.id) is not None

    db_session.add(
        Participant(
            bill_session_id=uuid4(),
            name="Orphan",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_database_constraints_reject_invalid_amounts_and_currency(
    db_session: Session,
) -> None:
    user = User(name="Taylor", email="taylor@example.test")
    db_session.add(user)
    db_session.flush()

    db_session.add(
        BillSession(
            owner=user,
            title="Invalid bill",
            currency="usd",
            status=BillSessionStatus.DRAFT,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
