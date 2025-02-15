"""v1 schema

Revision ID: fe3138aef0bd
Revises:
Create Date: 2025-01-14 22:41:54.853953

"""

from collections.abc import Sequence

import sqlmodel as sm
from parrot.alembic.common import cleanup_models

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "fe3138aef0bd"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	from parrot.alembic.models import v1  # noqa: F401 -- for SQLModel

	sm.SQLModel.metadata.create_all(op.get_bind())
	cleanup_models(v1)


def downgrade() -> None:
	op.drop_table("guilds")
	op.drop_table("messages")
	op.drop_table("channels")
	op.drop_table("users")
