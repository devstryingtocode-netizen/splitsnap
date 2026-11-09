from decimal import Decimal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class PayPalInvoiceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: str = Field(min_length=1)
    href: AnyHttpUrl | None = None
