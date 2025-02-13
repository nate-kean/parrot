"""add cascade delete relationships 2

Revision ID: d965a0d5f9ef
Revises: 31fa22f3fa57
Create Date: 2025-02-12 23:51:38.952840

"""

from collections.abc import Sequence

from parrot.alembic.common import batch_alter_table

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d965a0d5f9ef"
down_revision: str | None = "31fa22f3fa57"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	# "antiavatar": replace the two foreign key constraints relative to "guild"
	# and "user" with one relative to "membership", plus on delete cascade
	with batch_alter_table("antiavatar") as bop:
		bop.drop_constraint(
			op.f("fk_antiavatar_guild_id_guild"), type_="foreignkey"
		)
		bop.drop_constraint(
			op.f("fk_antiavatar_user_id_user"), type_="foreignkey"
		)
		bop.create_foreign_key(
			op.f("fk_antiavatar_guild_id_user_id_membership"),
			"membership",
			["guild_id", "user_id"],
			["guild_id", "user_id"],
			ondelete="cascade",
		)

	# "channel.guild_id": add on delete cascade
	with batch_alter_table("channel") as bop:
		bop.drop_constraint(
			op.f("fk_channel_guild_id_guild"), type_="foreignkey"
		)
		bop.create_foreign_key(
			op.f("fk_channel_guild_id_guild"),
			"guild",
			["guild_id"],
			["id"],
			ondelete="cascade",
		)

	# "membership": add foreign key constraint "guild_id", on delete cascade
	with batch_alter_table("membership") as bop:
		bop.create_foreign_key(
			op.f("fk_membership_guild_id_guild"),
			"guild",
			["guild_id"],
			["id"],
			ondelete="cascade",
		)

	with batch_alter_table("message") as bop:
		# "message.channel_id": add foreign key constraint, on delete cascade
		bop.create_foreign_key(
			op.f("fk_message_channel_id_channel"),
			"channel",
			["channel_id"],
			["id"],
			ondelete="cascade",
		)
		# replace foreign key constraint relative to "user" with one relative to
		# "membership", preserve on delete cascade
		bop.drop_constraint(
			op.f("fk_message_author_id_user"), type_="foreignkey"
		)
		bop.create_foreign_key(
			op.f("fk_message_guild_id_author_id_membership"),
			"membership",
			["guild_id", "author_id"],
			["guild_id", "user_id"],
			ondelete="cascade",
		)


def downgrade() -> None:
	with batch_alter_table("message") as bop:
		# "message.channel_id": remove foreign key constraint, on delete nothing
		bop.drop_constraint(
			op.f("fk_message_channel_id_channel"), type_="foreignkey"
		)
		# replace foreign key constraint relative to "membership" with one
		# relative to "user", preserve on delete cascade
		bop.drop_constraint(
			op.f("fk_message_guild_id_author_id_membership"), type_="foreignkey"
		)
		bop.create_foreign_key(
			op.f("fk_message_author_id_user"),
			"user",
			["author_id"],
			["id"],
			ondelete="cascade",
		)

	# "membership": remove foreign key constraint "guild_id"
	with batch_alter_table("membership") as bop:
		bop.drop_constraint(
			op.f("fk_membership_guild_id_guild"), type_="foreignkey"
		)

	# "channel.guild_id": remove on delete cascade
	with batch_alter_table("channel") as bop:
		bop.drop_constraint(
			op.f("fk_channel_guild_id_guild"), type_="foreignkey"
		)
		bop.create_foreign_key(
			op.f("fk_channel_guild_id_guild"),
			"guild",
			["guild_id"],
			["id"],
			ondelete=None,
		)

	# "antiavatar": replace foreign key constraint relative to "membership" with
	# two relative to "guild" and "user"
	with batch_alter_table("antiavatar") as bop:
		# TODO: What did SQLAlchemy end up naming this constraint
		bop.drop_constraint(
			op.f("fk_antiavatar_guild_id_user_id_membership"),
			type_="foreignkey",
		)
		# Just "user_id" on delete cascade because that's how it was before 🤷
		bop.create_foreign_key(
			op.f("fk_antiavatar_user_id_user"),
			"user",
			["user_id"],
			["id"],
			ondelete="cascade",
		)
		bop.create_foreign_key(
			op.f("fk_antiavatar_guild_id_guild"),
			"guild",
			["guild_id"],
			["id"],
			ondelete=None,
		)
