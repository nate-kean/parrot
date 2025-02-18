import logging

from discord.ext import commands

from parrot.bot import Parrot
from parrot.utils import tag


class ReadyEventHandler(commands.Cog):
	initialized: bool

	def __init__(self, bot: Parrot):
		self.bot = bot
		self.initialized = False

	# Update the database when a message is deleted.
	# Must use the raw event because the main event doesn't catches edit events
	# for messages that happen to be in its cache.
	@commands.Cog.listener()
	async def on_ready(self) -> None:
		"""on_ready fires when the bot (re)gains connection."""
		if self.bot.user is None:
			logging.error("Invalid `on_ready` state: `self.user` is None")
			return
		if self.initialized:
			logging.info("Logged back in.")
			return
		logging.info(f"Logged in as {tag(self.bot.user)}")
		self.initialized = True


async def setup(bot: Parrot) -> None:
	await bot.add_cog(ReadyEventHandler(bot))
