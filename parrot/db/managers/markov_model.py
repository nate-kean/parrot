import asyncio
import logging
from collections.abc import Iterable
from typing import cast

import discord
import markovify

from parrot import config
from parrot.db.crud import CRUD
from parrot.utils import LastUpdatedOrderedDict, markov
from parrot.utils.types import Snowflake


class MarkovModelManager:
	# A user-id, guild-id pair to uniquely identify a guild membership
	type Key = tuple[Snowflake, Snowflake]
	MAX_MEM_SIZE = config.markov_cache_size_bytes

	def __init__(self, crud: CRUD):
		self.crud = crud
		self.space_used = 0
		self.cache = LastUpdatedOrderedDict[
			MarkovModelManager.Key, markov.ParrotText
		]()

	async def fetch(self, member: discord.Member) -> markov.ParrotText:
		self.crud.member.assert_registered(member)
		key: MarkovModelManager.Key = (member.id, member.guild.id)
		# Fetch this model from the cache if it's there
		if key in self.cache:
			logging.debug(f"Cache hit: {key}")
			# Mark this model as most recently used (and so new last in line to
			# be evicted)
			self.cache.move_to_end(key)
			return self.cache[key]
		logging.debug(f"Cache miss: {key}")
		corpus = self.crud.member.get_messages_content(member)
		new_model = await markov.ParrotText.new(corpus)
		# Evict until we have enough space for the new model
		while (
			self.space_used + len(new_model) > MarkovModelManager.MAX_MEM_SIZE
		):
			evicted: markov.ParrotText = self.cache.popitem(last=False)[1]
			logging.debug(
				" ** Full "
				f"({self.space_used}/{MarkovModelManager.MAX_MEM_SIZE}); "
				f"evicting: {evicted} (-{len(evicted)})"
			)
			self.space_used -= len(evicted)
		self.cache[key] = new_model
		self.space_used += len(new_model)
		return new_model

	async def update(
		self,
		member: discord.Member,
		corpus_update: Iterable[str],
	) -> None:
		"""Update a local model in the cache. Does not affect the database."""
		async with asyncio.TaskGroup() as tg:
			task_partial = tg.create_task(markov.ParrotText.new(corpus_update))
			task_current = tg.create_task(self.fetch(member))
		partial = task_partial.result()
		current = task_current.result()
		# Returns same class as first element of first argument
		updated = cast(markov.ParrotText, markovify.combine((current, partial)))
		key: MarkovModelManager.Key = (member.id, member.guild.id)
		self.cache[key] = updated
