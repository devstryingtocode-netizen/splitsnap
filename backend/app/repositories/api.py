from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    BillSession,
    BillSplit,
    ItemAssignment,
    Participant,
    Payment,
    PayPalInvoice,
    Receipt,
    ReceiptItem,
)


def get_session(
    db: Session, owner_id: UUID, session_id: UUID
) -> BillSession | None:
    statement = (
        select(BillSession)
        .where(BillSession.id == session_id, BillSession.owner_id == owner_id)
        .options(
            selectinload(BillSession.participants),
            selectinload(BillSession.receipt),
        )
    )
    return db.scalar(statement)


def list_sessions(
    db: Session, owner_id: UUID, limit: int, offset: int
) -> tuple[list[BillSession], int]:
    total = db.scalar(
        select(func.count()).select_from(BillSession).where(BillSession.owner_id == owner_id)
    )
    rows = db.scalars(
        select(BillSession)
        .where(BillSession.owner_id == owner_id)
        .options(selectinload(BillSession.participants), selectinload(BillSession.receipt))
        .order_by(BillSession.created_at.desc(), BillSession.id)
        .limit(limit)
        .offset(offset)
    )
    return list(rows), total or 0


def get_participant(
    db: Session, owner_id: UUID, participant_id: UUID
) -> Participant | None:
    statement = (
        select(Participant)
        .join(Participant.bill_session)
        .where(
            Participant.id == participant_id,
            BillSession.owner_id == owner_id,
        )
    )
    return db.scalar(statement)


def get_receipt(db: Session, owner_id: UUID, receipt_id: UUID) -> Receipt | None:
    statement = (
        select(Receipt)
        .join(Receipt.bill_session)
        .where(
            Receipt.id == receipt_id,
            BillSession.owner_id == owner_id,
        )
        .options(selectinload(Receipt.items))
    )
    return db.scalar(statement)


def get_receipt_for_session(
    db: Session, owner_id: UUID, session_id: UUID
) -> Receipt | None:
    statement = (
        select(Receipt)
        .join(Receipt.bill_session)
        .where(
            Receipt.bill_session_id == session_id,
            BillSession.owner_id == owner_id,
        )
        .options(selectinload(Receipt.items))
    )
    return db.scalar(statement)


def get_item(db: Session, owner_id: UUID, item_id: UUID) -> ReceiptItem | None:
    statement = (
        select(ReceiptItem)
        .join(ReceiptItem.receipt)
        .join(Receipt.bill_session)
        .where(
            ReceiptItem.id == item_id,
            BillSession.owner_id == owner_id,
        )
        .options(selectinload(ReceiptItem.receipt))
    )
    return db.scalar(statement)


def list_items(db: Session, owner_id: UUID, receipt_id: UUID) -> list[ReceiptItem]:
    statement = (
        select(ReceiptItem)
        .join(ReceiptItem.receipt)
        .join(Receipt.bill_session)
        .where(
            Receipt.id == receipt_id,
            BillSession.owner_id == owner_id,
        )
        .order_by(ReceiptItem.created_at, ReceiptItem.id)
    )
    return list(db.scalars(statement))


def get_assignment(
    db: Session, owner_id: UUID, assignment_id: UUID
) -> ItemAssignment | None:
    statement = (
        select(ItemAssignment)
        .join(ItemAssignment.receipt_item)
        .join(ReceiptItem.receipt)
        .join(Receipt.bill_session)
        .where(
            ItemAssignment.id == assignment_id,
            BillSession.owner_id == owner_id,
        )
    )
    return db.scalar(statement)


def list_assignments(
    db: Session, owner_id: UUID, item_id: UUID
) -> list[ItemAssignment]:
    statement = (
        select(ItemAssignment)
        .join(ItemAssignment.receipt_item)
        .join(ReceiptItem.receipt)
        .join(Receipt.bill_session)
        .where(
            ReceiptItem.id == item_id,
            BillSession.owner_id == owner_id,
        )
        .order_by(ItemAssignment.created_at, ItemAssignment.id)
    )
    return list(db.scalars(statement))


def list_splits(db: Session, owner_id: UUID, session_id: UUID) -> list[BillSplit]:
    statement = (
        select(BillSplit)
        .join(BillSplit.bill_session)
        .where(
            BillSplit.bill_session_id == session_id,
            BillSession.owner_id == owner_id,
        )
        .order_by(BillSplit.created_at, BillSplit.id)
    )
    return list(db.scalars(statement))


def list_invoices(
    db: Session, owner_id: UUID, session_id: UUID
) -> list[PayPalInvoice]:
    statement = (
        select(PayPalInvoice)
        .join(PayPalInvoice.bill_session)
        .where(
            PayPalInvoice.bill_session_id == session_id,
            BillSession.owner_id == owner_id,
        )
        .order_by(PayPalInvoice.created_at, PayPalInvoice.id)
    )
    return list(db.scalars(statement))


def get_invoice(
    db: Session, owner_id: UUID, invoice_id: UUID
) -> PayPalInvoice | None:
    statement = (
        select(PayPalInvoice)
        .join(PayPalInvoice.bill_session)
        .where(
            PayPalInvoice.id == invoice_id,
            BillSession.owner_id == owner_id,
        )
        .options(selectinload(PayPalInvoice.payments))
    )
    return db.scalar(statement)


def list_invoice_payments(
    db: Session, owner_id: UUID, invoice_id: UUID
) -> list[Payment]:
    statement = (
        select(Payment)
        .join(Payment.paypal_invoice)
        .join(PayPalInvoice.bill_session)
        .where(
            Payment.paypal_invoice_id == invoice_id,
            BillSession.owner_id == owner_id,
        )
        .order_by(Payment.created_at, Payment.id)
    )
    return list(db.scalars(statement))


def list_session_payments(
    db: Session, owner_id: UUID, session_id: UUID
) -> list[Payment]:
    statement = (
        select(Payment)
        .join(Payment.paypal_invoice)
        .join(PayPalInvoice.bill_session)
        .where(
            PayPalInvoice.bill_session_id == session_id,
            BillSession.owner_id == owner_id,
        )
        .order_by(Payment.created_at, Payment.id)
    )
    return list(db.scalars(statement))
