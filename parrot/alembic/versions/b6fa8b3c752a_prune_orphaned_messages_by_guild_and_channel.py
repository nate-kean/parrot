"""prune orphaned messages by guild and channel

Prune messages that the migration 7d0ffe4179c6 wasn't able to determine a
guild or channel for.

WARNING!!! This migration is irreversible. You should have a backup of your
database before running migrations anyway but just saying

Revision ID: b6fa8b3c752a
Revises: 7d0ffe4179c6
Create Date: 2025-01-24 23:38:55.172176

"""

import logging
from collections.abc import Sequence

import sqlmodel as sm
from parrot.alembic.common import cleanup_models, count

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b6fa8b3c752a"
down_revision: str | None = "7d0ffe4179c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	from parrot.alembic.models import r7d0ffe4179c6
	from parrot.alembic.models.r7d0ffe4179c6 import ErrorCode

	session = sm.Session(op.get_bind())
	logging.info(
		f"Initial message count: {count(session, r7d0ffe4179c6.Message.id)}"
	)
	session.execute(
		sm.text(
			"DELETE FROM message "
			"WHERE guild_id = :guild_id OR channel_id = :channel_id"
		),
		{
			"guild_id": ErrorCode.NOT_FOUND.value,
			"channel_id": ErrorCode.NOT_FOUND.value,
		},
	)
	logging.info(
		f"New message count: {count(session, r7d0ffe4179c6.Message.id)}"
	)
	session.commit()

	cleanup_models(r7d0ffe4179c6)


def downgrade() -> None:
	logging.warning("No action taken: this migration is irreversible.")
