from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import create_database_engine
from app.models import (
    BillSession,
    BillSessionStatus,
    ItemAssignment,
    ItemShareType,
    Participant,
    Receipt,
    ReceiptExtractionStatus,
    ReceiptItem,
    User,
)

DEMO_EMAIL = "dev@splitsnap.example"
DEMO_SESSION_TITLE = "Development Dinner"


def seed_development_data(session: Session) -> User:
    user = session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(name="Splitsnap Developer", email=DEMO_EMAIL)
        session.add(user)
        session.flush()

    bill_session = session.scalar(
        select(BillSession).where(
            BillSession.owner_id == user.id,
            BillSession.title == DEMO_SESSION_TITLE,
        )
    )
    if bill_session is None:
        bill_session = BillSession(
            owner=user,
            title=DEMO_SESSION_TITLE,
            currency="USD",
            status=BillSessionStatus.REVIEW_REQUIRED,
            subtotal=Decimal("68.00"),
            tax_amount=Decimal("5.44"),
            tip_amount=Decimal("12.00"),
            service_charge=Decimal("0.00"),
            total_amount=Decimal("85.44"),
        )
        session.add(bill_session)
        session.flush()

    participants_by_name: dict[str, Participant] = {}
    for name, email, paypal_email in [
        ("Alex", "alex@example.com", "alex.paypal@example.com"),
        ("Jordan", "jordan@example.com", None),
        ("Sam", None, "sam.paypal@example.com"),
    ]:
        participant = session.scalar(
            select(Participant).where(
                Participant.bill_session_id == bill_session.id,
                Participant.name == name,
            )
        )
        if participant is None:
            participant = Participant(
                bill_session=bill_session,
                name=name,
                email=email,
                paypal_email=paypal_email,
            )
            session.add(participant)
        participants_by_name[name] = participant
    session.flush()

    receipt = session.scalar(
        select(Receipt).where(Receipt.bill_session_id == bill_session.id)
    )
    if receipt is None:
        receipt = Receipt(
            bill_session=bill_session,
            original_filename="development-dinner.jpg",
            mime_type="image/jpeg",
            storage_key="development/receipts/development-dinner.jpg",
            extraction_status=ReceiptExtractionStatus.COMPLETED,
            extracted_merchant_name="The Garden Room",
            currency="USD",
            subtotal=Decimal("68.00"),
            tax_amount=Decimal("5.44"),
            tip_amount=Decimal("12.00"),
            service_charge=Decimal("0.00"),
            total_amount=Decimal("85.44"),
        )
        session.add(receipt)
        session.flush()

    item_specs = [
        ("Whipped ricotta", Decimal("1"), Decimal("14.00"), "starter"),
        ("Wild mushroom pasta", Decimal("1"), Decimal("24.00"), "main"),
        ("Wood-fired pizza", Decimal("1"), Decimal("22.00"), "main"),
        ("Sparkling water", Decimal("2"), Decimal("4.00"), "drink"),
    ]
    items_by_name: dict[str, ReceiptItem] = {}
    for name, quantity, unit_price, category in item_specs:
        item = session.scalar(
            select(ReceiptItem).where(
                ReceiptItem.receipt_id == receipt.id,
                ReceiptItem.name == name,
            )
        )
        if item is None:
            item = ReceiptItem(
                receipt=receipt,
                name=name,
                quantity=quantity,
                unit_price=unit_price,
                total_price=quantity * unit_price,
                category=category,
            )
            session.add(item)
            session.flush()
        items_by_name[name] = item

    assignment_specs = [
        ("Whipped ricotta", "Alex", Decimal("1"), ItemShareType.INDIVIDUAL),
        ("Wild mushroom pasta", "Jordan", Decimal("1"), ItemShareType.INDIVIDUAL),
        ("Wood-fired pizza", "Alex", Decimal("1"), ItemShareType.EQUAL),
        ("Wood-fired pizza", "Jordan", Decimal("1"), ItemShareType.EQUAL),
        ("Wood-fired pizza", "Sam", Decimal("1"), ItemShareType.EQUAL),
        ("Sparkling water", "Sam", Decimal("2"), ItemShareType.QUANTITY_BASED),
    ]
    for item_name, participant_name, quantity, share_type in assignment_specs:
        receipt_item = items_by_name[item_name]
        participant = participants_by_name[participant_name]
        assignment = session.scalar(
            select(ItemAssignment).where(
                ItemAssignment.receipt_item_id == receipt_item.id,
                ItemAssignment.participant_id == participant.id,
            )
        )
        if assignment is None:
            session.add(
                ItemAssignment(
                    receipt_item=receipt_item,
                    participant=participant,
                    quantity=quantity,
                    share_type=share_type,
                )
            )
    return user


def main() -> None:
    settings = get_settings()
    if settings.app_env.lower() not in {"development", "dev", "test"}:
        raise SystemExit(
            "Refusing to seed a non-development environment. "
            "Set APP_ENV=development to run this script."
        )

    seed_engine = create_database_engine(settings.database_url)
    try:
        with Session(seed_engine) as session, session.begin():
            user = seed_development_data(session)
            owner_id = user.id
    finally:
        seed_engine.dispose()
    print(
        f"Development seed user id: {owner_id}. This seeded account has no password; "
        "register another account to use authenticated API endpoints."
    )


if __name__ == "__main__":
    main()
