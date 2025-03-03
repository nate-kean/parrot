import datetime as dt
from collections.abc import Sequence

import discord
import sqlmodel as sm

import parrot.db.models as p
from parrot.utils import executor_function
from parrot.utils.exceptions import NotRegistered

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
		return self.session.exec(statement).first()

	def set_registered(self, member: discord.Member, value: bool) -> None:
		membership = self._get(member) or p.Membership(
			user=self.session.get(p.User, member.id) or p.User(id=member.id),
			guild=self.session.get(p.Guild, member.guild.id)
			or p.Guild(id=member.guild.id),
		)
		membership.is_registered = value
		self.session.add(membership)
		self.session.commit()

	def assert_registered(self, member: discord.Member) -> None:
		if not self.is_registered(member):
			raise NotRegistered.User(member)

	def is_registered(self, member: discord.Member) -> bool:
		if member.bot:  # Bots are always counted as registered
			return True
		membership = self._get(member)
		return membership is not None and membership.is_registered

	def get_messages_content(self, member: discord.Member) -> Sequence[str]:
		"""
		Get the text content of every message this user has said in this guild.
		"""
		# self.assert_registered(member)
		statement = sm.select(p.Message.content).where(
			p.Message.author_id == member.id,
			p.Message.guild_id == member.guild.id,
		)
		return self.session.exec(statement).all()

	def get_antiavatar(self, member: discord.Member) -> p.Antiavatar | None:
		# self.assert_registered(member)
		statement = sm.select(p.Antiavatar).where(
			p.Antiavatar.guild_id == member.guild.id,
			p.Antiavatar.user_id == member.id,
		)
		return self.session.exec(statement).first()

	def update_antiavatar(self, antiavatar: p.Antiavatar) -> None:
		self.session.add(antiavatar)
		self.session.commit()
		self.session.refresh(antiavatar)

	def create_antiavatar(
		self,
		member: discord.Member,
		antiavatar_in: p.AntiavatarCreate,
	) -> None:
		antiavatar = p.Antiavatar(
			guild_id=member.guild.id,
			user_id=member.id,
			url=antiavatar_in.url,
			message_id=antiavatar_in.message_id,
			original_url=antiavatar_in.original_url,
		)
		self.update_antiavatar(antiavatar)

	# region Affixes
	def set_custom_prefix(self, member: discord.Member, prefix: str) -> None:
		membership = self._get_or_create(member)
		membership.custom_prefix = prefix
		self.session.add(membership)

	def get_custom_prefix(self, member: discord.Member) -> str:
		return self._get_or_create(member).custom_prefix

	def set_custom_suffix(self, member: discord.Member, suffix: str) -> None:
		membership = self._get_or_create(member)
		membership.custom_suffix = suffix
		self.session.add(membership)

	def get_custom_suffix(self, member: discord.Member) -> str:
		return self._get_or_create(member).custom_suffix

	# endregion
	def mark_gone(self, member: discord.Member) -> bool:
		membership = self._get(member)
		if membership is None:
			return False
		membership.ended_since = discord.utils.time_snowflake(dt.datetime.now())
		self.session.add(membership)
		return True

	def mark_present(self, member: discord.Member) -> bool:
		membership = self._get(member)
		if membership is None:
			return False
		membership.ended_since = None
		self.session.add(membership)
		return True

	async def raw_delete_membership(self, membership: p.Membership) -> None:
		db_user = membership.user
		was_last_membership = len(db_user.memberships) == 1
		self.session.delete(membership)
		if was_last_membership:
			await self.bot.crud.user.delete_all_data(db_user)

	async def leave_guild(self, member: discord.Member) -> bool:
		membership = self._get(member)
		if membership is None:
			return False
		await self.raw_delete_membership(membership)
		return True

	@executor_function  # COUNT() is O(n) and can be slow with many messages
	def size(self, member: discord.Member) -> int:
		statement = sm.select(sm.func.count(sm.col(p.Message.id))).where(
			p.Message.author_id == member.id,
			p.Message.guild_id == member.guild.id,
		)
		return self.session.exec(statement).first() or 0
