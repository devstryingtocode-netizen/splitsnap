from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TypeVar
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UTCDateTime

MONEY_PRECISION = 14
MONEY_SCALE = 2
QUANTITY_PRECISION = 12
QUANTITY_SCALE = 3

MONEY = Numeric(MONEY_PRECISION, MONEY_SCALE, asdecimal=True)
QUANTITY = Numeric(QUANTITY_PRECISION, QUANTITY_SCALE, asdecimal=True)

EnumType = TypeVar("EnumType", bound=Enum)


def enum_column(enum_class: type[EnumType], name: str) -> SAEnum:
    return SAEnum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda values: [member.value for member in values],
    )


class BillSessionStatus(str, Enum):
    DRAFT = "draft"
    RECEIPT_UPLOADED = "receipt_uploaded"
    PROCESSING = "processing"
    REVIEW_REQUIRED = "review_required"
    READY_FOR_APPROVAL = "ready_for_approval"
    APPROVED = "approved"
    INVOICES_CREATED = "invoices_created"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReceiptExtractionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"


class ItemShareType(str, Enum):
    INDIVIDUAL = "individual"
    EQUAL = "equal"
    QUANTITY_BASED = "quantity_based"


class PayPalInvoiceStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    CREATING = "creating"
    SENT = "sent"
    PAID = "paid"
    CANCELLED = "cancelled"
    FAILED = "failed"
    OVERDUE = "overdue"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)

    bill_sessions: Mapped[list["BillSession"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    participants: Mapped[list["Participant"]] = relationship(back_populates="user")


class BillSession(TimestampMixin, Base):
    __tablename__ = "bill_sessions"
    __table_args__ = (
        CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_bill_sessions_currency_code",
        ),
        CheckConstraint("subtotal IS NULL OR subtotal >= 0", name="ck_bill_sessions_subtotal_nonnegative"),
        CheckConstraint("tax_amount IS NULL OR tax_amount >= 0", name="ck_bill_sessions_tax_nonnegative"),
        CheckConstraint("tip_amount IS NULL OR tip_amount >= 0", name="ck_bill_sessions_tip_nonnegative"),
        CheckConstraint(
            "service_charge IS NULL OR service_charge >= 0",
            name="ck_bill_sessions_service_charge_nonnegative",
        ),
        CheckConstraint(
            "total_amount IS NULL OR total_amount >= 0",
            name="ck_bill_sessions_total_nonnegative",
        ),
        Index("ix_bill_sessions_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[BillSessionStatus] = mapped_column(
        enum_column(BillSessionStatus, "bill_session_status"),
        default=BillSessionStatus.DRAFT,
        server_default=BillSessionStatus.DRAFT.value,
        nullable=False,
    )
    subtotal: Mapped[Decimal | None] = mapped_column(MONEY)
    tax_amount: Mapped[Decimal | None] = mapped_column(MONEY)
    tip_amount: Mapped[Decimal | None] = mapped_column(MONEY)
    service_charge: Mapped[Decimal | None] = mapped_column(MONEY)
    total_amount: Mapped[Decimal | None] = mapped_column(MONEY)

    owner: Mapped[User] = relationship(back_populates="bill_sessions")
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="bill_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    receipt: Mapped["Receipt | None"] = relationship(
        back_populates="bill_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    bill_splits: Mapped[list["BillSplit"]] = relationship(
        back_populates="bill_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    paypal_invoices: Mapped[list["PayPalInvoice"]] = relationship(
        back_populates="bill_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Participant(TimestampMixin, Base):
    __tablename__ = "participants"
    __table_args__ = (
        Index(
            "uq_participants_session_email",
            "bill_session_id",
            text("lower(email)"),
            unique=True,
            sqlite_where=text("email IS NOT NULL"),
            postgresql_where=text("email IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    bill_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bill_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    paypal_email: Mapped[str | None] = mapped_column(String(320))
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )

    bill_session: Mapped[BillSession] = relationship(back_populates="participants")
    user: Mapped[User | None] = relationship(back_populates="participants")
    item_assignments: Mapped[list["ItemAssignment"]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    bill_splits: Mapped[list["BillSplit"]] = relationship(
        back_populates="participant",
        passive_deletes=True,
    )
    paypal_invoices: Mapped[list["PayPalInvoice"]] = relationship(
        back_populates="participant",
        passive_deletes=True,
    )


class Receipt(TimestampMixin, Base):
    __tablename__ = "receipts"
    __table_args__ = (
        CheckConstraint(
            "currency IS NULL OR (currency = upper(currency) AND length(currency) = 3)",
            name="ck_receipts_currency_code",
        ),
        CheckConstraint("subtotal IS NULL OR subtotal >= 0", name="ck_receipts_subtotal_nonnegative"),
        CheckConstraint("tax_amount IS NULL OR tax_amount >= 0", name="ck_receipts_tax_nonnegative"),
        CheckConstraint("tip_amount IS NULL OR tip_amount >= 0", name="ck_receipts_tip_nonnegative"),
        CheckConstraint(
            "service_charge IS NULL OR service_charge >= 0",
            name="ck_receipts_service_charge_nonnegative",
        ),
        CheckConstraint(
            "total_amount IS NULL OR total_amount >= 0",
            name="ck_receipts_total_nonnegative",
        ),
        Index("ix_receipts_extraction_status", "extraction_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    bill_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bill_sessions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    extraction_status: Mapped[ReceiptExtractionStatus] = mapped_column(
        enum_column(ReceiptExtractionStatus, "receipt_extraction_status"),
        default=ReceiptExtractionStatus.PENDING,
        server_default=ReceiptExtractionStatus.PENDING.value,
        nullable=False,
    )
    extracted_merchant_name: Mapped[str | None] = mapped_column(String(255))
    extracted_receipt_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str | None] = mapped_column(String(3))
    subtotal: Mapped[Decimal | None] = mapped_column(MONEY)
    tax_amount: Mapped[Decimal | None] = mapped_column(MONEY)
    tip_amount: Mapped[Decimal | None] = mapped_column(MONEY)
    service_charge: Mapped[Decimal | None] = mapped_column(MONEY)
    total_amount: Mapped[Decimal | None] = mapped_column(MONEY)

    bill_session: Mapped[BillSession] = relationship(back_populates="receipt")
    items: Mapped[list["ReceiptItem"]] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ReceiptItem(TimestampMixin, Base):
    __tablename__ = "receipt_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_receipt_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_receipt_items_unit_price_nonnegative"),
        CheckConstraint("total_price >= 0", name="ck_receipt_items_total_price_nonnegative"),
        Index("ix_receipt_items_receipt_id", "receipt_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    receipt_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(
        QUANTITY,
        default=Decimal("1"),
        server_default=text("1"),
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    total_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))

    receipt: Mapped[Receipt] = relationship(back_populates="items")
    assignments: Mapped[list["ItemAssignment"]] = relationship(
        back_populates="receipt_item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ItemAssignment(TimestampMixin, Base):
    __tablename__ = "item_assignments"
    __table_args__ = (
        UniqueConstraint(
            "receipt_item_id",
            "participant_id",
            name="uq_item_assignments_item_participant",
        ),
        CheckConstraint("quantity > 0", name="ck_item_assignments_quantity_positive"),
        Index("ix_item_assignments_participant_id", "participant_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    receipt_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("receipt_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(
        QUANTITY,
        default=Decimal("1"),
        server_default=text("1"),
        nullable=False,
    )
    share_type: Mapped[ItemShareType] = mapped_column(
        enum_column(ItemShareType, "item_share_type"),
        default=ItemShareType.INDIVIDUAL,
        server_default=ItemShareType.INDIVIDUAL.value,
        nullable=False,
    )

    receipt_item: Mapped[ReceiptItem] = relationship(back_populates="assignments")
    participant: Mapped[Participant] = relationship(back_populates="item_assignments")


class BillSplit(TimestampMixin, Base):
    __tablename__ = "bill_splits"
    __table_args__ = (
        UniqueConstraint(
            "bill_session_id",
            "participant_id",
            name="uq_bill_splits_session_participant",
        ),
        CheckConstraint("subtotal >= 0", name="ck_bill_splits_subtotal_nonnegative"),
        CheckConstraint("tax_share >= 0", name="ck_bill_splits_tax_share_nonnegative"),
        CheckConstraint("tip_share >= 0", name="ck_bill_splits_tip_share_nonnegative"),
        CheckConstraint(
            "service_charge_share >= 0",
            name="ck_bill_splits_service_charge_nonnegative",
        ),
        CheckConstraint("total_owed >= 0", name="ck_bill_splits_total_owed_nonnegative"),
        CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_bill_splits_currency_code",
        ),
        Index("ix_bill_splits_participant_id", "participant_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    bill_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bill_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    participant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    subtotal: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    tax_share: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    tip_share: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    service_charge_share: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    total_owed: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(64), nullable=False)

    bill_session: Mapped[BillSession] = relationship(back_populates="bill_splits")
    participant: Mapped[Participant] = relationship(back_populates="bill_splits")
    paypal_invoice: Mapped["PayPalInvoice | None"] = relationship(
        back_populates="bill_split",
        uselist=False,
    )


class PayPalInvoice(TimestampMixin, Base):
    __tablename__ = "paypal_invoices"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_paypal_invoices_amount_nonnegative"),
        CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_paypal_invoices_currency_code",
        ),
        Index("ix_paypal_invoices_bill_session_id", "bill_session_id"),
        Index("ix_paypal_invoices_participant_id", "participant_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    bill_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bill_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    bill_split_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bill_splits.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    paypal_invoice_id: Mapped[str | None] = mapped_column(
        String(127),
        unique=True,
        index=True,
    )
    invoice_number: Mapped[str | None] = mapped_column(String(127), index=True)
    invoice_status: Mapped[PayPalInvoiceStatus] = mapped_column(
        enum_column(PayPalInvoiceStatus, "paypal_invoice_status"),
        default=PayPalInvoiceStatus.DRAFT,
        server_default=PayPalInvoiceStatus.DRAFT.value,
        index=True,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    invoice_url: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    due_date: Mapped[date | None] = mapped_column(Date)

    bill_session: Mapped[BillSession] = relationship(back_populates="paypal_invoices")
    participant: Mapped[Participant] = relationship(back_populates="paypal_invoices")
    bill_split: Mapped[BillSplit] = relationship(back_populates="paypal_invoice")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="paypal_invoice",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payments_amount_nonnegative"),
        CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_payments_currency_code",
        ),
        Index("ix_payments_paypal_invoice_id", "paypal_invoice_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    paypal_invoice_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paypal_invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_payment_id: Mapped[str | None] = mapped_column(
        String(127),
        unique=True,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        enum_column(PaymentStatus, "payment_status"),
        default=PaymentStatus.PENDING,
        server_default=PaymentStatus.PENDING.value,
        index=True,
        nullable=False,
    )
    payment_method: Mapped[str | None] = mapped_column(String(100))
    paid_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    paypal_invoice: Mapped[PayPalInvoice] = relationship(back_populates="payments")
