from decimal import Decimal
from typing import Protocol

from app.schemas.payments import PayPalInvoiceReference


class PayPalInvoicingProvider(Protocol):
    async def create_draft(
        self,
        *,
        recipient_email: str,
        amount: Decimal,
        currency_code: str,
        description: str,
    ) -> PayPalInvoiceReference: ...
