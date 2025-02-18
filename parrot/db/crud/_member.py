import datetime as dt
from collections.abc import Sequence

import discord
import sqlmodel as sm

import parrot.db.models as p
from parrot.utils.exceptions import NotRegisteredError

from .types import SubCRUD


class CRUDMember(SubCRUD):
	"""
	Actions on users in the context of a guild.
	Takes Discord Member objects and acts on database Memberships.
	"""

	def _get(self, member: discord.Member) -> p.Membership | None:
		statement = sm.select(p.Membership).where(
			p.Membership.user_id == member.id,
			p.Membership.guild_id == member.guild.id,
		)
		return self.bot.db_session.exec(statement).first()

	def set_registered(self, member: discord.Member, value: bool) -> None:
		membership = self._get(member) or p.Membership(
			user=self.bot.db_session.get(p.User, member.id)
			or p.User(id=member.id),
			guild=self.bot.db_session.get(p.Guild, member.guild.id)
			or p.Guild(id=member.guild.id),
		)
		membership.is_registered = value
		self.bot.db_session.add(membership)

	def assert_registered(self, member: discord.Member) -> None:
		if not self.is_registered(member):
			raise NotRegisteredError.User(member)

	def is_registered(self, member: discord.Member) -> bool:
		if member.bot:  # Bots are always counted as registered
			return True
		membership = self._get(member)
		return membership is not None and membership.is_registered

	def get_messages_content(self, member: discord.Member) -> Sequence[str]:
		"""
		Get the text content of every message this user has said in this guild.
		"""
		self.assert_registered(member)
		statement = sm.select(p.Message.content).where(
			p.Message.author_id == member.id,
			p.Message.guild_id == member.guild.id,
		)
		return self.bot.db_session.exec(statement).all()

	def get_antiavatar(self, member: discord.Member) -> p.Antiavatar | None:
		self.assert_registered(member)
		statement = sm.select(p.Antiavatar).where(
			p.Antiavatar.user_id == member.id,
			p.Antiavatar.guild_id == member.guild.id,
		)
		return self.bot.db_session.exec(statement).first()

	def set_antiavatar(
		self, member: discord.Member, avatar_info_in: p.AntiavatarCreate
	) -> None:
		self.bot.db_session.add(
			p.Antiavatar(
				user_id=member.id,
				guild_id=member.guild.id,
				url=avatar_info_in.url,
				message_id=avatar_info_in.message_id,
				original_url=avatar_info_in.original_url,
			)
		)

	def mark_gone(self, member: discord.Member) -> bool:
		membership = self._get(member)
		if membership is None:
			return False
		membership.ended_since = discord.utils.time_snowflake(dt.datetime.now())
		self.bot.db_session.add(membership)
		return True

	def mark_present(self, member: discord.Member) -> bool:
		membership = self._get(member)
		if membership is None:
			return False
		membership.ended_since = None
		self.bot.db_session.add(membership)
		return True

	async def raw_delete_membership(self, membership: p.Membership) -> None:
		db_user = membership.user
		was_last_membership = len(db_user.memberships) == 1
		self.bot.db_session.delete(membership)
		if was_last_membership:
			await self.bot.crud.user.delete_all_data(db_user)

	async def leave(self, member: discord.Member) -> bool:
		membership = self._get(member)
		if membership is None:
			return False
		await self.raw_delete_membership(membership)
		return True
