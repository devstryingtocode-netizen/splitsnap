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
`backend/.env`; for local API use, follow the development-owner setup below.
Generate a unique `SECRET_KEY` before deploying. Keep real `.env` files out of
Git. The root [.env.example](./.env.example) summarizes the supported
variables and contains placeholders only.

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

### Development owner setup

Authentication is not implemented. To support local API requests without
accepting a client-supplied owner ID, the backend uses the temporary
`DEVELOPMENT_OWNER_ID` setting. It must reference an existing row in `users`;
the API does not create one implicitly.

After migrating, seed the optional development data and copy the printed UUID
into `backend/.env` as `DEVELOPMENT_OWNER_ID`:

```bash
cd backend
alembic upgrade head
APP_ENV=development python -m app.seed
```

Restart the backend after setting the owner UUID. If it is unset, invalid, or
references no existing user, API requests return a clear `503` configuration
error. This single-owner setup is strictly for development and is not
production-safe. Real authentication, authorization, and ownership isolation
must be implemented before deployment.

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

Rollback the schema with `alembic downgrade base`. Apply it again with
`alembic upgrade head`. The local SQLite database is `backend/splitsnap.db`;
tests use isolated in-memory or temporary SQLite databases instead.

Optional development data can be loaded after migrating:

```bash
cd backend
APP_ENV=development python -m app.seed
```

The seed script refuses to run outside development/test and is idempotent.
It only inserts representative records and does not execute automatically.
It prints the seeded development user's UUID for `DEVELOPMENT_OWNER_ID`.

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

Example local API calls after configuring the development owner:

```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dinner with friends","currency":"USD"}'
curl 'http://localhost:8000/api/v1/sessions?limit=20&offset=0'
```
