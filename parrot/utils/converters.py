import random
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

import discord
from discord.errors import NotFound
from discord.ext import commands

from parrot import config
from parrot.bot import Parrot
from parrot.utils import regex
from parrot.utils.exceptions import (
	ChannelTypeError,
	UserNotFoundError,
)
from parrot.utils.types import Snowflake


type Check = Callable[
	[commands.Context[Parrot], str | None], Awaitable[discord.Member | None]
]


__all__ = ["Userlike", "Memberlike"]


# HACK: to make the type checker accept my commands.Converters as the type they
# convert to.
# For arguments annotated as a converters.Converter, discord.py actually gives
# you a value whose type is the return type of that converter's .convert().
# So, e.g., if you type annotate an argument as a Userlike, it will actually
# come in as a discord.Member.
if TYPE_CHECKING:
	type Userlike = _Userlike | discord.Member
	type Memberlike = _Memberlike | discord.Member

	class ParrotConverter(commands.Converter, discord.Member): ...
else:
	# strip off the disguise at runtime
	# or rather... leave nothing but the disguise?
	type Userlike = _Userlike
	type Memberlike = _Memberlike

	class ParrotConverter(commands.Converter): ...


class BaseUserlike(ParrotConverter):
	async def convert(
		self,
		ctx: commands.Context,
		argument: str | None,
	) -> discord.Member:
		for check in self._checks:
			result = await check(ctx, argument)
			if result is not None:
				return result
		raise UserNotFoundError.Username(argument or "<None>")

	@staticmethod
	async def _id(
		ctx: commands.Context,
		text: str | None,
	) -> discord.Member | None:
		if text is None:
			return cast(discord.Member, ctx.author)

		if ctx.guild is None:
			return None

		# Strip the mention down to an ID.
		try:
			member_id = Snowflake(regex.snowflake.sub("", text.lower()))
		except ValueError:
			return None

		# Fetch the member by ID.
		try:
			return await ctx.guild.fetch_member(member_id)
		except NotFound:
			return None

	_checks: list[Check] = [_id]


class _Userlike(BaseUserlike):
	"""
	A string that can resolve to a Member.
	Works with:
		- Mentions, like <@394750023975409309> and <@!394750023975409309>
		- User IDs, like 394750023975409309
		- The string "me" or "myself", which resolves to the context's author
	"""

	@staticmethod
	async def _me(
		ctx: commands.Context,
		text: str | None,
	) -> discord.Member | None:
		if text in ("me", "myself"):
			# guaranteed Member and not User because that is already asserted
			# in BaseUserlike.convert()
			return cast(discord.Member, ctx.author)

	_checks = BaseUserlike._checks + [_me]


class _Memberlike(_Userlike):
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

	@staticmethod
	async def _you(
		ctx: commands.Context[Parrot], text: str | None
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

	@staticmethod
	async def _someone(
		ctx: commands.Context[Parrot], text: str | None
	) -> discord.Member | None:
		"""Choose a random registered user in this channel."""
		if text not in ("someone", "somebody", "anyone", "anybody"):
			return
		if ctx.guild is None:
			raise ChannelTypeError(
				f'"{config.command_prefix}imitate someone" is only available '
				"in regular server text channels."
			)
		registered_member_ids_here = (
			await ctx.bot.crud.guild.get_registered_member_ids(ctx.guild)
		)
		if len(registered_member_ids_here) == 0:
			raise UserNotFoundError(
				"Nobody is registered with Parrot in this server."
			)
		member_id = random.choice(registered_member_ids_here)
		return await ctx.guild.fetch_member(member_id)

	_checks = _Userlike._checks + [_you, _someone]
