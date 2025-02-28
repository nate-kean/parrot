from typing import Self

from parrot import config
from parrot.utils import tag
from parrot.utils.types import AnyUser


class FriendlyError(Exception):
	"""An error we can show directly to the user."""


class NotRegistered(FriendlyError):
	"""Parrot tried to access data from an unregistered user."""

	@classmethod
	def User(cls, user: AnyUser) -> Self:
		return cls(
			f"User {user.mention} is not opted in to Parrot in this server. "
			f"To opt in, do the `{config.command_prefix}register` command."
		)


class NoData(FriendlyError):
	"""Parrot tried to access an empty or nonexistent corpus."""

	@classmethod
	def User(cls, user: AnyUser) -> Self:
		return cls(f"No data available for user {tag(user)}.")


class TextNotFound(FriendlyError):
	"""Parrot failed to find text to use for a command."""


class UserNotFound(FriendlyError):
	"""Parrot tried to get a Discord user who does not exist."""

	@classmethod
	def Username(cls, username: str) -> Self:
		return cls(f'User "{username}" does not exist.')


class FeatureDisabled(FriendlyError):
	"""A user tried to use a feature that is disabled on this instance of Parrot."""


class UserMissingPermissions(FriendlyError):
	"""
	A user tried to commit an action with Parrot that they don't have the right
	permissions to do.
	"""


class AlreadyScanning(FriendlyError):
	"""
	A user tried to run Quickstart in a channel that Quickstart is already
	scanning for them.
	"""


class WrongChannelType(FriendlyError):
	"""
	Requested command is not available in this type of channel.
	"""
