import datetime as dt
import logging

import discord

from parrot.utils.types import Snowflake


discord_bot_token: str

# Put either this or "@parrot " before a command
command_prefix: str = "|"

db_url: str = "sqlite:////var/lib/parrot/db.sqlite3"

# Seconds between database commits
autosave_interval_seconds: int = 3600

# How long to hold messages in a guild after the author has left the guild they
# posted them in.
# Gathering messages is a lot of work so this is protection against people who
# leave and come back after like one day
message_retention_period_seconds: int = int(
	dt.timedelta(days=90).total_seconds()
)

# Allow the cache of generated models to take up to this much space in
# memory
markov_cache_size_bytes: int = 1 * 1024 * 1024 * 1024  # 1 GB

admin_user_ids: set[Snowflake] = set()
# admin_user_ids: set[Snowflake] = {
# 	206235904644349953,  # @garlic_os
# }

admin_role_ids: set[Snowflake] = set()

# Discord channel where Parrot caches antiavatars
avatar_store_channel_id: Snowflake

# Random probability on [0, 1] to reply to a message with its content
# filtered through `weasel.wawa`
random_wawa_chance: float = 0.005

# Time to allow a text modification command (which is liable to run forever) to
# run before canceling it
modify_text_timeout_seconds: int = 5

ayy_lmao: bool = True


class image:
	max_filesize_bytes: int = discord.utils.DEFAULT_FILE_SIZE_LIMIT_BYTES
	max_frames: int = 300


class CustomFormatter(logging.Formatter):
	grey = "\x1b[38;21m"
	yellow = "\x1b[33;21m"
	red = "\x1b[31;21m"
	bold_red = "\x1b[31;1m"
	reset = "\x1b[0m"
	format_str = "%(levelname)s - %(message)s"

	FORMATS = {
		logging.DEBUG: grey + format_str + reset,
		logging.INFO: grey + format_str + reset,
		logging.WARNING: yellow + format_str + reset,
		logging.ERROR: red + format_str + reset,
		logging.CRITICAL: bold_red + format_str + reset,
	}

	def format(self, record: logging.LogRecord) -> str:
		log_fmt = self.FORMATS.get(record.levelno)
		formatter = logging.Formatter(log_fmt)
		return formatter.format(record)


ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())

logger = logging.getLogger("Parrot")
logger.setLevel(logging.DEBUG)
logger.addHandler(ch)
