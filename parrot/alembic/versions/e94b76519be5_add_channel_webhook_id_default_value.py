"""add channel webhook id default value

Revision ID: e94b76519be5
Revises: 3757315eec4c
Create Date: 2025-01-22 23:34:25.443986

"""

from collections.abc import Sequence

import sqlalchemy as sa
from parrot.alembic.common import batch_alter_table


# revision identifiers, used by Alembic.
revision: str = "e94b76519be5"
down_revision: str | None = "3757315eec4c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	with batch_alter_table("channel") as bop:
		bop.alter_column("webhook_id", server_default=sa.null())


def downgrade() -> None:
	with batch_alter_table("channel") as bop:
		bop.alter_column("webhook_id", server_default=None)
