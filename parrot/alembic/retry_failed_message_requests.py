import discord
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


def main() -> None:
	from parrot.alembic.models import r7d0ffe4179c6
	from parrot.alembic.models.r7d0ffe4179c6 import ErrorCode

	engine = sm.create_engine(config.db_url)
	session = sm.Session(engine)

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
		logger.info("Scraping Discord retry failed message requests...")
		try:
			channels = await process_channels()
			processor.retrying = True
			await processor.process_messages(channels)
		except Exception as exc:
			logger.error(exc)
		session.commit()
		await client.close()

	if len(db_channels) != 0:
		client.run(config.discord_bot_token)

	cleanup_models(r7d0ffe4179c6)


if __name__ == "__main__":
	main()
