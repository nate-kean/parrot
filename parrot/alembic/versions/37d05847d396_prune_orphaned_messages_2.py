"""prune orphaned messages 2

Orphaned messages that the first pruning didn't find lol


Revision ID: 37d05847d396
Revises: f49ff9c35283
Create Date: 2025-02-14 18:23:12.984593

"""

import logging
from collections.abc import Sequence

import sqlmodel as sm
from parrot.alembic.common import cleanup_models, count

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "37d05847d396"
down_revision: str | None = "f49ff9c35283"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	from parrot.alembic.models import r7d0ffe4179c6

	session = sm.Session(op.get_bind())
	logging.info(
		f"Initial message count: {count(session, r7d0ffe4179c6.Message.id)}"
	)
	session.execute(
		sm.text("""
			DELETE FROM message
			WHERE message.rowid IN (
				SELECT rowid
				FROM pragma_foreign_key_check() as fkc
				WHERE fkc."table" = "message"
					AND fkc."parent" = "membership"
			)
		""")
	)
	logging.info(
		f"New message count: {count(session, r7d0ffe4179c6.Message.id)}"
	)
	session.commit()
	cleanup_models(r7d0ffe4179c6)


def downgrade() -> None:
	logging.warning("No action taken: this migration is irreversible.")
