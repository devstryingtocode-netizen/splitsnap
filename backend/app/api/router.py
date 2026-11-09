from fastapi import APIRouter

from app.api.v1.endpoints import (
    assignments,
    chat,
    invoices,
    participants,
    payments,
    receipt_items,
    receipts,
    sessions,
    splits,
)

api_router = APIRouter()
api_router.include_router(sessions.router)
api_router.include_router(participants.router)
api_router.include_router(receipts.router)
api_router.include_router(receipt_items.router)
api_router.include_router(assignments.router)
api_router.include_router(chat.router)
api_router.include_router(splits.router)
api_router.include_router(invoices.router)
api_router.include_router(payments.router)
