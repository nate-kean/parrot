"""make user profiles separate per guild

Forgets users' old is_registered value; no longer valid because the old value
was global while the new value is guild-specific.
This will unregister everyone, so you'll have to tell them they have to register
again.

Scrapes Discord to populate this table based on what guilds the bot is in and
what users exist in the database being migrated.

Revision ID: 79a4371fbc92
Revises: b6fa8b3c752a
Create Date: 2025-01-21 14:43:16.104103

"""

import logging
from collections.abc import Sequence

import discord
import sqlalchemy as sa
import sqlmodel as sm
from parrot import config
from parrot.alembic.common import cleanup_models
from parrot.utils.types import Snowflake
from tqdm import tqdm

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "79a4371fbc92"
down_revision: str | None = "b6fa8b3c752a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	# Imported here so the models inside aren't added to the global namespace
	from parrot.alembic.models import r79a4371fbc92

	conn = op.get_bind()
	r79a4371fbc92.Membership.__table__.create(conn, checkfirst=True)
	op.drop_column("user", "is_registered")

	global target_metadata
	target_metadata = sm.SQLModel.metadata
	session = sm.Session(bind=conn)

	intents = discord.Intents.default()
	intents.members = True
	client = discord.Client(intents=intents)

	db_users = session.exec(sm.select(r79a4371fbc92.User)).all()

	@client.event
	async def on_ready() -> None:
		logging.info("Scraping Discord to populate guild IDs...")
		members_found: set[Snowflake] = set()
		for guild in tqdm(client.guilds, desc="Guilds processed"):
			async for member in guild.fetch_members(limit=None):
				for db_user in db_users:
					if db_user.id != member.id:
						continue
					# logging.debug(
					# 	f"User {db_user.id} is a member of guild {guild.id}"
					# )
					db_guild = session.get(
						r79a4371fbc92.Guild, guild.id
					) or r79a4371fbc92.Guild(id=guild.id)
					session.add(
						r79a4371fbc92.Membership(
							user=db_user,
							guild=db_guild,
						)
					)
					members_found.add(db_user.id)
					break
		for db_user in db_users:
			if db_user.id not in members_found:
				logging.warning(f"No guilds found for user {db_user.id}")
		session.commit()
		await client.close()

	if len(db_users) != 0:
		client.run(config.discord_bot_token)
	cleanup_models(r79a4371fbc92)


def downgrade() -> None:
	op.drop_table("membership")
	op.add_column(
		"user",
		sa.Column(
			"is_registered",
			sa.Boolean(),
			server_default="0",
			nullable=False,
		),
	)
