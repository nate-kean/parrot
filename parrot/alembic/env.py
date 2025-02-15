import functools
import logging.config
import sys

from parrot import config as parrot_cfg
from parrot.db import NAMING_CONVENTION
from sqlalchemy import MetaData, engine_from_config, pool

from alembic import context, op


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
alembic_cfg = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if alembic_cfg.config_file_name is not None:
	logging.config.fileConfig(alembic_cfg.config_file_name)

# Use current SQLModel MetaData for autogenerating
if "--autogenerate" in sys.argv:
	import sqlmodel as sm
	from parrot.db import models  # noqa: F401

	target_metadata = sm.SQLModel.metadata
	target_metadata.naming_convention = NAMING_CONVENTION
else:
	target_metadata = MetaData(naming_convention=NAMING_CONVENTION)

# SQLAlchemy headache #15:
# Curry naming_convention into batch_alter_table because it doesn't use it by
# default
op.batch_alter_table = functools.partial(
	op.batch_alter_table, naming_convention=NAMING_CONVENTION
)


def run_migrations_offline() -> None:
	"""Run migrations in 'offline' mode.

	This configures the context with just a URL and not an Engine, though an
	Engine is acceptable here as well. By skipping the Engine creation we don't
	even need a DBAPI to be available.

	Calls to context.execute() here emit the given string to the script output.
	"""
	context.configure(
		url=parrot_cfg.db_url,
		target_metadata=target_metadata,
		literal_binds=True,
		dialect_opts={"paramstyle": "named"},
	)

	with context.begin_transaction():
		context.run_migrations()


def run_migrations_online() -> None:
	"""Run migrations in 'online' mode.

	In this scenario we need to create an Engine and associate a connection with
	the context.
	"""
	PREFIX = "sqlalchemy."
	config = alembic_cfg.get_section(alembic_cfg.config_ini_section, {})
	config[PREFIX + "url"] = parrot_cfg.db_url
	connectable = engine_from_config(
		config,
		prefix=PREFIX,
		poolclass=pool.NullPool,
	)

	with connectable.connect() as connection:
		context.configure(
			connection=connection, target_metadata=target_metadata
		)
		with context.begin_transaction():
			context.run_migrations()


if context.is_offline_mode():
	run_migrations_offline()
else:
	run_migrations_online()
