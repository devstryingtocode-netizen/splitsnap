from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import (
    BillSessionStatus,
    ItemShareType,
    PaymentStatus,
    PayPalInvoiceStatus,
    ReceiptExtractionStatus,
)

CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$", strip_whitespace=True)]
EmailAddress = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=320,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        strip_whitespace=True,
    ),
]
MoneyAmount = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
PositiveQuantity = Annotated[
    Decimal, Field(gt=0, max_digits=12, decimal_places=3)
]


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ORMResponse(APIModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class SessionCreate(APIModel):
    title: Annotated[str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)]
    currency: CurrencyCode


class SessionUpdate(APIModel):
    title: Annotated[
        str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)
    ] | None = None
    currency: CurrencyCode | None = None


class ParticipantResponse(ORMResponse):
    id: UUID
    bill_session_id: UUID
    name: str
    email: EmailAddress | None
    paypal_email: EmailAddress | None
    user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class SessionResponse(ORMResponse):
    id: UUID
    owner_id: UUID
    title: str
    currency: CurrencyCode
    status: BillSessionStatus
    subtotal: MoneyAmount | None
    tax_amount: MoneyAmount | None
    tip_amount: MoneyAmount | None
    service_charge: MoneyAmount | None
    total_amount: MoneyAmount | None
    participant_count: int
    receipt_id: UUID | None
    created_at: datetime
    updated_at: datetime


class SessionListResponse(APIModel):
    items: list[SessionResponse]
    total: int
    limit: int
    offset: int


class SessionDetailResponse(SessionResponse):
    participants: list[ParticipantResponse]


class ParticipantCreate(APIModel):
    name: Annotated[str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)]
    email: EmailAddress | None = None
    paypal_email: EmailAddress | None = None


class ParticipantUpdate(APIModel):
    name: Annotated[
        str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)
    ] | None = None
    email: EmailAddress | None = None
    paypal_email: EmailAddress | None = None


class ReceiptCreate(APIModel):
    original_filename: Annotated[
        str, StringConstraints(min_length=1, max_length=255, strip_whitespace=True)
    ]
    mime_type: Annotated[
        str, StringConstraints(min_length=1, max_length=127, strip_whitespace=True)
    ]
    storage_key: Annotated[
        str, StringConstraints(min_length=1, max_length=1024, strip_whitespace=True)
    ]
    currency: CurrencyCode | None = None


class ReceiptUpdate(APIModel):
    original_filename: Annotated[
        str, StringConstraints(min_length=1, max_length=255, strip_whitespace=True)
    ] | None = None
    mime_type: Annotated[
        str, StringConstraints(min_length=1, max_length=127, strip_whitespace=True)
    ] | None = None
    storage_key: Annotated[
        str, StringConstraints(min_length=1, max_length=1024, strip_whitespace=True)
    ] | None = None
    extracted_merchant_name: Annotated[
        str, StringConstraints(min_length=1, max_length=255, strip_whitespace=True)
    ] | None = None
    extracted_receipt_date: date | None = None
    currency: CurrencyCode | None = None
    subtotal: MoneyAmount | None = None
    tax_amount: MoneyAmount | None = None
    tip_amount: MoneyAmount | None = None
    service_charge: MoneyAmount | None = None
    total_amount: MoneyAmount | None = None


class ReceiptItemCreate(APIModel):
    name: Annotated[str, StringConstraints(min_length=1, max_length=255, strip_whitespace=True)]
    quantity: PositiveQuantity = Decimal("1.000")
    unit_price: MoneyAmount
    total_price: MoneyAmount
    category: Annotated[
        str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)
    ] | None = None


class ReceiptItemUpdate(APIModel):
    name: Annotated[
        str, StringConstraints(min_length=1, max_length=255, strip_whitespace=True)
    ] | None = None
    quantity: PositiveQuantity | None = None
    unit_price: MoneyAmount | None = None
    total_price: MoneyAmount | None = None
    category: Annotated[
        str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)
    ] | None = None


class ReceiptItemResponse(ORMResponse):
    id: UUID
    receipt_id: UUID
    name: str
    quantity: PositiveQuantity
    unit_price: MoneyAmount
    total_price: MoneyAmount
    category: str | None
    created_at: datetime
    updated_at: datetime


class ReceiptResponse(ORMResponse):
    id: UUID
    bill_session_id: UUID
    original_filename: str
    mime_type: str
    storage_key: str
    extraction_status: ReceiptExtractionStatus
    extracted_merchant_name: str | None
    extracted_receipt_date: date | None
    currency: CurrencyCode | None
    subtotal: MoneyAmount | None
    tax_amount: MoneyAmount | None
    tip_amount: MoneyAmount | None
    service_charge: MoneyAmount | None
    total_amount: MoneyAmount | None
    items: list[ReceiptItemResponse]
    created_at: datetime
    updated_at: datetime


class AssignmentCreate(APIModel):
    participant_id: UUID
    quantity: PositiveQuantity = Decimal("1.000")
    share_type: ItemShareType = ItemShareType.INDIVIDUAL


class AssignmentUpdate(APIModel):
    participant_id: UUID | None = None
    quantity: PositiveQuantity | None = None
    share_type: ItemShareType | None = None


class AssignmentResponse(ORMResponse):
    id: UUID
    receipt_item_id: UUID
    participant_id: UUID
    quantity: PositiveQuantity
    share_type: ItemShareType
    created_at: datetime
    updated_at: datetime


class BillSplitResponse(ORMResponse):
    id: UUID
    bill_session_id: UUID
    participant_id: UUID
    subtotal: MoneyAmount
    tax_share: MoneyAmount
    tip_share: MoneyAmount
    service_charge_share: MoneyAmount
    total_owed: MoneyAmount
    currency: CurrencyCode
    calculation_version: str
    created_at: datetime
    updated_at: datetime


class PayPalInvoiceResponse(ORMResponse):
    id: UUID
    bill_session_id: UUID
    participant_id: UUID
    bill_split_id: UUID
    paypal_invoice_id: str | None
    invoice_number: str | None
    invoice_status: PayPalInvoiceStatus
    amount: MoneyAmount
    currency: CurrencyCode
    invoice_url: str | None
    sent_at: datetime | None
    due_date: date | None
    created_at: datetime
    updated_at: datetime


class PaymentResponse(ORMResponse):
    id: UUID
    paypal_invoice_id: UUID
    external_payment_id: str | None
    amount: MoneyAmount
    currency: CurrencyCode
    status: PaymentStatus
    payment_method: str | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime
