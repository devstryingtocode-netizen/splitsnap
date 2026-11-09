# Splitsnap

Splitsnap is a foundation for an AI-assisted restaurant bill-splitting app with
PayPal invoicing. The frontend and backend are independent applications in this
repository and can be started separately.

## Architecture

- **Frontend:** Next.js App Router, React, TypeScript, Tailwind CSS, and Lucide
  React. It talks to the backend through a small typed API client.
- **Backend:** FastAPI with Pydantic settings and validation. Versioned API
  routers are reserved for receipts, chat, splits, invoices, and payments.
- **Persistence:** SQLAlchemy 2.x and Alembic are configured for PostgreSQL.
  SQLite is the local-development default; set `DATABASE_URL` to a PostgreSQL
  URL when a server is available.
- **AI and payments:** Provider credentials and service configuration belong
  only on the backend. Provider integrations are intentionally not implemented
  yet; their future service boundaries are documented in
  [docs/architecture.md](./docs/architecture.md).

**Financial correctness is a backend responsibility.** AI may interpret
receipts and natural-language assignments, but ordinary, deterministic backend
code must calculate every amount. Sending any invoice must require explicit
user approval.

## Prerequisites

- Node.js 20.9 or newer and npm
- Python 3.10 or newer
- PostgreSQL for production (not required for local startup)

## Configure the environment

Copy the templates for each app:

```bash
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env
```

Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local`. Set the backend values in
`backend/.env`, including a random `JWT_SECRET_KEY` of at least 32 characters.
Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`.
Keep real `.env` files out of Git. The root [.env.example](./.env.example)
summarizes the supported variables and contains placeholders only.

## Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Useful checks:

```bash
npm run typecheck
npm run build
```

## Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The health endpoint is [http://localhost:8000/health](http://localhost:8000/health);
interactive API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs).
The application routes are grouped under `/api/v1`.

### Register and authenticate

After applying migrations, register an account and log in. Registration never
marks email verified and returns no password data. Login accepts JSON and
returns a 30-minute JWT:

```bash
cd backend
alembic upgrade head
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"name":"Example User","email":"user@example.test","password":"<choose-a-unique-password-of-at-least-12-characters>"}'
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.test","password":"<the-password-you-chose>"}'
```

Send the returned `access_token` as `Authorization: Bearer <token>` on private
API requests. In Swagger at `/docs`, log in through the JSON `/auth/login`
endpoint, copy `access_token`, select **Authorize**, and paste the token. All
bill-session and related-resource endpoints require an active authenticated
user. Session ownership is derived from that user; caller-supplied `owner_id`
is rejected.

The frontend API client keeps the token in memory only, attaches it to private
requests, clears it after a 401, and discards it on logout. Reloading the page
also clears it. Logout is stateless: the server does not revoke a token, and a
copied token remains valid until expiry.

Optional sample data can be loaded with `APP_ENV=development python -m
app.seed`. It creates a legacy-style sample user with no password set, so that
user cannot log in; register an account for authenticated API use. Seed data
must not be treated as credentials.

## Database

The database schema currently contains:

- `User` owns bill sessions and may optionally be linked to a participant.
- `BillSession` owns participants, one receipt, calculated split records, and
  invoice records.
- `Participant` may be a guest without a Splitsnap user account.
- `Receipt` stores receipt metadata and a storage reference, not image bytes;
  it owns receipt items.
- `ReceiptItem` links to participants through `ItemAssignment`, which records
  an individual, equal, or quantity-based assignment without calculating it.
- `BillSplit` stores a versioned per-participant result. A unique constraint
  allows at most one split per participant per session.
- `PayPalInvoice` records the invoice state for a split; `Payment` stores
  payment events separately. An invoice being sent does not mark it paid.

UUID columns use PostgreSQL UUID and SQLite-compatible UUID storage. Monetary
values use `NUMERIC(14, 2)` (up to 12 integer digits and two fractional digits);
quantities use `NUMERIC(12, 3)`. Python values are `Decimal`, never float.
Timestamps are timezone-aware UTC in application code. Currency is stored on
each relevant record as an uppercase three-letter code; the schema does not
convert currencies or assume USD. Original receipt totals and split amounts
remain separate.

After setting up `backend/.env`, apply the checked-in migration:

```bash
cd backend
alembic upgrade head
```

The authentication migration normalizes existing account emails to lowercase
and trims surrounding whitespace. It stops before changing the schema if
existing accounts contain addresses that collide after normalization; resolve
those duplicate accounts before retrying.

Rollback the schema with `alembic downgrade base`. Apply it again with
`alembic upgrade head`. The local SQLite database is `backend/splitsnap.db`;
tests use isolated in-memory or temporary SQLite databases instead.

Optional development data can be loaded after migrating:

```bash
cd backend
APP_ENV=development python -m app.seed
```

The seed script refuses to run outside development/test and is idempotent. It
only inserts representative records and does not execute automatically.

Install development dependencies and run the backend checks:

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest
python -m compileall -q app tests
```

## Current scope

The current API supports session and participant CRUD, receipt metadata and
item management, item assignments, and read-only access to stored splits,
invoices, and payment records. It does not implement receipt image uploads,
AI extraction/chat, financial calculations, or PayPal operations. Receipt
metadata creation does not mark a receipt as scanned; extraction status remains
pending. Assignments record user input only and do not calculate amounts.

The versioned routes are:

- `/sessions` and `/sessions/{session_id}/cancel`
- `/sessions/{session_id}/participants` and `/participants/{participant_id}`
- `/sessions/{session_id}/receipts` and `/receipts/{receipt_id}`
- `/receipts/{receipt_id}/items` and `/receipt-items/{item_id}`
- `/receipt-items/{item_id}/assignments` and `/assignments/{assignment_id}`
- `/sessions/{session_id}/splits`
- `/sessions/{session_id}/invoices`, `/invoices/{invoice_id}`, and
  `/invoices/{invoice_id}/payments`
- `/sessions/{session_id}/payments`

Monetary values are validated and serialized as decimal strings to avoid
lossy binary floating-point representation. API errors use a consistent
`{"error":{"code":"...","message":"..."}}` shape; validation errors also
include field details. Swagger and ReDoc are available at `/docs` and `/redoc`.

## Authentication and security limitations

- Passwords are hashed with Argon2; JWT access tokens are signed using HS256
  and expire after the configured `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Existing users migrated without a password hash cannot log in until a
  password-reset flow is provided; no credentials are assigned automatically.
- Email verification delivery, rate limiting, MFA, refresh tokens, and token
  revocation are not implemented. Logout only clears frontend memory.
- The frontend currently uses an in-memory bearer token rather than an
  HttpOnly cookie. Do not persist it in localStorage or expose backend
  secrets through `NEXT_PUBLIC_*` settings.
- The token secret must be unique and strong in every deployed environment.
  Production startup fails when `JWT_SECRET_KEY` is shorter than 32 characters.
- The development seed account has no password and cannot authenticate.

Example local API calls after registering and logging in:

```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <access-token>' \
  -d '{"title":"Dinner with friends","currency":"USD"}'
curl 'http://localhost:8000/api/v1/sessions?limit=20&offset=0' \
  -H 'Authorization: Bearer <access-token>'
```
