import asyncio
import logging
from collections.abc import Callable, Coroutine
from enum import Enum, auto
from typing import Any, cast

import discord
from discord.ext import commands

from parrot import config, utils
from parrot.bot import Parrot
from parrot.utils import (
	ParrotEmbed,
	cast_not_none,
	discord_caps,
	trace,
	weasel,
)
from parrot.utils.converters import FuzzyMemberlike
from parrot.utils.exceptions import TextNotFoundError


class Text(commands.Cog):
	class ImitateMode(Enum):
		"""
		I have plans that I cannot share with you right now because the haters
		will sabotage me
		"""

		STANDARD = auto()
		INTIMIDATE = auto()

	def __init__(self, bot: Parrot):
		self.bot = bot

	@staticmethod
	async def _modify_text(
		ctx: commands.Context,
		*,
		input_text: str = "",
		modifier: Callable[[str], Coroutine[Any, Any, str]],
	) -> None:
		"""Generic function for commands that just modify text.

		Tries really hard to find text to work with then processes it with your
		callback.
		"""
		# If the author is replying to a message, add that message's text
		# to anything the author might have also said after the command.
		if ctx.message.reference and ctx.message.reference.message_id:
			reference_message = await ctx.channel.fetch_message(
				ctx.message.reference.message_id
			)
			input_text += utils.find_text(reference_message)
			if len(input_text) == 0:
				# Author didn't include any text of their own, and the message
				# they're trying to get text from doesn't have any text.
				raise TextNotFoundError(
					"😕 That message doesn't have any text!"
				)

		# If there is no text and no reference message, try to get the text from
		# the last (usable) message sent in this channel.
		elif len(input_text) == 0:
			history = ctx.channel.history(limit=10, before=ctx.message)
			while len(input_text) == 0:
				try:
					input_text += utils.find_text(await history.__anext__())
				except StopAsyncIteration:
					raise TextNotFoundError(
						"😕 Couldn't find a gibberizeable message"
					)

		try:
			async with asyncio.timeout(config.modify_text_timeout_seconds):
				# TODO: timeout actually cancels this, right?
				text = await modifier(input_text)
		except TimeoutError:
			text = ""
		await ctx.send(text[:2000])

	async def _imitate_impl(
		self,
		ctx: commands.Context,
		member: discord.Member,
		mode: ImitateMode = ImitateMode.STANDARD,
	) -> None:
		# Parrot can't imitate itself!
		if member.id == cast_not_none(self.bot.user).id:
			# Send the funny XOK message instead, that'll show 'em.
			embed = ParrotEmbed(
				title="Error",
				color=ParrotEmbed.Color.RED,
			)
			embed.set_thumbnail(
				url="https://i.imgur.com/zREuVTW.png"
			)  # Windows 7 close button
			embed.set_image(url="https://i.imgur.com/JAQ7pjz.png")  # Xok
			sent_message = await ctx.send(embed=embed)
			await sent_message.add_reaction("🆗")
			return

		# Fetch this user's model.
		model = await self.bot.markov_models.fetch(member)
		sentence = model.make_short_sentence(500) or "Error"

		prefix = (
			self.bot.crud.guild.get_prefix(ctx.guild)
			if ctx.guild is not None
			else ""
		)
		suffix = (
			self.bot.crud.guild.get_suffix(ctx.guild)
			if ctx.guild is not None
			else ""
		)
		name = f"{prefix}{member.display_name}{suffix}"

		match mode:
			case Text.ImitateMode.INTIMIDATE:
				sentence = "**" + discord_caps(sentence) + "**"
				name = name.upper()

		# Prepare to send this sentence through a webhook.
		# Discord lets you change the name and avatar of a webhook account much
		# faster than those of a bot/user account, which is crucial for
		# being able to imitate lots of users quickly.
		try:
			avatar_url = await self.bot.antiavatars.fetch(member)
		except Exception as error:
			logging.error(utils.error2traceback(error))
			avatar_url = member.display_avatar.url

		webhook = (
			await self.bot.webhooks.fetch(ctx.channel)
			if isinstance(ctx.channel, discord.TextChannel)
			else None
		)
		if webhook is None:
			# Fall back to using an embed if Parrot couldn't get a webhook.
			await ctx.send(
				embed=ParrotEmbed(
					description=sentence,
				).set_author(name=name, icon_url=avatar_url)
			)
			return
		# Send the sentence through the webhook.
		await webhook.send(
			content=sentence,
			username=name,
			avatar_url=avatar_url,
			allowed_mentions=discord.AllowedMentions.none(),
		)

	@commands.command(aliases=["be"], brief="Imitate someone.")
	@commands.cooldown(2, 2, commands.BucketType.user)
	@trace
	async def imitate(
		self, ctx: commands.Context, user: FuzzyMemberlike
	) -> None:
		"""Imitate someone."""
		logging.info(f"Imitating {user}")
		await self._imitate_impl(ctx, cast(discord.Member, user))

	@commands.command(brief="IMITATE SOMEONE.")
	@commands.cooldown(2, 2, commands.BucketType.user)
	@trace
	async def intimidate(
		self, ctx: commands.Context, user: FuzzyMemberlike
	) -> None:
		"""IMITATE SOMEONE."""
		logging.info(f"Intimidating {user}")
		await self._imitate_impl(
			ctx, cast(discord.Member, user), mode=Text.ImitateMode.INTIMIDATE
		)

	@commands.command(
		aliases=["gibberize"],
		brief="Gibberize a sentence.",
	)
	@commands.cooldown(2, 2, commands.BucketType.user)
	@trace
	async def gibberish(self, ctx: commands.Context, *, text: str = "") -> None:
		"""Turn text into gibberish."""
		await Text._modify_text(ctx, input_text=text, modifier=weasel.gibberish)

	@commands.command(brief="Devolve a sentence.")
	@commands.cooldown(2, 2, commands.BucketType.user)
	async def devolve(self, ctx: commands.Context, *, text: str = "") -> None:
		"""Devolve text back toward primordial ooze."""
		await Text._modify_text(ctx, input_text=text, modifier=weasel.devolve)

	@commands.command(brief="Wawa a sentence.", aliases=["stowaway"])
	@commands.cooldown(2, 2, commands.BucketType.user)
	async def wawa(self, ctx: commands.Context, *, text: str = "") -> None:
		"""See what the Stowaway says
		https://corru.wiki/wiki/Stowaway"""
		await Text._modify_text(ctx, input_text=text, modifier=weasel.wawa)


async def setup(bot: Parrot) -> None:
	await bot.add_cog(Text(bot))
