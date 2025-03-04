"""
Database schema for Parrot v1 as defined here:
https://github.com/garlic-os/parrot/blob/53a95b8/bot.py#L56-L82

Ported/preserved for migrations
"""

# from parrot.alembic.common import ISODateString
from parrot.db import NAMING_CONVENTION
from parrot.utils.types import Snowflake
from sqlmodel import Field, SQLModel


SQLModel.metadata.naming_convention = NAMING_CONVENTION


__all__ = ["Channels", "Guilds", "Messages", "Users"]


class Channels(SQLModel, table=True):
	id: Snowflake = Field(primary_key=True)
	can_speak_here: bool = False
	can_learn_here: bool = False
	webhook_id: Snowflake | None


class Guilds(SQLModel, table=True):
	id: Snowflake = Field(primary_key=True)
	imitation_prefix: str = "Not "
	imitation_suffix: str = ""


class Messages(SQLModel, table=True):
	id: Snowflake = Field(primary_key=True)
	user_id: Snowflake = Field(foreign_key="users.id")
	# This column's type is de facto `int | str`.
	# But! I can't type annotate that because Cannot Have A Union As A
	# SQLAlchemy Field. Say that to this column's face SQLAlchemy.
	# See models.rfd7c085ab081.py
	timestamp: int  # | ISODateString
	content: str


class Users(SQLModel, table=True):
	id: Snowflake = Field(primary_key=True)
	is_registered: bool = False
	original_avatar_url: str | None
	modified_avatar_url: str | None
	modified_avatar_message_id: Snowflake | None
