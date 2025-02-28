from enum import Enum, auto
from typing import cast

import discord

import parrot.db.models as p
from parrot import config
from parrot.utils import cast_not_none, regex
from parrot.utils.types import Snowflake

from .types import SubCRUD


class CRUDMessage(SubCRUD):
	class CreateOrUpdate(Enum):
		CREATED = auto()
		UPDATED = auto()
		REJECTED = auto()

	@staticmethod
	def _extract_text(message: discord.Message) -> str:
		for embed in message.embeds:
			if embed.description is not None:
				message.content += "\n" + embed.description
		for attachment in message.attachments:
			message.content += " " + attachment.url
		return message.content

	def validate_message(self, message: discord.Message) -> bool:
		"""
		A message must pass all of these checks before Parrot can learn from it.
		"""
		return (
			# Text content not empty.
			len(message.content) > 0
			and
			# Not a Parrot command.
			not message.content.startswith(config.command_prefix)
			and
			# Most bots' commands start with non-alphanumeric characters, so if
			# a message starts with one other than a known Markdown character or
			# special Discord character, Parrot should just avoid it because
			# it's probably a command.
			(
				message.content[0].isalnum()
				or bool(regex.discord_string_start.match(message.content[0]))
				or bool(regex.markdown.match(message.content[0]))
			)
			and
			# Don't learn from self.
			message.author.id != cast_not_none(self.bot.user).id
			and
			# Don't learn from Webhooks.
			message.webhook_id is None
			and
			# Parrot must be allowed to learn in this channel.
			self.bot.crud.channel.can_learn_here(message.channel)
			and
			# People will often say "v" or "z" on accident while spamming,
			# and it doesn't really make for good learning material.
			message.content not in ("v", "z")
			and
			# I think this can happen sometimes, as evidenced by a number of
			# messages with author ID 0 that I found in the database
			message.author.id != 0
		)

	def record(self, message: discord.Message) -> bool:
		"""
		:pre: message.author is a discord.Member
		"""

		member = cast(discord.Member, message.author)
		if not self.bot.crud.member.is_registered(member):
			return False

		if not self.validate_message(message):
			return False

		# Convert the messages to the database's format and add them to this
		# user's corpus.
		self.session.add(
			p.Message(
				id=message.id,
				author_id=member.id,
				guild_id=member.guild.id,
				channel_id=message.channel.id,
				content=CRUDMessage._extract_text(message),
			)
		)

		return True

		# for message in messages:
		# 	self.session.refresh(message)
		# if len(messages) > 0:
		# 	return self.corpora.add(user, messages)
		# return 0

	def update(self, message: discord.Message) -> bool:
		db_message = self.session.get(p.Message, message.id)
		if db_message is None:
			return False
		db_message.content = CRUDMessage._extract_text(message)
		self.session.add(db_message)
		return True

	def record_or_update(self, message: discord.Message) -> CreateOrUpdate:
		db_message = self.session.get(p.Message, message.id)
		if db_message is None:
			success = self.record(message)
			return (
				CRUDMessage.CreateOrUpdate.CREATED
				if success
				else CRUDMessage.CreateOrUpdate.REJECTED
			)
		else:
			success = self.update(message)
			return (
				CRUDMessage.CreateOrUpdate.UPDATED
				if success
				else CRUDMessage.CreateOrUpdate.REJECTED
			)

	def delete(self, message_id: Snowflake) -> p.Message | None:
		"""Delete a message from the database."""
		db_message = self.session.get(p.Message, message_id)
		if db_message is None:
			return None
		self.session.delete(db_message)
		return db_message
