"""Protect participant financial history and duplicate contact emails.

Revision ID: d8238d2c132c
Revises: f0bafed4c28a
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8238d2c132c"
down_revision: Union[str, None] = "f0bafed4c28a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_index(
        "uq_participants_session_email",
        "participants",
        ["bill_session_id", sa.text("lower(email)")],
        unique=True,
        sqlite_where=sa.text("email IS NOT NULL"),
        postgresql_where=sa.text("email IS NOT NULL"),
    )

    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER prevent_participant_delete_with_financial_history
            BEFORE DELETE ON participants
            FOR EACH ROW
            WHEN EXISTS (
                SELECT 1 FROM bill_splits WHERE participant_id = OLD.id
            ) OR EXISTS (
                SELECT 1 FROM paypal_invoices WHERE participant_id = OLD.id
            )
            BEGIN
                SELECT RAISE(ABORT, 'participant has financial history');
            END
            """
        )
    elif dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION prevent_participant_delete_with_financial_history()
            RETURNS trigger AS $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM bill_splits WHERE participant_id = OLD.id
                ) OR EXISTS (
                    SELECT 1 FROM paypal_invoices WHERE participant_id = OLD.id
                ) THEN
                    RAISE EXCEPTION 'participant has financial history'
                        USING ERRCODE = 'restrict_violation';
                END IF;
                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER prevent_participant_delete_with_financial_history
            BEFORE DELETE ON participants
            FOR EACH ROW
            EXECUTE FUNCTION prevent_participant_delete_with_financial_history()
            """
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute(
            "DROP TRIGGER prevent_participant_delete_with_financial_history"
        )
    elif dialect == "postgresql":
        op.execute(
            """
            DROP TRIGGER prevent_participant_delete_with_financial_history
            ON participants
            """
        )
        op.execute(
            "DROP FUNCTION prevent_participant_delete_with_financial_history()"
        )
    op.drop_index("uq_participants_session_email", table_name="participants")
