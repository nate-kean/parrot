"""add per user affixes

Revision ID: 4d677d1d0bc2
Revises: dc3de2bdff39
Create Date: 2025-03-02 14:40:30.855919

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "4d677d1d0bc2"
down_revision: str | None = "dc3de2bdff39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.add_column(
		"membership",
		sa.Column(
			"custom_prefix", sa.String(), nullable=False, server_default=""
		),
	)
	op.add_column(
		"membership",
		sa.Column(
			"custom_suffix", sa.String(), nullable=False, server_default=""
		),
	)


def downgrade() -> None:
	op.drop_column("membership", "custom_suffix")
	op.drop_column("membership", "custom_prefix")
