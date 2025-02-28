import datetime as dt
from collections.abc import Sequence
from typing import cast

import discord
import sqlmodel as sm

import parrot.db.models as p
from parrot import config
from parrot.utils.trace import trace
from parrot.utils.types import Snowflake

from .types import SubCRUD


@trace
class CRUDGuild(SubCRUD):
	def get_learning_channel_ids(
		self,
		guild: discord.Guild,
	) -> Sequence[Snowflake]:
		statement = sm.select(p.Channel.id).where(
			p.Channel.guild_id == guild.id,
			p.Channel.guild_id == True,
		)
		return self.session.exec(statement).all()

	def get_prefix(self, guild: discord.Guild) -> str:
		statement = sm.select(p.Guild.imitation_prefix).where(
			p.Guild.id == guild.id
		)
		prefix = self.session.exec(statement).first()
		return (
			prefix
			if prefix is not None
			else p.GuildMeta.default_imitation_prefix
		)

	def set_prefix(self, guild: discord.Guild, new_prefix: str) -> None:
		db_guild = self.session.get(p.Guild, guild.id) or p.Guild(
			id=guild.id, imitation_prefix=new_prefix
		)
		db_guild.imitation_prefix = new_prefix
		self.session.add(db_guild)

	def get_suffix(self, guild: discord.Guild) -> str:
		statement = sm.select(p.Guild.imitation_suffix).where(
			p.Guild.id == guild.id
		)
		suffix = self.session.exec(statement).first()
		return (
			suffix
			if suffix is not None
			else p.GuildMeta.default_imitation_suffix
		)

	def set_suffix(self, guild: discord.Guild, new_suffix: str) -> None:
		db_guild = self.session.get(p.Guild, guild.id) or p.Guild(
			id=guild.id, imitation_suffix=new_suffix
		)
		db_guild.imitation_suffix = new_suffix
		self.session.add(db_guild)

	async def get_registered_member_ids(
		self,
		guild: discord.Guild,
	) -> Sequence[Snowflake]:
		return cast(
			Sequence[Snowflake],
			self.session.exec(
				sm.select(p.Membership.user_id).where(
					p.Membership.guild_id == guild.id,
					p.Membership.is_registered == True,
				)
			).all()
			or [],
		)

	async def prune_expired_memberships(self) -> None:
		now = discord.utils.time_snowflake(dt.datetime.now())
		statement = sm.select(p.Membership).where(
			sm.col(p.Membership.ended_since).is_not(None),
			(
				now - sm.col(p.Membership.ended_since)
				> config.message_retention_period_seconds
			),
		)
		expired_memberships = self.session.exec(statement)

		for membership in expired_memberships:
			try:
				guild = self.bot.get_guild(membership.guild.id)
				if guild is None:
					# TODO: what do here
					# Also delete this db guild?
					raise Exception()
				await guild.fetch_member(membership.user.id)
			except discord.NotFound:
				# User is truly not in this guild anymore
				await self.bot.crud.member.raw_delete_membership(membership)
			else:
				# User is actually still in this guild after all
				membership.ended_since = None
				self.session.add(membership)

	def delete(self, guild: discord.Guild) -> bool:
		db_guild = self.session.get(p.Guild, guild.id)
		if db_guild is None:
			return False
		self.session.delete(db_guild)
		return True
