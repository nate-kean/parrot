"""add cascade delete relationships

Revision ID: b8f950e3fb56
Revises: 79a4371fbc92
Create Date: 2025-01-21 14:46:13.725138

"""

from collections.abc import Sequence

from parrot.alembic.common import batch_alter_table

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b8f950e3fb56"
down_revision: str | None = "79a4371fbc92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	# I can see this constraint right in the database but Alembic doesn't
	with batch_alter_table("membership") as bop:
		bop.drop_constraint(
			op.f("fk_membership_user_id_user"), type_="foreignkey"
		)
		bop.create_foreign_key(
			op.f("fk_membership_user_id_user"),
			"user",
			["user_id"],
			["id"],
			ondelete="CASCADE",
		)

	with batch_alter_table("message") as bop:
		bop.drop_constraint(
			op.f("fk_message_author_id_user"), type_="foreignkey"
		)
		bop.create_foreign_key(
			op.f("fk_message_author_id_user"),
			"user",
			["author_id"],
			["id"],
			ondelete="CASCADE",
		)

	with batch_alter_table("antiavatar") as bop:
		bop.drop_constraint(
			op.f("fk_antiavatar_user_id_user"), type_="foreignkey"
		)
		bop.create_foreign_key(
			op.f("fk_antiavatar_user_id_user"),
			"user",
			["user_id"],
			["id"],
			ondelete="CASCADE",
		)


def downgrade() -> None:
	with batch_alter_table("membership") as bop:
		bop.drop_constraint(
			op.f("fk_membership_user_id_user"), type_="foreignkey"
		)
		bop.create_foreign_key(
			op.f("fk_membership_user_id_user"),
			"user",
			["user_id"],
			["id"],
			ondelete=None,
		)
	with batch_alter_table("message") as bop:
		bop.drop_constraint(
			op.f("fk_message_author_id_member"), type_="foreignkey"
		)
		bop.create_foreign_key(
			op.f("fk_messages_user_id_users"),
			"user",
			["author_id"],
			["id"],
			ondelete=None,
		)
	with batch_alter_table("antiavatar") as bop:
		bop.drop_constraint(
			op.f("fk_membership_user_id_user"), type_="foreignkey"
		)
		bop.create_foreign_key(
			op.f("fk_membership_user_id_user"),
			"user",
			["user_id"],
			["id"],
			ondelete=None,
		)
