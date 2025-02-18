"""
Parrot's database models, using SQLModel.

This is a local cache of data from the Discord API that Parrot needs to access
with higher frequency than Discord's ratelimits, plus some of Parrot's own
information.

Measures are taken in program code to keep this database in parity with Discord.

N.B. The primary keys in these tables are from Discord, and are intentionally
_not_ created automatically by the database. Every primary key (or primary key
component) is expected to be a valid Discord ID.
"""

# TODO: Feasible to keep all Markov chain generators in the database,
# remove the in-memory cache?
# NOTE: sa.PickleType?

# TODO: understand .commit() and .refresh()/see if there are any occurrences
# that can be deleted

# TODO: Are any of these Relationships or back-populations ones Parrot can get
# away without having?

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

from parrot.db import NAMING_CONVENTION, GuildMeta
from parrot.utils.types import Snowflake


SQLModel.metadata.naming_convention = NAMING_CONVENTION


class Channel(SQLModel, table=True):
	id: Snowflake = Field(primary_key=True)
	can_speak_here: bool = False
	can_learn_here: bool = False
	webhook_id: Snowflake | None = None
	guild_id: Snowflake = Field(foreign_key="guild.id")

	# Explicit delete conditions:
	# - Channel is deleted on Discord.
	# Relationships:
	# - Any one Channel belongs to exactly ONE Guild, while any given Guild can
	#   hold MANY channels.
	# - Any one Channel can hold MANY Messages, while any given Message belongs
	#   to exactly ONE Channel.
	# Cascade delete conditions:
	# - If a Channel's associated Guild is deleted.
	guild: "Guild" = Relationship(back_populates="channels")
	messages: list["Message"] = Relationship(
		back_populates="channel", cascade_delete=True
	)


class Message(SQLModel, table=True):
	id: Snowflake = Field(primary_key=True)
	content: str
	author_id: Snowflake = Field(foreign_key="user.id")
	channel_id: Snowflake = Field(foreign_key="channel.id")
	guild_id: Snowflake = Field(foreign_key="guild.id")
	__table_args__ = (
		# Messages are going to be SELECTed almost exclusively by these columns,
		# so declare an index for them
		sa.Index("ix_guild_id_author_id", "guild_id", "author_id"),
		# SQLAlchemy isn't smart enough to figure out composite foreign keys on
		# its own
		sa.ForeignKeyConstraint(
			["guild_id", "author_id"],
			["membership.guild_id", "membership.user_id"],
		),
	)

	# Explicit delete conditions:
	# - Message is deleted on Discord.
	# Relationships:
	# - Any one Message belongs to exactly ONE Membership, while any given
	#   Membership can be associated with MANY Messages.
	# - Any one Message belongs to exactly ONE Channel, while any given Channel
	#   can hold MANY Messages.
	# Cascade delete conditions:
	# - If a Message's associated Channel is deleted.
	# - If a Message's associated Membership is deleted.
	channel: Channel = Relationship(back_populates="messages")
	membership: "Membership" = Relationship(back_populates="messages")


class Membership(SQLModel, table=True):
	"""User-Guild relationship"""

	# Optional so Membership objects can be constructed through the user and
	# guild attributes
	user_id: Snowflake = Field(
		default=None, foreign_key="user.id", primary_key=True
	)
	guild_id: Snowflake = Field(
		default=None, foreign_key="guild.id", primary_key=True
	)
	is_registered: bool = False
	# Timestamp denoting when a user left this guild.
	# None if the user is still there.
	ended_since: Snowflake | None = None

	# Explicit delete conditions:
	# - User leaves a Guild *for long enough*.
	# - (TODO) User does a guild-specific version of |forget me.
	# Relationships:
	# - Any one Membership belongs to exactly ONE User, while any given User can
	#   have MANY Memberships.
	# - Any one Membership is associated with exactly ONE Guild, while any given
	#   Guild can hold MANY Memberships.
	# - Any one Membership can have ONE OR ZERO Antiavatars, and each Antiavatar
	#   is associated with exactly ONE Membership.
	# Cascade delete conditions:
	# - If a Membership's associated User is deleted.
	# - If a Membership's associated Guild is deleted.
	user: "User" = Relationship(back_populates="memberships")
	guild: "Guild" = Relationship(back_populates="memberships")
	# TODO: this does work, right? Even without a bespoke foreign key column for
	# it?
	antiavatar: "Antiavatar" = Relationship(
		back_populates="membership", cascade_delete=True
	)
	messages: list[Message] = Relationship(
		back_populates="membership", cascade_delete=True
	)


class User(SQLModel, table=True):
	id: Snowflake = Field(primary_key=True)
	wants_random_wawa: bool = True

	# Explicit delete conditions:
	# - User does |forget me.
	# - User's last associated Memberships are deleted.
	# Relationships:
	# - Any one User can have MANY Memberships, while any given Membership
	#   belongs to exactly ONE User.
	# Cascade delete conditions:
	# - None (a User will never be directly deleted as a result of a row in
	#   another table being deleted).
	memberships: list[Membership] = Relationship(
		back_populates="user", cascade_delete=True
	)


class Guild(SQLModel, table=True):
	id: Snowflake = Field(primary_key=True)
	imitation_prefix: str = GuildMeta.default_imitation_prefix
	imitation_suffix: str = GuildMeta.default_imitation_suffix

	gone_since: Snowflake | None = None

	# Explicit delete conditions:
	# - Guild is deleted on Discord.
	# - (TODO) Parrot is removed from a Guild and is gone without being added
	#   back *for long enough*.
	# Relationships:
	# - Any one Guild can hold MANY Memberships, while any given Membership
	#   belongs to exactly ONE Guild.
	# - Any one Guild can hold MANY Channels, while any given Channel belongs
	#   to exactly ONE Guild.
	# Cascade delete conditions:
	# - None (a Guild will never be deleted as a result of a row in another
	#   table being deleted).
	memberships: list[Membership] = Relationship(
		back_populates="guild", cascade_delete=True
	)
	channels: list[Channel] = Relationship(
		back_populates="guild", cascade_delete=True
	)


class AntiavatarBase(SQLModel):
	original_url: str
	url: str
	message_id: Snowflake


# TODO (optimization): merge these across guilds for users who don't use
# guild-specific avatars/don't have Premium
class Antiavatar(AntiavatarBase, table=True):
	"""Avatar info linked to a Membership"""

	guild_id: Snowflake = Field(foreign_key="guild.id", primary_key=True)
	user_id: Snowflake = Field(foreign_key="user.id", primary_key=True)

	__table_args__ = (
		sa.ForeignKeyConstraint(
			["guild_id", "user_id"],
			["membership.guild_id", "membership.user_id"],
		),
	)

	# Explicit delete conditions:
	# - None (an Antiavatar is never (directly) deleted after it is created).
	# Relationships:
	# - Any Antiavatar that exists belongs to exactly ONE Membership, while any
	#   given Membership may have ONE Antiavatar OR NONE.
	# Cascade delete conditions:
	# - If an Antiavatar's associated Membership is deleted.
	membership: Membership = Relationship(back_populates="antiavatar")


class AntiavatarCreate(AntiavatarBase):
	pass
