import asyncio
import logging
from pathlib import Path

import aiohttp
import asyncio_atexit
import discord
import sqlmodel as sm
from discord.ext import commands, tasks

from parrot import config
from parrot.db.crud import CRUD
from parrot.db.managers.antiavatar import AntiavatarManager
from parrot.db.managers.markov_model import MarkovModelManager
from parrot.db.managers.webhook import WebhookManager


class Parrot(commands.AutoShardedBot):
	def __init__(self):
		logging.info(f"discord.py {discord.__version__}")

		intents = discord.Intents.default()
		intents.message_content = True
		intents.members = True

		super().__init__(
			command_prefix=config.command_prefix,
			intents=intents,
			owner_ids=config.admin_user_ids,
			allowed_mentions=discord.AllowedMentions.none(),
			activity=discord.Activity(
				type=discord.ActivityType.listening,
				name=f"everyone ({config.command_prefix}help)",
			),
			case_insensitive=True,
		)
		self._db_session = sm.Session(sm.create_engine(config.db_url))
		self.crud = CRUD(self, self._db_session)
		self.markov_models = MarkovModelManager(self.crud)
		self.webhooks = WebhookManager()

	async def setup_hook(self) -> None:
		"""Constructor Part 2: Enter Async"""
		# Parrot has to do async stuff as part of its destructor, so it can't
		# actually use __del__, a method strictly synchronous. So we have to
		# reinvent a little bit of the wheel and manually set a function to run
		# when Parrot is about to be destroyed -- except slightly earlier, while
		# the event loop is still up.
		asyncio_atexit.register(self._async__del__, loop=self.loop)

		self.http_session = aiohttp.ClientSession(loop=self.loop)
		self._autosave.start()
		async with asyncio.TaskGroup() as tg:
			tg.create_task(self.load_extension("jishaku"))
			tg.create_task(self.load_extension_folder("commands"))
			tg.create_task(self.load_extension_folder("cogs"))

		self.antiavatars = await AntiavatarManager.new(self)

	async def _async__del__(self) -> None:
		logging.info("Parrot shutting down...")
		self._db_session.close()
		self._autosave.cancel()
		await self.close()  # Log out of Discord
		await self.http_session.close()
		await self._autosave()

	async def load_extension_folder(self, path: str) -> None:
		async with asyncio.TaskGroup() as tg:
			for entry in (Path("parrot") / path).iterdir():
				if not entry.is_file():
					continue
				if entry.name == "__init__.py":
					continue
				fqn = f"parrot.{path}.{entry.stem}"
				try:
					logging.info(f"Loading {fqn}... ")
					tg.create_task(self.load_extension(fqn))
					logging.info("✅")
				except Exception as error:
					logging.info("❌")
					logging.error(f"{error}\n")

	@tasks.loop(seconds=config.autosave_interval_seconds)
	async def _autosave(self) -> None:
		"""Commit the database on a timer.
		Far more performant than committing on every query."""
		logging.info("Saving to database...")
		self._db_session.commit()
		logging.info("Save complete.")

	def go(self) -> None:
		"""The next logical step after `start` and `run`"""
		self.run(config.discord_bot_token)
