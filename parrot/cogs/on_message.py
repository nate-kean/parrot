import random

import discord
from discord.ext import commands

from parrot import config, utils
from parrot.bot import Parrot
from parrot.utils import cast_not_none, is_learnable, weasel
from parrot.utils.exceptions import NotRegistered


class MessageHandler(commands.Cog):
	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_message(self, message: discord.Message) -> None:
		"""
		Handle receiving messages.
		Monitors messages of registered users.
		"""
		if message.author.id == cast_not_none(self.bot.user).id:
			return

		if is_learnable(message.channel):
			try:
				self.bot.crud.message.record(message)
				# TODO: implement in a way that doesn't run for _every_ collected
				# message. Every hundred from one member? Every certain proportion
				# of the size of a member's corpus?
				# guaranteed to be Member because message is guaranteed above to be
				# in a guild
				# member = cast(discord.Member, message.author)
				# corpus_update = (message.content for message in recorded)
				# asyncio.create_task(
				# 	self.bot.markov_models.update(member, corpus_update)
				# )
			except NotRegistered:
				pass

		# I am a mature person making a competent Discord bot.
		if message.content == "ayy" and config.ayy_lmao:
			await message.channel.send("lmao")

		# Randomly decide to wawa a message.
		if (
			random.random() < config.random_wawa_chance
			and self.bot.crud.user.wants_wawa(message.author)
		):
			text = utils.find_text(message)
			if text is not None:
				await message.reply(await weasel.wawa(text))


async def setup(bot: Parrot) -> None:
	await bot.add_cog(MessageHandler(bot))
