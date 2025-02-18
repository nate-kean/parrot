from typing import cast

import discord
from discord.ext import commands, tasks
from parrot.bot import Parrot
from parrot.utils import is_learnable


class Autoforget(commands.Cog):
	"""Database hygiene

	Event listeners and timers to delete stuff from the database that's not on
	Discord anymore.
	"""

	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_raw_member_remove(
		self, payload: discord.RawMemberRemoveEvent
	) -> None:
		"""
		Start a "timer" on the messages and other information of a member
		associated with a guild upon the member leaving. After a certain
		retention period, the data will be deleted on the next tick of the
		"prune expired memberships" task.
		"""
		self.bot.crud.member.mark_gone(cast(discord.Member, payload.user))

	@tasks.loop(hours=24)
	async def prune_expired_memberships(self) -> None:
		"""
		Every so often, prune any ended memberships that are past their
		retention period.
		Also deletes the associated user if this deletes their last
		membership(s).
		"""
		await self.bot.crud.guild.prune_expired_memberships()

	@commands.Cog.listener()
	async def on_member_join(self, member: discord.Member) -> None:
		"""
		A member's data will not be deleted if they rejoin before the end of the
		retention period.
		"""
		# TODO: mention this in the privacy policy
		self.bot.crud.member.mark_present(member)

	@commands.Cog.listener()
	async def on_guild_remove(self, guild: discord.Guild) -> None:
		"""
		If a guild is deleted, forget all the data associated with it.
		E.g., messages, DB membership rows, etc.
		"""
		self.bot.crud.guild.delete(guild)

	@commands.Cog.listener()
	async def on_guild_channel_delete(
		self, channel: discord.abc.GuildChannel
	) -> None:
		"""If a channel is deleted, forget any messages associated with it."""
		if not is_learnable(channel):
			return
		self.bot.crud.channel.delete(channel)


async def setup(bot: Parrot) -> None:
	await bot.add_cog(Autoforget(bot))
