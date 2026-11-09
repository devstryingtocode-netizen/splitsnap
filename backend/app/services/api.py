import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.models import (
    BillSession,
    BillSessionStatus,
    BillSplit,
    ItemAssignment,
    Participant,
    Payment,
    PayPalInvoice,
    Receipt,
    ReceiptExtractionStatus,
    ReceiptItem,
    User,
)
from app.repositories import api as repository
from app.schemas.api import (
    AssignmentCreate,
    AssignmentUpdate,
    ParticipantCreate,
    ParticipantUpdate,
    ReceiptCreate,
    ReceiptItemCreate,
    ReceiptItemUpdate,
    ReceiptUpdate,
    SessionCreate,
    SessionUpdate,
)

logger = logging.getLogger(__name__)


def _development_owner_id(db: Session) -> UUID:
    configured_id = get_settings().development_owner_id.strip()
    if not configured_id:
        raise APIError(
            503,
            "development_owner_not_configured",
            "Set DEVELOPMENT_OWNER_ID to an existing user UUID before using the API.",
        )
    try:
        owner_id = UUID(configured_id)
    except ValueError as exc:
        raise APIError(
            503,
            "development_owner_not_configured",
            "DEVELOPMENT_OWNER_ID must be a valid UUID for an existing user.",
        ) from exc

    if db.get(User, owner_id) is None:
        raise APIError(
            503,
            "development_owner_not_found",
            "DEVELOPMENT_OWNER_ID does not match an existing user.",
        )
    return owner_id


def _not_found(resource: str) -> APIError:
    return APIError(404, "not_found", f"{resource} was not found.")


def _conflict(message: str, code: str = "conflict") -> APIError:
    return APIError(409, code, message)


def _reject_null_fields(
    changes: dict[str, object], required_fields: set[str]
) -> None:
    if any(field in changes and changes[field] is None for field in required_fields):
        raise APIError(
            422,
            "invalid_field",
            "A required field cannot be null.",
        )


def _commit(db: Session, conflict_message: str = "The request conflicts with stored data.") -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _conflict(conflict_message) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database operation failed")
        raise APIError(500, "database_error", "A database operation failed.") from exc


def _ensure_no_financial_records(db: Session, session_id: UUID) -> None:
    has_split = db.scalar(
        select(BillSplit.id).where(BillSplit.bill_session_id == session_id).limit(1)
    )
    has_invoice = db.scalar(
        select(PayPalInvoice.id)
        .where(PayPalInvoice.bill_session_id == session_id)
        .limit(1)
    )
    if has_split is not None or has_invoice is not None:
        raise _conflict(
            "This bill session has financial records; source data cannot be changed."
        )


def _require_editable_session(db: Session, owner_id: UUID, session_id: UUID) -> BillSession:
    bill_session = repository.get_session(db, owner_id, session_id)
    if bill_session is None:
        raise _not_found("Bill session")
    if bill_session.status in {
        BillSessionStatus.APPROVED,
        BillSessionStatus.INVOICES_CREATED,
        BillSessionStatus.COMPLETED,
        BillSessionStatus.CANCELLED,
    }:
        raise _conflict("This bill session can no longer be edited.")
    _ensure_no_financial_records(db, session_id)
    return bill_session


def _session_response(bill_session: BillSession) -> dict[str, object]:
    return {
        "id": bill_session.id,
        "owner_id": bill_session.owner_id,
        "title": bill_session.title,
        "currency": bill_session.currency,
        "status": bill_session.status,
        "subtotal": bill_session.subtotal,
        "tax_amount": bill_session.tax_amount,
        "tip_amount": bill_session.tip_amount,
        "service_charge": bill_session.service_charge,
        "total_amount": bill_session.total_amount,
        "participant_count": len(bill_session.participants),
        "receipt_id": bill_session.receipt.id if bill_session.receipt else None,
        "created_at": bill_session.created_at,
        "updated_at": bill_session.updated_at,
    }


def create_session(db: Session, payload: SessionCreate) -> dict[str, object]:
    owner_id = _development_owner_id(db)
    bill_session = BillSession(
        owner_id=owner_id,
        title=payload.title,
        currency=payload.currency,
        status=BillSessionStatus.DRAFT,
    )
    db.add(bill_session)
    _commit(db)
    row = repository.get_session(db, owner_id, bill_session.id)
    if row is None:
        raise APIError(500, "database_error", "The created session could not be loaded.")
    return _session_response(row)


def list_sessions(db: Session, limit: int, offset: int) -> dict[str, object]:
    owner_id = _development_owner_id(db)
    sessions, total = repository.list_sessions(db, owner_id, limit, offset)
    return {
        "items": [_session_response(row) for row in sessions],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_session(db: Session, session_id: UUID) -> dict[str, object]:
    owner_id = _development_owner_id(db)
    bill_session = repository.get_session(db, owner_id, session_id)
    if bill_session is None:
        raise _not_found("Bill session")
    response = _session_response(bill_session)
    response["participants"] = bill_session.participants
    return response


def update_session(
    db: Session, session_id: UUID, payload: SessionUpdate
) -> dict[str, object]:
    owner_id = _development_owner_id(db)
    bill_session = repository.get_session(db, owner_id, session_id)
    if bill_session is None:
        raise _not_found("Bill session")
    if bill_session.status in {
        BillSessionStatus.COMPLETED,
        BillSessionStatus.CANCELLED,
        BillSessionStatus.INVOICES_CREATED,
        BillSessionStatus.APPROVED,
    }:
        raise _conflict("This bill session can no longer be edited.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise APIError(400, "empty_update", "Provide at least one field to update.")
    _reject_null_fields(changes, {"title", "currency"})
    if "currency" in changes and changes["currency"] != bill_session.currency:
        _ensure_no_financial_records(db, session_id)
        if bill_session.receipt is not None:
            raise _conflict("Currency cannot be changed after receipt metadata is added.")
    for field, value in changes.items():
        setattr(bill_session, field, value)
    _commit(db)
    updated = repository.get_session(db, owner_id, session_id)
    if updated is None:
        raise APIError(500, "database_error", "The updated session could not be loaded.")
    return _session_response(updated)


def cancel_session(db: Session, session_id: UUID) -> dict[str, object]:
    owner_id = _development_owner_id(db)
    bill_session = repository.get_session(db, owner_id, session_id)
    if bill_session is None:
        raise _not_found("Bill session")
    allowed = {
        BillSessionStatus.DRAFT,
        BillSessionStatus.RECEIPT_UPLOADED,
        BillSessionStatus.PROCESSING,
        BillSessionStatus.REVIEW_REQUIRED,
        BillSessionStatus.READY_FOR_APPROVAL,
    }
    if bill_session.status not in allowed:
        raise _conflict("This bill session cannot be cancelled in its current state.")
    _ensure_no_financial_records(db, session_id)
    bill_session.status = BillSessionStatus.CANCELLED
    _commit(db)
    return _session_response(bill_session)


def _check_duplicate_participant(
    db: Session,
    session_id: UUID,
    name: str,
    email: str | None,
    exclude_id: UUID | None = None,
) -> None:
    statement = select(Participant.id).where(Participant.bill_session_id == session_id)
    if exclude_id is not None:
        statement = statement.where(Participant.id != exclude_id)
    if email is not None:
        statement = statement.where(func.lower(Participant.email) == email.lower())
        if db.scalar(statement.limit(1)) is not None:
            raise _conflict(
                "A participant with this contact email already exists in the session.",
                "duplicate_participant",
            )
        return
    statement = statement.where(func.lower(Participant.name) == name.lower())
    if db.scalar(statement.limit(1)) is not None:
        raise _conflict(
            "A participant with this name and no contact email already exists.",
            "duplicate_participant",
        )


def add_participant(
    db: Session, session_id: UUID, payload: ParticipantCreate
) -> Participant:
    owner_id = _development_owner_id(db)
    _require_editable_session(db, owner_id, session_id)
    _check_duplicate_participant(db, session_id, payload.name, payload.email)
    participant = Participant(
        bill_session_id=session_id,
        name=payload.name,
        email=payload.email,
        paypal_email=payload.paypal_email,
    )
    db.add(participant)
    _commit(db, "A participant with this contact email already exists.")
    db.refresh(participant)
    return participant


def list_participants(db: Session, session_id: UUID) -> list[Participant]:
    owner_id = _development_owner_id(db)
    bill_session = repository.get_session(db, owner_id, session_id)
    if bill_session is None:
        raise _not_found("Bill session")
    return bill_session.participants


def get_participant(db: Session, participant_id: UUID) -> Participant:
    owner_id = _development_owner_id(db)
    participant = repository.get_participant(db, owner_id, participant_id)
    if participant is None:
        raise _not_found("Participant")
    return participant


def update_participant(
    db: Session, participant_id: UUID, payload: ParticipantUpdate
) -> Participant:
    owner_id = _development_owner_id(db)
    participant = repository.get_participant(db, owner_id, participant_id)
    if participant is None:
        raise _not_found("Participant")
    _require_editable_session(db, owner_id, participant.bill_session_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise APIError(400, "empty_update", "Provide at least one field to update.")
    _reject_null_fields(changes, {"name"})
    name = payload.name if payload.name is not None else participant.name
    email_value = (
        payload.email
        if "email" in payload.model_fields_set
        else participant.email
    )
    _check_duplicate_participant(
        db,
        participant.bill_session_id,
        name,
        email_value,
        exclude_id=participant.id,
    )
    for field, value in changes.items():
        setattr(participant, field, value)
    _commit(db, "A participant with this contact email already exists.")
    db.refresh(participant)
    return participant


def delete_participant(db: Session, participant_id: UUID) -> None:
    owner_id = _development_owner_id(db)
    participant = repository.get_participant(db, owner_id, participant_id)
    if participant is None:
        raise _not_found("Participant")
    _require_editable_session(db, owner_id, participant.bill_session_id)
    has_split = db.scalar(
        select(BillSplit.id).where(BillSplit.participant_id == participant_id).limit(1)
    )
    has_invoice = db.scalar(
        select(PayPalInvoice.id)
        .where(PayPalInvoice.participant_id == participant_id)
        .limit(1)
    )
    if has_split is not None or has_invoice is not None:
        raise _conflict(
            "This participant has financial records and cannot be removed."
        )
    db.delete(participant)
    _commit(db)


def create_receipt(
    db: Session, session_id: UUID, payload: ReceiptCreate
) -> Receipt:
    owner_id = _development_owner_id(db)
    bill_session = _require_editable_session(db, owner_id, session_id)
    if payload.currency is not None and payload.currency != bill_session.currency:
        raise APIError(
            400,
            "currency_mismatch",
            "Receipt currency must match the bill session currency.",
        )
    if repository.get_receipt_for_session(db, owner_id, session_id) is not None:
        raise _conflict("This bill session already has a receipt.", "duplicate_receipt")
    receipt = Receipt(
        bill_session_id=session_id,
        original_filename=payload.original_filename,
        mime_type=payload.mime_type,
        storage_key=payload.storage_key,
        currency=payload.currency,
        extraction_status=ReceiptExtractionStatus.PENDING,
    )
    db.add(receipt)
    _commit(db, "This bill session already has a receipt.")
    db.refresh(receipt)
    receipt.items = []
    return receipt


def get_receipt_for_session(db: Session, session_id: UUID) -> Receipt:
    owner_id = _development_owner_id(db)
    if repository.get_session(db, owner_id, session_id) is None:
        raise _not_found("Bill session")
    receipt = repository.get_receipt_for_session(db, owner_id, session_id)
    if receipt is None:
        raise _not_found("Receipt")
    return receipt


def get_receipt(db: Session, receipt_id: UUID) -> Receipt:
    owner_id = _development_owner_id(db)
    receipt = repository.get_receipt(db, owner_id, receipt_id)
    if receipt is None:
        raise _not_found("Receipt")
    return receipt


def update_receipt(
    db: Session, receipt_id: UUID, payload: ReceiptUpdate
) -> Receipt:
    owner_id = _development_owner_id(db)
    receipt = repository.get_receipt(db, owner_id, receipt_id)
    if receipt is None:
        raise _not_found("Receipt")
    bill_session = _require_editable_session(
        db, owner_id, receipt.bill_session_id
    )
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise APIError(400, "empty_update", "Provide at least one field to update.")
    required_fields = {"original_filename", "mime_type", "storage_key"}
    _reject_null_fields(changes, required_fields)
    requested_currency = changes.get("currency", receipt.currency)
    if requested_currency is not None and requested_currency != bill_session.currency:
        raise APIError(
            400,
            "currency_mismatch",
            "Receipt currency must match the bill session currency.",
        )
    for field, value in changes.items():
        setattr(receipt, field, value)
    _commit(db)
    db.refresh(receipt)
    return receipt


def create_receipt_item(
    db: Session, receipt_id: UUID, payload: ReceiptItemCreate
) -> ReceiptItem:
    owner_id = _development_owner_id(db)
    receipt = repository.get_receipt(db, owner_id, receipt_id)
    if receipt is None:
        raise _not_found("Receipt")
    _require_editable_session(db, owner_id, receipt.bill_session_id)
    item = ReceiptItem(
        receipt_id=receipt_id,
        name=payload.name,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        total_price=payload.total_price,
        category=payload.category,
    )
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


def list_receipt_items(db: Session, receipt_id: UUID) -> list[ReceiptItem]:
    owner_id = _development_owner_id(db)
    if repository.get_receipt(db, owner_id, receipt_id) is None:
        raise _not_found("Receipt")
    return repository.list_items(db, owner_id, receipt_id)


def update_receipt_item(
    db: Session, item_id: UUID, payload: ReceiptItemUpdate
) -> ReceiptItem:
    owner_id = _development_owner_id(db)
    item = repository.get_item(db, owner_id, item_id)
    if item is None:
        raise _not_found("Receipt item")
    _require_editable_session(db, owner_id, item.receipt.bill_session_id)
    if db.scalar(
        select(ItemAssignment.id)
        .where(ItemAssignment.receipt_item_id == item_id)
        .limit(1)
    ) is not None:
        raise _conflict("An assigned item cannot be edited; remove its assignments first.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise APIError(400, "empty_update", "Provide at least one field to update.")
    _reject_null_fields(changes, {"name", "quantity", "unit_price", "total_price"})
    for field, value in changes.items():
        setattr(item, field, value)
    _commit(db)
    db.refresh(item)
    return item


def delete_receipt_item(db: Session, item_id: UUID) -> None:
    owner_id = _development_owner_id(db)
    item = repository.get_item(db, owner_id, item_id)
    if item is None:
        raise _not_found("Receipt item")
    _require_editable_session(db, owner_id, item.receipt.bill_session_id)
    if db.scalar(
        select(ItemAssignment.id)
        .where(ItemAssignment.receipt_item_id == item_id)
        .limit(1)
    ) is not None:
        raise _conflict("An assigned item cannot be deleted; remove its assignments first.")
    db.delete(item)
    _commit(db)


def create_assignment(
    db: Session, item_id: UUID, payload: AssignmentCreate
) -> ItemAssignment:
    owner_id = _development_owner_id(db)
    item = repository.get_item(db, owner_id, item_id)
    if item is None:
        raise _not_found("Receipt item")
    _require_editable_session(db, owner_id, item.receipt.bill_session_id)
    participant = repository.get_participant(
        db, owner_id, payload.participant_id
    )
    if participant is None:
        raise _not_found("Participant")
    if participant.bill_session_id != item.receipt.bill_session_id:
        raise APIError(
            400,
            "cross_session_assignment",
            "The participant and item must belong to the same bill session.",
        )
    assignment = ItemAssignment(
        receipt_item_id=item_id,
        participant_id=participant.id,
        quantity=payload.quantity,
        share_type=payload.share_type,
    )
    db.add(assignment)
    _commit(db, "This participant is already assigned to this item.")
    db.refresh(assignment)
    return assignment


def list_assignments(db: Session, item_id: UUID) -> list[ItemAssignment]:
    owner_id = _development_owner_id(db)
    if repository.get_item(db, owner_id, item_id) is None:
        raise _not_found("Receipt item")
    return repository.list_assignments(db, owner_id, item_id)


def update_assignment(
    db: Session, assignment_id: UUID, payload: AssignmentUpdate
) -> ItemAssignment:
    owner_id = _development_owner_id(db)
    assignment = repository.get_assignment(db, owner_id, assignment_id)
    if assignment is None:
        raise _not_found("Assignment")
    item = repository.get_item(db, owner_id, assignment.receipt_item_id)
    if item is None:
        raise _not_found("Receipt item")
    _require_editable_session(db, owner_id, item.receipt.bill_session_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise APIError(400, "empty_update", "Provide at least one field to update.")
    _reject_null_fields(changes, {"participant_id", "quantity", "share_type"})
    new_participant_id = (
        payload.participant_id
        if "participant_id" in payload.model_fields_set
        else assignment.participant_id
    )
    if "participant_id" in changes:
        if new_participant_id is None:
            raise APIError(422, "invalid_field", "A participant ID cannot be null.")
        participant = repository.get_participant(db, owner_id, new_participant_id)
        if participant is None:
            raise _not_found("Participant")
        if participant.bill_session_id != item.receipt.bill_session_id:
            raise APIError(
                400,
                "cross_session_assignment",
                "The participant and item must belong to the same bill session.",
            )
    for field, value in changes.items():
        setattr(assignment, field, value)
    _commit(db, "This participant is already assigned to this item.")
    db.refresh(assignment)
    return assignment


def delete_assignment(db: Session, assignment_id: UUID) -> None:
    owner_id = _development_owner_id(db)
    assignment = repository.get_assignment(db, owner_id, assignment_id)
    if assignment is None:
        raise _not_found("Assignment")
    item = repository.get_item(db, owner_id, assignment.receipt_item_id)
    if item is None:
        raise _not_found("Receipt item")
    _require_editable_session(db, owner_id, item.receipt.bill_session_id)
    db.delete(assignment)
    _commit(db)


def list_session_splits(db: Session, session_id: UUID) -> list[BillSplit]:
    owner_id = _development_owner_id(db)
    if repository.get_session(db, owner_id, session_id) is None:
        raise _not_found("Bill session")
    return repository.list_splits(db, owner_id, session_id)


def list_session_invoices(db: Session, session_id: UUID) -> list[PayPalInvoice]:
    owner_id = _development_owner_id(db)
    if repository.get_session(db, owner_id, session_id) is None:
        raise _not_found("Bill session")
    return repository.list_invoices(db, owner_id, session_id)


def get_invoice(db: Session, invoice_id: UUID) -> PayPalInvoice:
    owner_id = _development_owner_id(db)
    invoice = repository.get_invoice(db, owner_id, invoice_id)
    if invoice is None:
        raise _not_found("Invoice")
    return invoice


def list_invoice_payments(db: Session, invoice_id: UUID) -> list[Payment]:
    owner_id = _development_owner_id(db)
    if repository.get_invoice(db, owner_id, invoice_id) is None:
        raise _not_found("Invoice")
    return repository.list_invoice_payments(db, owner_id, invoice_id)


def list_session_payments(db: Session, session_id: UUID) -> list[Payment]:
    owner_id = _development_owner_id(db)
    if repository.get_session(db, owner_id, session_id) is None:
        raise _not_found("Bill session")
    return repository.list_session_payments(db, owner_id, session_id)
