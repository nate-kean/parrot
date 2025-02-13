"""rename message user id to author id

Revision ID: 3757315eec4c
Revises: 21069c329505
Create Date: 2025-02-11 20:46:34.826636

"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3757315eec4c"
down_revision: str | None = "21069c329505"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	with op.batch_alter_table("message") as bop:
		bop.alter_column("user_id", new_column_name="author_id")


def downgrade() -> None:
	with op.batch_alter_table("message") as bop:
		bop.alter_column("author_id", new_column_name="user_id")
