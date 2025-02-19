import discord
import sqlmodel as sm

import parrot.db.models as p
from parrot.utils import is_learnable
from parrot.utils.types import (
	AnyChannel,
	LearnableChannel,
	Snowflake,
	SpeakableChannel,
)

from .types import SubCRUD


class CRUDChannel(SubCRUD):
	def set_can_learn_here(
		self, channel: LearnableChannel, value: bool
	) -> bool:
		"""
		Set whether Parrot is allowed to learn in a certain channel.

		:param channel: the channel in question (in DISCORD's format)
		:param value: the new state of the permission flag
		:returns: whether the flag did not already have that value
		"""
		db_channel = self.bot.db_session.get(p.Channel, channel.id)
		if db_channel is not None:
			if db_channel.can_learn_here == value:
				# Flag already had this value
				return False
			# Set this now because it might not have been during the migrations
			db_channel.guild_id = channel.guild.id
		else:
			db_channel = p.Channel(id=channel.id, guild_id=channel.guild.id)
		db_channel.can_learn_here = value
		self.bot.db_session.add(db_channel)
		# Flag's value is different now because of this call
		# (including if you create a new row just to set the flag to False)
		return True

	def can_learn_here(self, channel: AnyChannel) -> bool:
		if not is_learnable(channel):
			return False
		statement = sm.select(p.Channel.id).where(
			p.Channel.id == channel.id,
			# TODO: works without the `== True`?
			p.Channel.can_learn_here == True,
		)
		return self.bot.db_session.exec(statement).first() is not None

	def get_webhook_id(self, channel: SpeakableChannel) -> Snowflake | None:
		statement = sm.select(p.Channel.webhook_id).where(
			p.Channel.id == channel.id
		)
		return self.bot.db_session.exec(statement).first()

	def set_webhook_id(
		self,
		channel: SpeakableChannel,
		webhook: discord.Webhook,
	) -> None:
		db_channel = self.bot.db_session.get(
			p.Channel, channel.id
		) or p.Channel(id=channel.id, guild_id=channel.guild.id)
		db_channel.webhook_id = webhook.id
		self.bot.db_session.add(db_channel)
		self.bot.db_session.commit()
		self.bot.db_session.refresh(db_channel)

	def delete(self, channel: LearnableChannel) -> bool:
		db_channel = self.bot.db_session.get(p.Channel, channel.id)
		if db_channel is None:
			return False
		self.bot.db_session.delete(db_channel)
		return True
