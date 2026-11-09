from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    BillSession,
    BillSplit,
    Participant,
    Payment,
    PaymentStatus,
    PayPalInvoice,
    PayPalInvoiceStatus,
    Receipt,
    ReceiptExtractionStatus,
    User,
)


def create_session(client: TestClient, currency: str = "USD") -> dict[str, object]:
    response = client.post(
        "/api/v1/sessions",
        json={"title": "Friday Dinner", "currency": currency},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_receipt(client: TestClient, session_id: str) -> dict[str, object]:
    response = client.post(
        f"/api/v1/sessions/{session_id}/receipts",
        json={
            "original_filename": "dinner.png",
            "mime_type": "image/png",
            "storage_key": "test/receipts/dinner.png",
            "currency": "USD",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_item(client: TestClient, receipt_id: str, name: str = "Pasta") -> dict[str, object]:
    response = client.post(
        f"/api/v1/receipts/{receipt_id}/items",
        json={
            "name": name,
            "quantity": "1.250",
            "unit_price": "12.34",
            "total_price": "15.43",
            "category": "main",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_participant(
    client: TestClient, session_id: str, name: str = "Morgan"
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/sessions/{session_id}/participants",
        json={"name": name, "email": f"{name.lower()}@example.test"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_session_and_participant_crud(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, _, owner_id = api_client
    created = create_session(client)

    assert created["owner_id"] == str(owner_id)
    assert created["status"] == "draft"
    assert created["participant_count"] == 0
    assert created["total_amount"] is None

    page = client.get("/api/v1/sessions?limit=1&offset=0")
    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert len(page.json()["items"]) == 1

    session_id = str(created["id"])
    detail = client.get(f"/api/v1/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["participants"] == []

    updated = client.patch(
        f"/api/v1/sessions/{session_id}",
        json={"title": "Updated dinner"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated dinner"

    participant = create_participant(client, session_id)
    participant_id = str(participant["id"])
    assert participant["email"] == "morgan@example.test"
    assert participant["paypal_email"] is None
    duplicate = client.post(
        f"/api/v1/sessions/{session_id}/participants",
        json={"name": "Different display name", "email": "MORGAN@example.test"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_participant"

    listed = client.get(f"/api/v1/sessions/{session_id}/participants")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    changed = client.patch(
        f"/api/v1/participants/{participant_id}",
        json={"paypal_email": "billing@example.test"},
    )
    assert changed.status_code == 200
    assert changed.json()["paypal_email"] == "billing@example.test"
    assert client.get(f"/api/v1/participants/{participant_id}").status_code == 200

    deleted = client.delete(f"/api/v1/participants/{participant_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/participants/{participant_id}").status_code == 404


def test_session_validation_cancellation_and_development_owner(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, _, _ = api_client
    assert client.post(
        "/api/v1/sessions",
        json={"title": "Wrong currency", "currency": "usd"},
    ).status_code == 422
    assert client.post(
        "/api/v1/sessions",
        json={
            "title": "Client controlled owner",
            "currency": "USD",
            "owner_id": str(uuid4()),
        },
    ).status_code == 422

    session = create_session(client)
    session_id = str(session["id"])
    cancelled = client.post(f"/api/v1/sessions/{session_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.post(f"/api/v1/sessions/{session_id}/cancel").status_code == 409
    assert client.get("/api/v1/sessions/not-a-uuid").status_code == 422


def test_receipt_items_and_assignment_crud_and_cross_session_guard(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, engine, _ = api_client
    session = create_session(client)
    session_id = str(session["id"])
    mismatched_currency = client.post(
        f"/api/v1/sessions/{session_id}/receipts",
        json={
            "original_filename": "dinner.png",
            "mime_type": "image/png",
            "storage_key": "test/receipts/dinner.png",
            "currency": "EUR",
        },
    )
    assert mismatched_currency.status_code == 400
    assert mismatched_currency.json()["error"]["code"] == "currency_mismatch"
    receipt = create_receipt(client, session_id)
    receipt_id = str(receipt["id"])

    assert receipt["extraction_status"] == "pending"
    assert receipt["items"] == []
    assert client.get(f"/api/v1/sessions/{session_id}/receipts").status_code == 200
    assert client.get(f"/api/v1/receipts/{receipt_id}").status_code == 200
    assert client.post(
        f"/api/v1/sessions/{session_id}/receipts",
        json={
            "original_filename": "other.png",
            "mime_type": "image/png",
            "storage_key": "test/other.png",
        },
    ).status_code == 409

    item = create_item(client, receipt_id)
    item_id = str(item["id"])
    assert item["unit_price"] == "12.34"
    assert item["total_price"] == "15.43"
    assert item["quantity"] == "1.250"
    assert client.get(f"/api/v1/receipts/{receipt_id}/items").status_code == 200
    assert client.post(
        f"/api/v1/receipts/{receipt_id}/items",
        json={
            "name": "Invalid item",
            "quantity": "-1",
            "unit_price": "-0.01",
            "total_price": "1.00",
        },
    ).status_code == 422

    updated_item = client.patch(
        f"/api/v1/receipt-items/{item_id}",
        json={"name": "Fresh pasta"},
    )
    assert updated_item.status_code == 200
    assert updated_item.json()["name"] == "Fresh pasta"

    participant = create_participant(client, session_id)
    assignment_response = client.post(
        f"/api/v1/receipt-items/{item_id}/assignments",
        json={
            "participant_id": participant["id"],
            "quantity": "0.500",
            "share_type": "quantity_based",
        },
    )
    assert assignment_response.status_code == 201, assignment_response.text
    assignment = assignment_response.json()
    assignment_id = str(assignment["id"])
    assert assignment["quantity"] == "0.500"
    assert len(client.get(f"/api/v1/receipt-items/{item_id}/assignments").json()) == 1
    assert client.patch(
        f"/api/v1/assignments/{assignment_id}",
        json={"quantity": "0.750"},
    ).json()["quantity"] == "0.750"

    second_session = create_session(client)
    unrelated = create_participant(client, str(second_session["id"]), "Unrelated")
    cross_session = client.post(
        f"/api/v1/receipt-items/{item_id}/assignments",
        json={"participant_id": unrelated["id"]},
    )
    assert cross_session.status_code == 400
    assert cross_session.json()["error"]["code"] == "cross_session_assignment"
    assert client.delete(f"/api/v1/receipt-items/{item_id}").status_code == 409

    assert client.delete(f"/api/v1/assignments/{assignment_id}").status_code == 204
    assert client.delete(f"/api/v1/receipt-items/{item_id}").status_code == 204
    assert client.get(f"/api/v1/receipt-items/{item_id}").status_code == 405

    with Session(engine) as db:
        saved_receipt = db.scalar(select(Receipt).where(Receipt.id == UUID(receipt_id)))
        assert saved_receipt is not None
        assert saved_receipt.extraction_status == ReceiptExtractionStatus.PENDING


def test_receipt_metadata_patch_and_numeric_validation(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, _, _ = api_client
    session = create_session(client)
    receipt = create_receipt(client, str(session["id"]))
    receipt_id = str(receipt["id"])

    patch = client.patch(
        f"/api/v1/receipts/{receipt_id}",
        json={
            "extracted_merchant_name": "The Garden Room",
            "subtotal": "32.10",
        },
    )
    assert patch.status_code == 200
    assert patch.json()["extracted_merchant_name"] == "The Garden Room"
    assert patch.json()["subtotal"] == "32.10"
    assert patch.json()["extraction_status"] == "pending"

    too_precise = client.patch(
        f"/api/v1/receipts/{receipt_id}",
        json={"total_amount": "1.001"},
    )
    assert too_precise.status_code == 422
    assert client.patch(
        f"/api/v1/receipts/{receipt_id}",
        json={"original_filename": None},
    ).status_code == 422


def test_stored_financial_records_are_read_only_and_protected(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, engine, owner_id = api_client
    session_json = create_session(client)
    session_id = UUID(str(session_json["id"]))
    with Session(engine) as db:
        owner = db.get(User, owner_id)
        assert owner is not None
        bill_session = db.get(BillSession, session_id)
        assert bill_session is not None
        participant = Participant(
            bill_session_id=session_id,
            name="Historically billed",
            email="history@example.test",
        )
        db.add(participant)
        db.flush()
        split = BillSplit(
            bill_session_id=session_id,
            participant_id=participant.id,
            subtotal=Decimal("10.01"),
            tax_share=Decimal("0.80"),
            tip_share=Decimal("2.00"),
            service_charge_share=Decimal("0.00"),
            total_owed=Decimal("12.81"),
            currency="USD",
            calculation_version="test-v1",
        )
        db.add(split)
        db.flush()
        invoice = PayPalInvoice(
            bill_session_id=session_id,
            participant_id=participant.id,
            bill_split_id=split.id,
            paypal_invoice_id="API-TEST-INVOICE",
            invoice_number="API-TEST-001",
            invoice_status=PayPalInvoiceStatus.SENT,
            amount=Decimal("12.81"),
            currency="USD",
        )
        db.add(invoice)
        db.flush()
        payment = Payment(
            paypal_invoice_id=invoice.id,
            external_payment_id="API-TEST-PAYMENT",
            amount=Decimal("12.81"),
            currency="USD",
            status=PaymentStatus.COMPLETED,
        )
        db.add(payment)
        db.commit()
        participant_id = participant.id
        invoice_id = invoice.id

    assert client.get(f"/api/v1/sessions/{session_id}/splits").json()[0][
        "total_owed"
    ] == "12.81"
    assert client.get(f"/api/v1/sessions/{session_id}/invoices").json()[0][
        "invoice_status"
    ] == "sent"
    invoice_response = client.get(f"/api/v1/invoices/{invoice_id}")
    assert invoice_response.status_code == 200
    assert invoice_response.json()["amount"] == "12.81"
    assert len(client.get(f"/api/v1/invoices/{invoice_id}/payments").json()) == 1
    assert len(client.get(f"/api/v1/sessions/{session_id}/payments").json()) == 1
    assert client.patch(
        f"/api/v1/invoices/{invoice_id}",
        json={"invoice_status": "paid"},
    ).status_code == 405
    assert client.delete(f"/api/v1/participants/{participant_id}").status_code == 409


def test_financial_read_endpoints_return_empty_arrays_and_missing_errors(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, _, _ = api_client
    session = create_session(client)
    session_id = str(session["id"])

    assert client.get(f"/api/v1/sessions/{session_id}/splits").json() == []
    assert client.get(f"/api/v1/sessions/{session_id}/invoices").json() == []
    assert client.get(f"/api/v1/sessions/{session_id}/payments").json() == []
    missing = client.get(f"/api/v1/invoices/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_documentation_and_owner_configuration_errors(
    api_client: tuple[TestClient, Engine, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = api_client
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    openapi = client.get("/openapi.json").json()
    assert "/api/v1/sessions" in openapi["paths"]
    assert "/api/v1/sessions/{session_id}/receipts" in openapi["paths"]
    assert "/api/v1/receipts/{receipt_id}" in openapi["paths"]

    monkeypatch.setenv("DEVELOPMENT_OWNER_ID", str(uuid4()))
    get_settings.cache_clear()
    missing_owner = client.get("/api/v1/sessions")
    assert missing_owner.status_code == 503
    assert missing_owner.json()["error"]["code"] == "development_owner_not_found"

    monkeypatch.delenv("DEVELOPMENT_OWNER_ID")
    get_settings.cache_clear()
    response = client.get("/api/v1/sessions")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "development_owner_not_configured"
    get_settings.cache_clear()
