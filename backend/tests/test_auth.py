from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.config import Settings
from app.models import (
    BillSplit,
    Participant,
    Payment,
    PaymentStatus,
    PayPalInvoice,
    PayPalInvoiceStatus,
    User,
)


def register_user(
    client: TestClient,
    name: str = "Second User",
    email: str = "second@example.test",
    password: str = "second-user-password",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_user(
    client: TestClient,
    email: str = "second@example.test",
    password: str = "second-user-password",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_registration_normalizes_email_hashes_password_and_rejects_duplicates(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, engine, _ = api_client
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "  Riley  ",
            "email": "  Riley@Example.Test ",
            "password": "a-unique-password-123",
        },
    )
    assert response.status_code == 201, response.text
    profile = response.json()
    assert profile["name"] == "Riley"
    assert profile["email"] == "riley@example.test"
    assert profile["email_verified"] is False
    assert "password" not in profile
    assert "password_hash" not in profile

    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == "riley@example.test"))
        assert user is not None
        assert user.password_hash is not None
        assert user.password_hash != "a-unique-password-123"
        assert user.password_hash.startswith("$argon2")

    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Other Name",
            "email": "RILEY@example.test",
            "password": "another-unique-password",
        },
    )
    assert duplicate.status_code == 409


def test_registration_rejects_invalid_email_and_weak_password(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, _, _ = api_client
    invalid_email = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test User",
            "email": "not-an-email",
            "password": "valid-password-123",
        },
    )
    weak_password = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test User",
            "email": "valid@example.test",
            "password": "short",
        },
    )
    assert invalid_email.status_code == 422
    assert weak_password.status_code == 422


def test_login_current_user_and_password_not_exposed(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, engine, owner_id = api_client
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "API-OWNER@example.test",
            "password": "test-password-with-12-chars",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1800
    assert body["user"]["id"] == str(owner_id)
    assert "password_hash" not in body["user"]

    client.headers["Authorization"] = f"Bearer {body['access_token']}"
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == str(owner_id)

    with Session(engine) as db:
        user = db.get(User, owner_id)
        assert user is not None
        assert user.last_login_at is not None


def test_login_uses_generic_failure_for_unknown_and_incorrect_password(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, _, _ = api_client
    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": "api-owner@example.test", "password": "incorrect-password"},
    )
    unknown_email = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.test", "password": "incorrect-password"},
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_missing_invalid_and_expired_tokens_are_rejected(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, _, _ = api_client
    client.headers.pop("Authorization")
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/sessions").status_code == 401

    client.headers["Authorization"] = "Bearer not-a-jwt"
    assert client.get("/api/v1/auth/me").status_code == 401

    valid_token = login_user(
        client,
        email="api-owner@example.test",
        password="test-password-with-12-chars",
    )["access_token"]
    token_text = str(valid_token)
    tampered_token = token_text[:-1] + ("A" if token_text[-1] != "A" else "B")
    client.headers["Authorization"] = f"Bearer {tampered_token}"
    assert client.get("/api/v1/auth/me").status_code == 401

    expired = jwt.encode(
        {
            "sub": str(uuid4()),
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "type": "access",
        },
        get_settings().jwt_secret_key,
        algorithm="HS256",
    )
    client.headers["Authorization"] = f"Bearer {expired}"
    assert client.get("/api/v1/auth/me").status_code == 401

    wrong_type = jwt.encode(
        {
            "sub": str(uuid4()),
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "type": "refresh",
        },
        get_settings().jwt_secret_key,
        algorithm="HS256",
    )
    client.headers["Authorization"] = f"Bearer {wrong_type}"
    assert client.get("/api/v1/auth/me").status_code == 401

    missing_claim = jwt.encode(
        {
            "sub": str(uuid4()),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "type": "access",
        },
        get_settings().jwt_secret_key,
        algorithm="HS256",
    )
    client.headers["Authorization"] = f"Bearer {missing_claim}"
    assert client.get("/api/v1/auth/me").status_code == 401


def test_production_requires_a_strong_jwt_secret() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(app_env="production", jwt_secret_key="too-short").validate_production_security()

    Settings(
        app_env="production",
        jwt_secret_key="a-production-signing-key-with-at-least-32-characters",
    ).validate_production_security()

def test_inactive_accounts_cannot_login_or_use_private_routes(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, engine, owner_id = api_client
    with Session(engine) as db:
        user = db.get(User, owner_id)
        assert user is not None
        user.is_active = False
        db.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "api-owner@example.test",
            "password": "test-password-with-12-chars",
        },
    )
    assert login.status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 403
    assert client.get("/api/v1/sessions").status_code == 403


def test_logout_documents_stateless_token_behavior(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, _, _ = api_client
    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    assert "remains valid until expiry" in logout.json()["message"]
    assert client.get("/api/v1/auth/me").status_code == 200


def test_private_endpoints_require_bearer_authentication_in_openapi(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, _, _ = api_client
    openapi = client.get("/openapi.json").json()
    for path, path_item in openapi["paths"].items():
        if not path.startswith("/api/v1/"):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            if path in {"/api/v1/auth/register", "/api/v1/auth/login"}:
                assert "security" not in operation
            else:
                assert operation["security"] == [{"HTTPBearer": []}]


def test_users_cannot_access_or_change_other_users_resources(
    api_client: tuple[TestClient, Engine, UUID],
) -> None:
    client, engine, _ = api_client
    session_response = client.post(
        "/api/v1/sessions",
        json={"title": "Private dinner", "currency": "USD"},
    )
    session_id = session_response.json()["id"]
    receipt_response = client.post(
        f"/api/v1/sessions/{session_id}/receipts",
        json={
            "original_filename": "dinner.png",
            "mime_type": "image/png",
            "storage_key": "private/dinner.png",
        },
    )
    receipt_id = receipt_response.json()["id"]
    item_response = client.post(
        f"/api/v1/receipts/{receipt_id}/items",
        json={
            "name": "Pasta",
            "quantity": "1",
            "unit_price": "10.00",
            "total_price": "10.00",
        },
    )
    item_id = item_response.json()["id"]
    participant_response = client.post(
        f"/api/v1/sessions/{session_id}/participants",
        json={"name": "Guest"},
    )
    participant_id = participant_response.json()["id"]
    assignment_response = client.post(
        f"/api/v1/receipt-items/{item_id}/assignments",
        json={"participant_id": participant_id, "share_type": "individual"},
    )
    assignment_id = assignment_response.json()["id"]

    with Session(engine) as db:
        participant = db.get(Participant, UUID(participant_id))
        assert participant is not None
        split = BillSplit(
            bill_session_id=UUID(session_id),
            participant_id=participant.id,
            subtotal=Decimal("10.00"),
            tax_share=Decimal("0.80"),
            tip_share=Decimal("2.00"),
            service_charge_share=Decimal("0.00"),
            total_owed=Decimal("12.80"),
            currency="USD",
            calculation_version="test-v1",
        )
        db.add(split)
        db.flush()
        invoice = PayPalInvoice(
            bill_session_id=UUID(session_id),
            participant_id=participant.id,
            bill_split_id=split.id,
            invoice_status=PayPalInvoiceStatus.SENT,
            amount=Decimal("12.80"),
            currency="USD",
        )
        db.add(invoice)
        db.flush()
        payment = Payment(
            paypal_invoice_id=invoice.id,
            amount=Decimal("12.80"),
            currency="USD",
            status=PaymentStatus.COMPLETED,
        )
        db.add(payment)
        db.commit()
        invoice_id = str(invoice.id)

    register_user(client)
    second_login = login_user(client)
    client.headers["Authorization"] = f"Bearer {second_login['access_token']}"

    assert client.get("/api/v1/sessions").json()["total"] == 0
    private_requests = [
        ("GET", f"/api/v1/sessions/{session_id}", None),
        ("PATCH", f"/api/v1/sessions/{session_id}", {"title": "stolen"}),
        ("POST", f"/api/v1/sessions/{session_id}/cancel", None),
        ("GET", f"/api/v1/sessions/{session_id}/receipts", None),
        ("GET", f"/api/v1/receipts/{receipt_id}", None),
        ("PATCH", f"/api/v1/receipts/{receipt_id}", {"extracted_merchant_name": "x"}),
        ("GET", f"/api/v1/receipts/{receipt_id}/items", None),
        ("PATCH", f"/api/v1/receipt-items/{item_id}", {"name": "stolen"}),
        ("DELETE", f"/api/v1/receipt-items/{item_id}", None),
        ("GET", f"/api/v1/participants/{participant_id}", None),
        ("PATCH", f"/api/v1/participants/{participant_id}", {"name": "stolen"}),
        ("DELETE", f"/api/v1/participants/{participant_id}", None),
        ("GET", f"/api/v1/receipt-items/{item_id}/assignments", None),
        ("PATCH", f"/api/v1/assignments/{assignment_id}", {"quantity": "2"}),
        ("DELETE", f"/api/v1/assignments/{assignment_id}", None),
        ("GET", f"/api/v1/sessions/{session_id}/splits", None),
        ("GET", f"/api/v1/sessions/{session_id}/invoices", None),
        ("GET", f"/api/v1/invoices/{invoice_id}", None),
        ("GET", f"/api/v1/invoices/{invoice_id}/payments", None),
        ("GET", f"/api/v1/sessions/{session_id}/payments", None),
    ]
    for method, path, body in private_requests:
        response = client.request(method, path, json=body)
        assert response.status_code == 404, (method, path, response.text)

    cross_session_create = client.post(
        f"/api/v1/sessions/{session_id}/participants",
        json={"name": "Injected"},
    )
    assert cross_session_create.status_code == 404
