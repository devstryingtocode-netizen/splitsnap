# Architecture notes

## Application boundaries

- `frontend/` contains the user interface and a public-API-only configuration.
- `backend/` owns validation, persistence, provider credentials, and business
  rules. API routes are grouped by feature under `/api/v1`.
- AI and PayPal code will be added behind backend service interfaces so API
  routes do not depend directly on a vendor SDK.

## Financial safety

AI output is untrusted input. It may help extract receipt fields or interpret
which person had which item, but deterministic backend code must validate the
input and calculate shares using exact monetary arithmetic. The backend must
persist a reviewable split and must not send invoices until the user explicitly
approves it.

## Integrations

AI provider selection is intentionally open. `AI_API_KEY` and `AI_MODEL` are
backend-only configuration points; no provider client or credentials are
currently wired. Typed provider protocols define multimodal receipt extraction
and natural-language item-assignment boundaries. Their outputs are suggestions
and validated receipt data, not financial calculations.

PayPal integration belongs in its own backend service and should use the
Invoicing API v2. Development must use PayPal Sandbox. The `PAYPAL_BASE_URL`
setting defaults to the Sandbox API origin; no invoice operations are
implemented in this foundation. The provider protocol exposes draft creation
only; sending is intentionally absent until an explicit approval workflow is
designed.

## Persistence

SQLAlchemy 2.x models and Alembic migrations own persisted data. `DATABASE_URL`
defaults to a local SQLite database for startup convenience; production
deployments should provide a PostgreSQL URL and apply migrations.

### Models and relationships

- `User` has many owned `BillSession` records. A user can also be linked to
  optional `Participant` records; deleting the user nulls those links.
- `BillSession` belongs to an owner and owns participants, one optional
  `Receipt`, `BillSplit` records, and `PayPalInvoice` records. The one-to-one
  receipt association is represented by a unique, required
  `Receipt.bill_session_id`; no circular foreign key is needed.
- `Participant` belongs to one bill session and can be a guest without a user
  account. Its contact email and PayPal email are separate fields.
- `Receipt` stores extraction metadata and a `storage_key` reference only; it
  does not store image bytes. It owns `ReceiptItem` records.
- `ReceiptItem` has `ItemAssignment` links to participants. An assignment
  stores its share type and quantity; it does not calculate any financial
  allocation.
- `BillSplit` belongs to a bill session and participant. A unique
  `(bill_session_id, participant_id)` constraint permits at most one split
  record for that pair. Each split may have one `PayPalInvoice`.
- `PayPalInvoice` belongs to a session, participant, and split, and owns
  `Payment` event records. Invoice status and payment status are independent:
  sending an invoice does not mark its payment complete.

Foreign keys are indexed where needed, status fields have indexes, and database
constraints enforce uniqueness, valid enum values, non-negative financial
amounts/quantities, and uppercase three-character currency codes. Relationships
use delete cascades for owned records and `SET NULL` for optional user links to
avoid orphan rows. A database trigger additionally blocks participant deletion
when a split or invoice references it, preserving invoice/payment history even
if a caller bypasses the API service guard.

### Precision and currency

Money uses `NUMERIC(14, 2)`, providing twelve whole-number digits and two
fractional digits. Item and assignment quantities use `NUMERIC(12, 3)`. Python
uses `Decimal` for these columns. Receipt totals and saved split amounts are
separate fields so the extracted source values remain available for review and
auditing; `calculation_version` records which future calculation algorithm
produced a split.

Currency is explicit on each bill, split, invoice, and payment, and may be
unknown on an unreviewed receipt. Values must be uppercase three-character
codes. The application does not silently convert currencies or assume USD.

### Timestamps and migrations

UUID primary keys map to native PostgreSQL UUID columns and remain compatible
with SQLite. Created/updated timestamps use timezone-aware UTC values in the
application; SQLite round-tripped timestamps are normalized back to UTC.

Run `alembic upgrade head` from `backend/` to apply the initial schema, or
`alembic downgrade base` to remove it. Development and automated tests use
SQLite, while production can use PostgreSQL through `DATABASE_URL`. Tests use
isolated databases and do not touch the development database.

Optional sample records can be loaded after migration with
`APP_ENV=development python -m app.seed` from `backend/`. The script is
idempotent, refuses production environments, prints the development user's
UUID, and is never run automatically.

## API and ownership boundary

CRUD endpoints are grouped under `/api/v1` for sessions, participants,
receipts, receipt items, assignments, splits, invoices, and payments. Request
and response schemas are separate from SQLAlchemy models. Mutations are
committed as database transactions; unique and foreign-key conflicts return
structured errors. Receipt extraction status cannot be set by API clients,
financial records are read-only, and participant/item mutations are blocked
when doing so would alter financial history.

Authentication is not implemented. For local development only, API ownership
comes from the server-side `DEVELOPMENT_OWNER_ID`, which must reference an
existing user row; the client cannot specify an owner. The API scopes resource
queries to that configured user. This is not a production security boundary:
any caller who can reach the API can act as the configured development owner.
Real authentication and per-user authorization must be implemented before
deployment.
