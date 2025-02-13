from types import ModuleType
from typing import ClassVar, cast

import sqlalchemy as sa
import sqlmodel as sm


# Type alias to denote a string that is (supposed to be) in ISO 8601 format
ISODateString = str


class PModel(sm.SQLModel):
	"""Parrot Model

	SQLModel class but the __table__ property is unhidden because I need it in
	my migrations
	"""

	__table__: ClassVar[sa.Table]


def cleanup_models(models_module: ModuleType) -> None:
	"""
	You have to do this anywhere you define or import a SQLModel model within a
	migration, or else it will be there to cause name collisions in migrations
	that come after it.
	SQLModel is designed to be intuitive, easy to use, highly compatible, and
	robust.
	"""
	for name in models_module.__all__:
		try:
			obj = getattr(models_module, name)
		except AttributeError:
			continue
		if not isinstance(obj, sm.main.SQLModelMetaclass):
			continue
		table = cast(sa.Table, getattr(obj, "__table__"))
		sm.SQLModel.metadata.remove(table)


def count(session: sm.Session, column: sa.ColumnClause) -> int | None:
	return session.execute(sa.func.count(column)).scalar()
