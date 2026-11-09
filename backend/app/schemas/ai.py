from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ReceiptItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal = Field(ge=0)
    line_total: Decimal = Field(ge=0)


class ExtractedReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ReceiptItem]
    subtotal: Decimal | None = Field(default=None, ge=0)
    tax: Decimal | None = Field(default=None, ge=0)
    tip: Decimal | None = Field(default=None, ge=0)
    total: Decimal = Field(ge=0)


class SuggestedItemAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_name: str = Field(min_length=1)
    participant_names: list[str]


class AssignmentSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignments: list[SuggestedItemAssignment]
    clarification_question: str | None = None
