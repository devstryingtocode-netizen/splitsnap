"""Add user authentication fields and case-insensitive email uniqueness.

Revision ID: 91f87c4ab2d1
Revises: d8238d2c132c
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "91f87c4ab2d1"
down_revision: Union[str, None] = "d8238d2c132c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not op.get_context().as_sql:
        duplicates = op.get_bind().execute(
            sa.text(
                """
                SELECT lower(trim(email)), count(*)
                FROM users
                GROUP BY lower(trim(email))
                HAVING count(*) > 1
                """
            )
        ).first()
        if duplicates is not None:
            raise RuntimeError(
                "Cannot add case-insensitive user email uniqueness: existing "
                "users contain duplicate email addresses differing only by "
                "case. Resolve those accounts before applying this migration."
            )

    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(sa.text("UPDATE users SET email = lower(trim(email))"))
    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "is_active")
    op.drop_column("users", "password_hash")
