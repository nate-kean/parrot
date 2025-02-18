import logging

import discord
from discord.ext import commands

from parrot.bot import Parrot
from parrot.utils import cast_not_none, is_learnable


class RawMessageEditEventHandler(commands.Cog):
	def __init__(self, bot: Parrot):
		self.bot = bot

	# Update the database when a message is edited.
	# Must use the raw event because the regular version doesn't work for
	# messages that don't happen to be in its cache.
	@commands.Cog.listener()
	async def on_raw_message_edit(
		self, event: discord.RawMessageUpdateEvent
	) -> None:
		if "content" not in event.data:
			logging.error(f"Unexpected message edit event format: {event.data}")
			return
		channel = await self.bot.fetch_channel(event.channel_id)
		if not is_learnable(channel):
			return
		message = await channel.fetch_message(event.message_id)
		recorded = self.bot.crud.message.record(message)
		if len(recorded) > 0:
			# Invalidate cached model
			try:
				del self.bot.markov_models.cache[
					# message.channel.guild not none: channel is guaranteed to
					# be a guild channel
					(message.author.id, cast_not_none(message.channel.guild).id)
				]
			except KeyError:
				pass


async def setup(bot: Parrot) -> None:
	await bot.add_cog(RawMessageEditEventHandler(bot))
