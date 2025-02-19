from typing import TYPE_CHECKING

import sqlmodel as sm


if TYPE_CHECKING:
	from parrot.bot import Parrot


class SubCRUD:
	def __init__(self, bot: "Parrot", session: sm.Session):
		self.bot = bot
		self.session = session
