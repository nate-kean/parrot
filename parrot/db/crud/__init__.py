from typing import TYPE_CHECKING

import sqlmodel as sm

from . import _channel, _guild, _member, _message, _user


if TYPE_CHECKING:
	from parrot.bot import Parrot


class CRUD:
	"""A pile of Create-Read-Update-Delete functions for Parrot's database"""

	def __init__(self, bot: "Parrot", session: sm.Session):
		self.channel = _channel.CRUDChannel(bot, session)
		self.guild = _guild.CRUDGuild(bot, session)
		self.member = _member.CRUDMember(bot, session)
		self.user = _user.CRUDUser(bot, session)
		self.message = _message.CRUDMessage(bot, session)
