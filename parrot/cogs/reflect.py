import discord
from discord.ext import commands

from parrot.bot import Parrot
from parrot.config import logger
from parrot.utils import is_learnable


class Reflect(commands.Cog):
	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_raw_message_delete(
		self, event: discord.RawMessageDeleteEvent
	) -> None:
		"""
		Update the database when a message is deleted.
		Must use the raw event because the regular version doesn't work for
		messages that don't happen to be in its cache.
		"""
		deleted = self.bot.crud.message.delete(event.message_id)
		if deleted is None:
			return
		# Invalidate cached model
		try:
			del self.bot.markov_models.cache[
				(deleted.author_id, deleted.guild_id)
			]
		except KeyError:
			pass
		logger.info(
			f"Forgot message with ID {event.message_id} because it was deleted "
			"from Discord."
		)

	# Update the database when a message is edited.
	# Must use the raw event because the regular version doesn't work for
	# messages that don't happen to be in its cache.
	@commands.Cog.listener()
	async def on_raw_message_edit(
		self,
		event: discord.RawMessageUpdateEvent,
	) -> None:
		if not is_learnable(event.message.channel):
			return
		updated = self.bot.crud.message.update(event.message)
		if updated is None:
			return
		# Invalidate cached model
		try:
			del self.bot.markov_models.cache[
				(
					event.message.author.id,
					event.message.channel.guild.id,
				)
			]
		except KeyError:
			pass
		logger.info(
			f"Updated message with ID {event.message_id} with content from "
			"edited message."
		)


async def setup(bot: Parrot) -> None:
	await bot.add_cog(Reflect(bot))
