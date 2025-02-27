"""
Take Parrot's real database and remove a certain proportion of its messages.
For testing on a smaller version of the real database.
"""

import sqlmodel as sm
from parrot import config
from parrot.alembic import prepare_for_migration
from parrot.alembic.common import count
from parrot.alembic.models import v1
from parrot.config import logger


V1_REVISION = "fe3138aef0bd"

PARING_FACTOR = 2_0000  # 4,000,000 → 200 messages


def main() -> None:
	prepare_for_migration.main()

	engine = sm.create_engine(config.db_url)
	sm.SQLModel.metadata.create_all(engine)
	session = sm.Session(engine)

	logger.info("Paring message table")
	logger.info(f"Initial message count: {count(session, v1.Messages.id)}")
	session.execute(
		sm.text("""
			DELETE FROM messages WHERE id IN (
				SELECT id
				FROM (
					SELECT id, ROW_NUMBER() OVER () row_num
					FROM messages
				) t
				WHERE MOD(row_num, :factor) != 0
			)
		"""),
		{"factor": PARING_FACTOR},
	)

	logger.info(f"New message count: {count(session, v1.Messages.id)}")


if __name__ == "__main__":
	main()
