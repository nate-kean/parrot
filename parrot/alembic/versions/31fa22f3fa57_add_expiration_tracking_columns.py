"""add expiration tracking columns

Columns that track how long it's been since certain objects have been deleted on
Discord's end, so Parrot can delete them on her end at a later time, since
recouping the information that would be deleted is costly so we want to be sure
it won't be put back quickly on Discord's end.

Revision ID: 31fa22f3fa57
Revises: 1161df792f22
Create Date: 2025-02-12 23:39:10.344533

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "31fa22f3fa57"
down_revision: str | None = "1161df792f22"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.add_column("guild", sa.Column("gone_since", sa.Integer(), nullable=True))
	op.add_column(
		"membership", sa.Column("ended_since", sa.Integer(), nullable=True)
	)


def downgrade() -> None:
	op.drop_column("membership", "ended_since")
	op.drop_column("guild", "gone_since")
