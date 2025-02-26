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
	is_speakable,
	weasel,
)
from parrot.utils.converters import Memberlike
from parrot.utils.exceptions import TextNotFoundError
from parrot.utils.trace import trace


@trace
class Text(commands.Cog):
	class ImitateMode(Enum):
		"""
		I have plans that I cannot share with you right now because the haters
		will sabotage me
		"""

		STANDARD = auto()
		INTIMIDATE = auto()

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
			async for message in history:
				input_text += utils.find_text(message)
				if len(input_text) > 0:
					break
			else:  # input_text still empty
				raise TextNotFoundError(
					"😕 Couldn't find a gibberizeable message"
				)

		try:
			async with asyncio.timeout(config.modify_text_timeout_seconds):
				# TODO: timeout actually cancels this, right?
				text = await modifier(input_text)
		except TimeoutError:
			text = "Error"
		await ctx.send(text[:2000])

	@staticmethod
	async def _imitate_impl(
		ctx: commands.Context[Parrot],
		*,
		member: discord.Member,
		mode: ImitateMode = ImitateMode.STANDARD,
	) -> None:
		# Parrot can't imitate itself!
		if member.id == cast_not_none(ctx.bot.user).id:
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
		model = await ctx.bot.markov_models.fetch(member)
		sentence = model.make_short_sentence(500) or "Error"

		prefix = (
			ctx.bot.crud.guild.get_prefix(ctx.guild)
			if ctx.guild is not None
			else ""
		)
		suffix = (
			ctx.bot.crud.guild.get_suffix(ctx.guild)
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
			avatar_url = await ctx.bot.antiavatars.fetch(member)
		except Exception as error:
			logging.error(utils.error2traceback(error))
			avatar_url = member.display_avatar.url

		webhook = (
			await ctx.bot.webhooks.fetch(ctx)
			if is_speakable(ctx.channel)
			else None
		)
		if webhook is None:
			# Fall back to using an embed if Parrot couldn't get a webhook.
			embed = ParrotEmbed(
				description=sentence,
			).set_author(name=name, icon_url=avatar_url)
			await ctx.send(embed=embed)
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
	async def imitate(self, ctx: commands.Context, user: Memberlike) -> None:
		"""Imitate someone."""
		logging.info(f"Imitating {user}")
		await self._imitate_impl(
			ctx,
			member=cast(discord.Member, user),
			mode=Text.ImitateMode.STANDARD,
		)

	@commands.command(brief="IMITATE SOMEONE.")
	@commands.cooldown(2, 2, commands.BucketType.user)
	async def intimidate(self, ctx: commands.Context, user: Memberlike) -> None:
		"""IMITATE SOMEONE."""
		logging.info(f"Intimidating {user}")
		await self._imitate_impl(
			ctx,
			member=cast(discord.Member, user),
			mode=Text.ImitateMode.INTIMIDATE,
		)

	@commands.command(
		aliases=["gibberize"],
		brief="Gibberize a sentence.",
	)
	@commands.cooldown(2, 2, commands.BucketType.user)
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
	await bot.add_cog(Text())
