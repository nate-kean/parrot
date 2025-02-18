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
		key: MarkovModelManager.Key = (member.id, member.guild.id)
		if member.id in self.cache:
			logging.debug(f"Cache hit: {member.name}")
			self.cache.move_to_end(member.id)
			return self.cache[key]
		logging.debug(f"Cache miss: {member.id}")
		corpus = self.crud.member.get_messages_content(member)
		result = await markov.ParrotText.new(corpus)
		while self.space_used + len(result) > MarkovModelManager.MAX_MEM_SIZE:
			evicted: markov.ParrotText = self.cache.popitem(last=False)[1]
			logging.debug(
				" ** Full "
				f"({self.space_used}/{MarkovModelManager.MAX_MEM_SIZE}); "
				f"evicting: {evicted} (-{len(evicted)})"
			)
			self.space_used -= len(evicted)
		self.cache[key] = result
		self.space_used += len(result)
		return result

	async def update(
		self, member: discord.Member, corpus_update: Iterable[str]
	) -> None:
		"""Update a local model in the cache. Does not affect the database."""
		partial = markov.ParrotText(corpus_update)
		current = await self.fetch(member)
		# Returns same type as first element of first argument
		updated = cast(markov.ParrotText, markovify.combine((current, partial)))
		key: MarkovModelManager.Key = (member.id, member.guild.id)
		self.cache[key] = updated
