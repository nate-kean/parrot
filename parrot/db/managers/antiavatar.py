import asyncio
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING, Self

import discord

import parrot.db.models as p
from parrot import config
from parrot.config import logger
from parrot.utils import image


if TYPE_CHECKING:
	from parrot.bot import Parrot


class AntiavatarManager:
	"""
	A cache layer over Parrot's "antiavatars" that it uses when it imitates.

	Stores generated images in a channel on Discord and keeps the necessary
	information locally to retrieve them.

	Works with respect to Discord MEMBERS, i.e., to instances of users per
	guild. This way guild-specific avatars can be honored.
	"""

	_constructor_token = object()

	def __init__(
		self,
		constructor_token: object,
		bot: "Parrot",
		avatar_channel: discord.TextChannel,
	):
		if constructor_token is not AntiavatarManager._constructor_token:
			raise Exception(
				"Constructor requires async operations. Please use .new()"
			)
		self.bot = bot
		self.avatar_channel = avatar_channel

	@classmethod
	async def new(cls, bot: "Parrot") -> Self:
		avatar_channel = await bot.fetch_channel(config.avatar_store_channel_id)
		if not isinstance(avatar_channel, discord.TextChannel):
			raise TypeError(
				"Invalid channel type for the avatar store: "
				f"{avatar_channel}. The provided channel for storing "
				"avatars must be a regular TextChannel."
			)
		return cls(AntiavatarManager._constructor_token, bot, avatar_channel)

	async def fetch(self, member: discord.Member) -> str:
		self.bot.crud.member.assert_registered(member)
		antiavatar = self.bot.crud.member.get_antiavatar(member)

		has_preexisting_antiavatar = antiavatar is not None
		if has_preexisting_antiavatar:
			has_changed_avatar = AntiavatarManager._url_id(
				member.display_avatar.url
			) != AntiavatarManager._url_id(antiavatar.original_url)
			if not has_changed_avatar:
				# Use the cached antiavatar.
				return antiavatar.url

			# Else, user has changed their avatar here; respect the user's
			# privacy by deleting the message with their old avatar.
			# (This operation doesn't need to complete before continuing)
			asyncio.create_task(self.delete_antiavatar_file(antiavatar))

		# User has changed their avatar in this guild since last time they did
		# |imitate, and/or Parrot has never made the antiavatar for this avatar,
		# so we must create this avatar's anti.
		antiavatar_file = await image.create_antiavatar_file(member)

		# Post the new antiavatar to the "avatar store" Discord channel.
		message = await self.avatar_channel.send(
			file=discord.File(
				antiavatar_file.buffer, f"{member.id}.{antiavatar_file.ext}"
			)
		)

		# Record the information to access it later.
		if has_preexisting_antiavatar:
			antiavatar.message_id = message.id
			antiavatar.url = message.attachments[0].url
			antiavatar.original_url = member.display_avatar.url
			self.bot.crud.member.update_antiavatar(antiavatar)
		else:
			self.bot.crud.member.create_antiavatar(
				member,
				p.AntiavatarCreate(
					message_id=message.id,
					url=message.attachments[0].url,
					original_url=member.display_avatar.url,
				),
			)
		return message.attachments[0].url

	async def delete_antiavatar_file(self, antiavatar: p.Antiavatar) -> None:
		message_id = antiavatar.message_id
		try:
			message = await self.avatar_channel.fetch_message(message_id)
		except discord.NotFound:
			logger.warning(
				f"Tried to delete message {message_id} from the avatar store, "
				"but it doesn't exist."
			)
		else:
			await message.delete()

	@staticmethod
	def _url_id(url: str) -> str:
		path = urllib.parse.urlparse(url).path
		return Path(path).suffix
