"""
Generate a database on the v1 schema that contains a subset of Parrot's real
data. Made to make sure data makes it through the migrations in one piece.
"""

import os
import subprocess
import textwrap
from collections.abc import Generator

import sqlmodel as sm
from parrot import config
from parrot.alembic.models import v1
from parrot.config import logger
from parrot.utils.types import Snowflake


V1_REVISION = "fe3138aef0bd"

# This data is from me and I grant myself the right to publish it
RAW_MESSAGES = """
	431263950651260939	206235904644349953	0	thanks <@!346804110303166474>
	431264596184137728	206235904644349953	1969-12-31T18:00:00	im never posting screenshots of windows xp videos again
	431266865441013770	206235904644349953	2025-01-27T20:39:07.631139	https://www.youtube.com/watch?v=XRRsz_I44Ok o e-gads
	431269377208352790	206235904644349953	2021	0.35i39j69i61j0l4.1904j0j4
	431271093152514058	206235904644349953	2024	<@!132924988100444160>
	431271833770393601	206235904644349953	0	tarp
	431273094020202508	206235904644349953	0	lel crazyboye
	431273763880042508	206235904644349953	0	ᕕ(ᐛ)ᕗ
	12345	206235904644349953	0	https://www.youtube.com/watch?v=SAxpAs1Iaec ᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )ᕗᕕ( ᐛ )...
	431274136590090240	12345	0	it was worth the try 🤣 😂
"""

RAW_CHANNELS = """
	280298381807714304	1	1	1024396345768935484
	293340619395563521	1	0	None
	325969983441993729	1	1	1028837359971733575
	337470134950297602	1	0	1085986368980779119
	664483917419642921	1	0	1026171527386890251
	664485795977101334	1	0	1201180303901851749
	664486634271670284	1	1	1024510166273638432
	779820218326974464	1	0	1154169387792748685
	1012362190449279037	1	1	1034385696816889897
"""

RAW_GUILDS = """
	280298381807714304	​	​ simulacrum
	576212353390215178	The Anti	None
	664479042161999894	The Anti	None
"""

RAW_USERS = """
	206235904644349953	1	https://cdn.discordapp.com/avatars/206235904644349953/16805ceec8b6f8856e272163512330e8.png?size=1024	https://cdn.discordapp.com/attachments/867573882608943127/1323786690598277163/206235904644349953.PNG?ex=6775c7ed&is=6774766d&hm=feddf878d56db64a63d522292a34cc6d474c83cfadcbe915f2ccc2d054b3c90e&	1323786690761986111
"""


def to_matrix(data: str) -> Generator[list[str]]:
	data = textwrap.dedent(data).strip()
	rows = data.split("\n")
	return (row.split("\t") for row in rows)


def main() -> None:
	os.chdir("parrot")
	subprocess.run(["alembic", "upgrade", V1_REVISION])

	engine = sm.create_engine(config.db_url)
	sm.SQLModel.metadata.create_all(engine)
	session = sm.Session(engine)

	logger.info("Injecting test data")

	for row in to_matrix(RAW_MESSAGES):
		try:
			timestamp = int(row[2])
		except ValueError:
			timestamp = row[2]
		session.add(
			v1.Messages(
				id=Snowflake(row[0]),
				user_id=Snowflake(row[1]),
				timestamp=timestamp,  # type: ignore
				content=row[3],
			)
		)

	session.add_all(
		v1.Channels(
			id=Snowflake(row[0]),
			can_speak_here=bool(row[1]),
			can_learn_here=bool(row[2]),
			webhook_id=None if row[3] == "None" else Snowflake(row[3]),
		)
		for row in to_matrix(RAW_CHANNELS)
	)

	session.add_all(
		v1.Guilds(
			id=Snowflake(row[0]),
			imitation_prefix="" if row[1] == "None" else row[1],
			imitation_suffix="" if row[2] == "None" else row[2],
		)
		for row in to_matrix(RAW_GUILDS)
	)

	session.add_all(
		v1.Users(
			id=Snowflake(row[0]),
			is_registered=bool(row[1]),
			original_avatar_url=row[2],
			modified_avatar_url=row[3],
			modified_avatar_message_id=Snowflake(row[4]),
		)
		for row in to_matrix(RAW_USERS)
	)

	session.commit()


if __name__ == "__main__":
	main()
