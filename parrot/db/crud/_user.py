import asyncio
from typing import Any

import sqlmodel as sm

import parrot.db.models as p
from parrot.utils.trace import trace
from parrot.utils.types import AnyUser

from .types import SubCRUD


@trace
class CRUDUser(SubCRUD):
	"""Methods on Users that are Guild-agnostic

	I.e., these methods regard a User's global state
	"""

	def wants_wawa(self, user: AnyUser) -> bool:
		statement = sm.select(p.User.wants_random_wawa).where(
			p.User.id == user.id
		)
		return self.session.exec(statement).first() or False

	def toggle_random_wawa(self, user: AnyUser) -> bool:
		"""
		Toggle your "wants random wawa" setting globally.
		Returns new state.
		"""
		db_user = self.session.get(p.User, user.id) or p.User(id=user.id)
		db_user.wants_random_wawa = not db_user.wants_random_wawa
		self.session.add(db_user)
		return db_user.wants_random_wawa

	def get_raw(self, user: AnyUser) -> dict[str, Any] | None:
		db_user = self.session.get(p.User, user.id)
		if db_user is None:
			return None
		# TODO: this dumps the relationships too, right?
		#       How many levels deep?
		return db_user.model_dump(mode="json")

	def exists(self, user: AnyUser) -> bool:
		"""Search Parrot's database for any trace of this user."""
		return self.session.get(p.User, user.id) is not None

	async def delete_all_data(self, user: AnyUser | p.User) -> bool:
		"""
		Delete ALL the data associated with a user.
		You better be sure calling this method!
		"""
		if isinstance(user, p.User):
			db_user = user
		else:
			db_user = self.session.get(p.User, user.id)
			if db_user is None:
				return False

		# Delete all their information contained in the abstractions over the
		# database
		async with asyncio.TaskGroup() as tg:
			for membership in db_user.memberships:
				if membership.antiavatar is not None:
					tg.create_task(
						self.bot.antiavatars.delete_antiavatar_file(
							membership.antiavatar
						)
					)
				try:
					del self.bot.markov_models.cache[
						(db_user.id, membership.guild.id)
					]
				except KeyError:
					pass

		# Delete all their information in the database
		self.session.delete(db_user)
		return True

	def size(self, member: AnyUser) -> int:
		statement = sm.select(sm.func.count(sm.col(p.Message.id))).where(
			p.Message.author_id == member.id
		)
		return self.session.exec(statement).first() or 0
