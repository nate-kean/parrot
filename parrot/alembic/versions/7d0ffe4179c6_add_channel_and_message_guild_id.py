"""add channel and message guild id

Adds key guild_id to tables channel and message,
Adds indices to message.guild_id + author_id.

Scrapes these guild IDs from Discord.

Revision ID: 7d0ffe4179c6
Revises: 2e2045b63d7a
Create Date: 2025-01-21 14:40:18.601522

"""

from collections.abc import Sequence

import discord
import sqlalchemy as sa
import sqlmodel as sm
from parrot import config
from parrot.alembic.common import (
	AddChannelAndMessageGuildIDFactory,
	cleanup_models,
)
from parrot.config import logger
from parrot.utils import is_learnable
from parrot.utils.types import LearnableChannel
from tqdm import tqdm

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7d0ffe4179c6"
down_revision: str | None = "2e2045b63d7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	from parrot.alembic.models import r7d0ffe4179c6
	from parrot.alembic.models.r7d0ffe4179c6 import ErrorCode

	with op.batch_alter_table("channel") as bop:
		# https://stackoverflow.com/a/6710280
		# sqlite oversight: You have to add the column with a default value then
		# remove the default value after for it to work
		bop.add_column(
			sa.Column(
				"guild_id",
				sa.BigInteger(),
				nullable=False,
				server_default=str(ErrorCode.UNPROCESSED.value),
			)
		)
	with op.batch_alter_table("channel") as bop:
		bop.alter_column("guild_id", server_default=None)
		bop.create_foreign_key(None, "guild", ["guild_id"], ["id"])

	with op.batch_alter_table("message") as bop:
		bop.add_column(
			sa.Column(
				"guild_id",
				sa.BigInteger(),
				nullable=False,
				# Temporary default
				server_default=str(ErrorCode.UNPROCESSED.value),
			)
		)
		# Developing this migration has made me realize Parrot sorely needs
		# channel ID too to be able to remotely efficiently get information from
		# messages. With this plus guild ID, we won't have to do this again.
		bop.add_column(
			sa.Column(
				"channel_id",
				sa.BigInteger(),
				nullable=False,
				# Temporary default
				server_default=str(ErrorCode.UNPROCESSED.value),
			)
		)
		bop.create_foreign_key(None, "guild", ["guild_id"], ["id"])
		bop.create_index(
			op.f("ix_guild_id_author_id"), ["guild_id", "author_id"]
		)

	global target_metadata
	target_metadata = sm.SQLModel.metadata
	session = sm.Session(bind=op.get_bind())

	client = discord.Client(intents=discord.Intents.default())

	db_channels = session.exec(
		sm.select(r7d0ffe4179c6.Channel).where(
			# TODO: works without the == True?
			r7d0ffe4179c6.Channel.can_learn_here == True  # noqa: E712
		)
	).all()

	async def process_channels() -> list[LearnableChannel]:
		channels: list[LearnableChannel] = []
		for db_channel in tqdm(db_channels, desc="Channels processed"):
			try:
				channel = await client.fetch_channel(db_channel.id)
			except Exception as exc:
				logger.warning(
					f"Failed to fetch channel {db_channel.id}: {exc}"
				)
				db_channel.guild_id = ErrorCode.REQUEST_FAILED.value
				session.add(db_channel)
				continue
			if not is_learnable(channel):
				logger.warning(
					f"Invalid channel type: {db_channel.id} is {type(channel)}"
				)
				db_channel.guild_id = ErrorCode.INVALID_TYPE.value
				session.add(db_channel)
				continue
			logger.debug(
				f"Channel {db_channel.id} in guild {db_channel.guild_id}"
			)
			db_channel.guild_id = channel.guild.id
			channels.append(channel)
			session.add(db_channel)
		return channels

	processor = AddChannelAndMessageGuildIDFactory(r7d0ffe4179c6, session)

	@client.event
	async def on_ready() -> None:
		logger.info("Scraping Discord to populate guild IDs...")
		try:
			channels = await process_channels()
			await processor.process_messages(channels)
			processor.retrying = True
			await processor.process_messages(channels)
		except Exception as exc:
			logger.error(exc)
		session.commit()
		await client.close()

	if len(db_channels) != 0:
		client.run(config.discord_bot_token)

	# Remove the temporary default value settings from message.guild_id and
	# channel_id now that they should have all been populated
	with op.batch_alter_table("message") as bop:
		bop.alter_column("guild_id", server_default=None)
		bop.alter_column("channel_id", server_default=None)

	cleanup_models(r7d0ffe4179c6)


def downgrade() -> None:
	try:
		with op.batch_alter_table("channel") as bop:
			bop.drop_constraint(
				op.f("fk_channel_guild_id_guild"), type_="foreignkey"
			)
			bop.drop_index(op.f("ix_guild_id_author_id"))
	except ValueError as exc:
		logger.warning(exc)
	with op.batch_alter_table("channel") as bop:
		bop.drop_column("guild_id")

	with op.batch_alter_table("message") as bop:
		bop.drop_constraint(
			op.f("fk_message_guild_id_guild"), type_="foreignkey"
		)
		bop.drop_column("guild_id")
