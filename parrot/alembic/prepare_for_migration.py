"""
Add the "alembic_version" marker to a database to allow Alembic to recognize it
as on schema v1.
A database coming from Parrot v1 needs this before Alembic can execute the
migrations on it.
"""

import sqlmodel as sm
from parrot import config
from parrot.config import logger


V1_REVISION = "fe3138aef0bd"


def main() -> None:
	class alembic_version(sm.SQLModel, table=True):
		version_num: str = sm.Field(primary_key=True)

	engine = sm.create_engine(config.db_url)
	sm.SQLModel.metadata.create_all(engine)
	session = sm.Session(engine)
	session.add(alembic_version(version_num=V1_REVISION))
	logger.info(f"Version marker added: {V1_REVISION}")
	session.commit()


if __name__ == "__main__":
	main()
