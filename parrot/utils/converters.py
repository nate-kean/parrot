import random
from collections.abc import Awaitable, Callable
from typing import cast

import discord
from discord.errors import NotFound
from discord.ext import commands

from parrot import config
from parrot.bot import Parrot
from parrot.utils import regex
from parrot.utils.exceptions import (
	ChannelTypeError,
	FeatureDisabledError,
	UserNotFoundError,
)


type Check = Callable[
	[commands.Context, str | None], Awaitable[discord.Member | None]
]


class BaseUserlike(commands.Converter):
	def __init__(self):
		self._checks: list[Check] = []

	async def convert(
		self, ctx: commands.Context, argument: str
	) -> discord.Member:
		argument = argument.lower()

		for check in self._checks:
			result = await check(ctx, argument)
			if result is not None:
				return result

		# If this is not a guild, it must be a DM channel, and therefore the
		# only person you can imitate is yourself.
		if ctx.guild is None:
			raise UserNotFoundError.Username(argument)

		# Strip the mention down to an ID.
		try:
			member_id = int(regex.snowflake.sub("", argument))
		except ValueError:
			raise UserNotFoundError.Username(argument)

		# Fetch the member by ID.
		try:
			return await ctx.guild.fetch_member(member_id)
		except NotFound:
			raise UserNotFoundError.Username(argument)


class Userlike(BaseUserlike):
	"""
	A string that can resolve to a Member.
	Works with:
		- Mentions, like <@394750023975409309> and <@!394750023975409309>
		- User IDs, like 394750023975409309
		- The string "me" or "myself", which resolves to the context's author
	"""

	def __init__(self):
		super().__init__()
		self._checks.append(self._me)

	async def _me(
		self, ctx: commands.Context, text: str | None
	) -> discord.Member | None:
		if text in ("me", "myself"):
			# guaranteed Member and not User because that is already asserted
			# in BaseUserlike.convert()
			return cast(discord.Member, ctx.author)


class Memberlike(Userlike):
	"""
	A string that can resolve to a Member -- plus novelty options!
	Works with:
		- Everything Userlike does
		- The string "you", "yourself", or "previous" which resolves to the last
			person who spoke in the channel
		- "someone", "anyone", whatever, the rest of them, read the code, that
			randomly picks a valid user in the provided Context. Requires
			Members Intent on the Discord developer dashboard and must be
			enabled in Parrot's config.
	"""

	def __init__(self):
		super().__init__()
		self._checks.append(self._you)
		self._checks.append(self._someone)

	async def _you(
		self, ctx: commands.Context, text: str | None
	) -> discord.Member | None:
		"""Get the author of the last message send in the channel who isn't
		Parrot or the person who sent this command."""
		if text not in ("you", "yourself", "previous"):
			return
		if ctx.guild is None:
			raise ChannelTypeError(
				f'"{config.command_prefix}imitate you" is only available '
				"in regular server text channels."
			)
		async for message in ctx.channel.history(before=ctx.message, limit=50):
			if (
				message.author not in (ctx.bot.user, ctx.author)
				and message.webhook_id is None
			):
				# Authors of messages from a history iterator are always
				# users, not members, so we have to fetch the member
				# separately.
				return await ctx.guild.fetch_member(message.author.id)

	async def _someone(
		self, ctx: commands.Context, text: str | None
	) -> discord.Member | None:
		"""Choose a random registered user in this channel."""
		if text not in ("someone", "somebody", "anyone", "anybody"):
			return
		if not config.enable_imitate_someone:
			raise FeatureDisabledError(
				f'The "{config.command_prefix}imitate someone" feature is '
				"disabled."
			)
		if ctx.guild is None:
			raise ChannelTypeError(
				f'"{config.command_prefix}imitate someone" is only available '
				"in regular server text channels."
			)
		registered_member_ids_here = await cast(
			Parrot, ctx.bot
		).crud.guild.get_registered_member_ids(ctx.guild)
		if len(registered_member_ids_here) == 0:
			raise UserNotFoundError(
				"Nobody is registered with Parrot in this server."
			)
		member_id = random.choice(registered_member_ids_here)
		return await ctx.guild.fetch_member(member_id)
