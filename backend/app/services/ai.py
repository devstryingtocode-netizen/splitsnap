from typing import Protocol, Sequence

from app.schemas.ai import (
    AssignmentSuggestion,
    ExtractedReceipt,
    ReceiptItem,
)


class ReceiptExtractionProvider(Protocol):
    async def extract_receipt(
        self,
        *,
        image: bytes,
        media_type: str,
    ) -> ExtractedReceipt: ...


class ItemAssignmentProvider(Protocol):
    async def suggest_assignments(
        self,
        *,
        instruction: str,
        items: Sequence[ReceiptItem],
        participants: Sequence[str],
    ) -> AssignmentSuggestion: ...
