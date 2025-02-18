"""remove can_speak_here

Just set this permission on Discord's side

Revision ID: dc3de2bdff39
Revises: 37d05847d396
Create Date: 2025-02-17 20:13:29.094933

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "dc3de2bdff39"
down_revision: str | None = "37d05847d396"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.drop_column("channel", "can_speak_here")


def downgrade() -> None:
	op.add_column(
		"channel",
		sa.Column(
			"can_speak_here",
			type_=sa.Boolean(),
			nullable=False,
			server_default=sa.false(),
		),
	)
