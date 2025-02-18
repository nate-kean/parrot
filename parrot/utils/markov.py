import random
from collections.abc import Iterable, Sequence
from typing import Self, cast

import markovify

from parrot.utils import executor_function


class ParrotText(markovify.Text):
	def __init__(
		self,
		corpus: Iterable[str],
		# Unused in Parrot except to retain compatibility with markovify.combine
		parsed_sentences: list[list[str]] | None = None,
		state_size: int = 2,
		chain: markovify.Chain | None = None,
	):
		super().__init__(
			input_text=corpus,
			state_size=random.randint(1, 2),
			retain_original=False,
			well_formed=False,
			parsed_sentences=parsed_sentences,
			chain=chain,
		)

	@classmethod
	@executor_function
	def new(cls, corpus: Iterable[str]) -> Self:
		"""
		Construct the Markov chain generator in a new thread/process to remain
		non-blocking.
		"""
		return cls(corpus)

	def __len__(self):
		"""Approximate the memory size of the underlying model.

		Sums:
		- the size of each state
		- the size of each follow within each state
		- the size of the int value associated with each follow
		"""
		total = 0
		model = cast(dict[Sequence[str], dict[str, int]], self.chain.model)
		for state in model:
			for item in state:
				total += len(item)
			for follow in model[state]:
				total += len(follow)
			total += len(model[state]) * 4  # 4 bytes per int
		return total


class Gibberish(markovify.Text):
	"""
	Feed the corpus to the Markov model character-by-character instead of
	word-by-word for extra craziness!
	"""

	def __init__(self, text: str):
		super().__init__(
			None,
			parsed_sentences=[list(text)],
			state_size=random.randint(1, 2),
			retain_original=False,
			well_formed=False,
		)
		self.original = text

	@classmethod
	@executor_function
	def new(cls, text: str) -> Self:
		return cls(text)

	def word_join(self, words: list[str]) -> str:
		"""
		The generator usually puts spaces between each entry in the list
		because it expects them to be words. Since they're actually characters
		here, we join the list without spaces.
		I could be smarter about this and make it use a string instead of a
		list of strings, but I would have to modify markovify.Chain to do that
		and I don't want to!
		"""
		return "".join(words)

	def make_sentence(
		self, init_state: tuple[str, ...] | None = None, **kwargs: dict
	) -> str:
		"""
		Make some gibberish. If it ends up the same as the original text,
		maybe try again. But not always, because sometimes it's funny!
		"""
		while True:
			sentence = super().make_sentence(init_state=init_state, **kwargs)
			if sentence is not None and (
				sentence != self.original or random.random() < 0.2
			):
				return sentence
