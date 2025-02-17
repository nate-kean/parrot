import logging
from types import ModuleType
from typing import TYPE_CHECKING, ClassVar, cast

import discord
import sqlalchemy as sa
import sqlmodel as sm
from tqdm import tqdm


if TYPE_CHECKING:
	from parrot.alembic.models import r7d0ffe4179c6
from parrot.utils import cast_not_none


# Type alias to denote a string that is (supposed to be) in ISO 8601 format
ISODateString = str


class PModel(sm.SQLModel):
	"""Parrot Model

	SQLModel class but the __table__ property is unhidden because I need it in
	my migrations
	"""

	__table__: ClassVar[sa.Table]


def cleanup_models(models_module: ModuleType) -> None:
	"""
	You have to do this anywhere you define or import a SQLModel model within a
	migration, or else it will be there to cause name collisions in migrations
	that come after it.
	SQLModel is designed to be intuitive, easy to use, highly compatible, and
	robust.
	"""
	for name in models_module.__all__:
		try:
			obj = getattr(models_module, name)
		except AttributeError:
			continue
		if not isinstance(obj, sm.main.SQLModelMetaclass):
			continue
		table = cast(sa.Table, getattr(obj, "__table__"))
		sm.SQLModel.metadata.remove(table)


def count(session: sm.Session, column: sa.ColumnClause) -> int | None:
	return session.execute(sa.func.count(column)).scalar()


class AddChannelAndMessageGuildIDFactory:
	"""
	Extracted out of revision 7d0ffe4179c6 because I originally had plans to
	run the retry phase elsewhere
	"""

	def __init__(
		self,
		# type: ignore -- Cry, Pylance, I'm using it as a type anyway
		module_r7d0ffe4179c6: "r7d0ffe4179c6",  # type: ignore
		session: sm.Session,
		*,
		retrying: bool = False,
	):
		if (
			getattr(module_r7d0ffe4179c6, "__name__")
			!= "parrot.alembic.models.r7d0ffe4179c6"
		):
			raise TypeError("Wrong module DOOFUS")
		self.m = module_r7d0ffe4179c6
		self.session = session
		self.retrying = retrying

	@property
	def retrying(self) -> bool:
		return self.target_value != self.m.ErrorCode.UNPROCESSED.value

	@retrying.setter
	def retrying(self, value: bool) -> None:
		if value:
			self.target_value = self.m.ErrorCode.REQUEST_FAILED.value
		else:
			self.target_value = self.m.ErrorCode.UNPROCESSED.value

	async def _search_channel(
		self,
		channel: discord.TextChannel,
		candidate: "r7d0ffe4179c6.Message",
	) -> tuple[int, bool]:
		"""
		Get a chunk of messages around the chosen message (inclusive).
		The chosen message is relevant, and chances are ones near it are too.
		:param channel: channel to search for the message in.
		:param candidate: database form of the message to search for.
		:return: (number of relevant messages processed,
		         whether the API request succeeded).
		"""
		try:
			# The largest chunk we can get from this API in one call is 100.
			# May not contain the candidate, since we do not know if this is the
			# channel it's really in.
			messages = [
				message
				async for message in channel.history(
					limit=100, around=candidate
				)
			]
		except KeyboardInterrupt:
			raise
		except Exception as exc:
			logging.warning(
				"Request for messages after"
				f"{channel.guild.id}/{channel.id}/{candidate.id} "
				f"failed: {exc}"
			)
			candidate.guild_id = self.m.ErrorCode.REQUEST_FAILED.value
			self.session.add(candidate)
			return 1, False

		# Get any yet-unprocessed messages from the database that match the ones
		# in the chunk.
		message_ids = (message.id for message in messages)
		db_messages = self.session.exec(
			sm.select(self.m.Message).where(
				sm.col(self.m.Message.id).in_(message_ids),
				self.m.Message.guild_id == 0,
			)
		)
		# Fill in the guild IDs and channel IDs for those messages in the
		# database.
		num_found = 0
		for db_message in db_messages:
			for message in messages:
				if db_message.id != message.id:
					continue
				# logging.debug(
				# 	f"Message {db_message.id} in guild/channel "
				# 	f"{db_message.guild_id}/{db_message.channel_id}"
				# )
				# message.guild guaranteed to exist because we got it from a
				# guild
				db_message.guild_id = cast_not_none(message.guild).id
				db_message.channel_id = message.channel.id
				self.session.add(db_message)
				num_found += 1
				break
		return (
			num_found,
			candidate.guild_id != self.target_value,
		)

	async def process_messages(
		self, channels: list[discord.TextChannel]
	) -> None:
		"""
		Scattershot scraping strategy: process chunks of 100 messages all over
		Discord around relevant messages.
		Collect every relevant message's guild and channel ID, while staying as
		gracious to Discord's API as we can. Using the history API, we can pick
		up up to 100 relevant messages per API call. By only calling it around
		messages we know we need to process (as opposed to using just one
		history iterator per channel and scanning the entire thing), we will
		probably end up skipping chunks of messages we don't need to process,
		further reducing API calls.
		In a very large channel with many relevant messages, this could save
		hours. In a very large channel with few relevant messages, this could
		save days.
		Unfortunately, since we don't know which channel any message is in, we
		have to look for it in every channel Parrot can learn in.
		Still, these calls _may_ end up finding other relevant messages.
		"""
		unprocessed_count: int = self.session.exec(
			sm.select(sa.func.count(self.m.Message.id)).where(
				self.m.Message.guild_id == self.target_value
			)
		).one()

		# "Pick an unprocessed message. Which one, doesn't matter."
		statement = (
			sm.select(self.m.Message)
			.where(self.m.Message.guild_id == self.target_value)
			.limit(1)
		)
		with tqdm(
			total=unprocessed_count, desc="Messages processed"
		) as progress_bar:
			# Repeat until all messages from the database are processed.
			while (
				candidate := self.session.exec(statement).first()
			) is not None:
				# Look for the message in every learning channel.
				# Great part is this may incidentally find other relevant
				# messages we didn't ask for.
				for channel in channels:
					num_found, candidate_found = await self._search_channel(
						channel, candidate
					)
					progress_bar.update(n=num_found)
					if candidate_found:
						break
				else:
					# Candidate message never found.
					# Mark it processed, otherwise we may get stuck with the
					# database selecting the same unprocessable message over and
					# over.
					logging.debug(
						f"Message {candidate.id} not found in learning channels"
					)
					candidate.guild_id = self.m.ErrorCode.NOT_FOUND.value
					self.session.add(candidate)
					progress_bar.update(n=1)
