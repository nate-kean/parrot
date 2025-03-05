import random
from collections.abc import Callable


type Predicate = Callable[[str], bool]

VOWELS = "AEIOU"
CONSONANTS = "BCDFGHJKLMNPQRSTVWXYZ"
CONSONANTS = CONSONANTS + CONSONANTS.lower()
VOWELS = VOWELS + VOWELS.lower()


def is_vowel(letter: str) -> bool:
	return letter in VOWELS


def is_const(letter: str) -> bool:
	return letter in CONSONANTS


def find_syllables(word: str) -> list[str]:
	"""
	A rudimentary syllable splitter for English words.
	For making wawas more interesting than random.
	https://stackoverflow.com/a/69803624
	"""
	split_points: list[int] = []
	patterns: list[list[Predicate]] = [
		[is_vowel, is_const, is_vowel],
		[is_const, is_vowel, is_const],
	]
	segment_length = len(patterns[0])

	# Find where the pattern occurs
	for i in range(len(word) - segment_length):
		segment = word[i : i + segment_length]
		if any(
			[
				all([pred(letter) for letter, pred in zip(segment, pattern)])
				for pattern in patterns
			]
		):
			split_points.append(i + segment_length // 2)

	# Use the index to find the syllables - add 0 and len(word) to make it work
	split_points.insert(0, 0)
	split_points.append(len(word))
	syllables: list[str] = []
	for i in range(len(split_points) - 1):
		start = split_points[i]
		end = split_points[i + 1]
		syllables.append(word[start:end])
	return syllables


# Async just because the rest of the text algorithms are
async def wawa(text: str) -> str:
	if "wawa" in text:
		return "wawa"
	for _ in range(10):
		syls = (find_syllables(word) for word in text.split(" "))
		syls_flat: list[str] = []
		for syl in syls:
			syls_flat.extend(syl)
			syls_flat.append(" ")
		samples = min(random.randint(1, 3), len(syls_flat))
		start_index = random.randint(0, len(syls_flat) - samples)
		result = "".join(syls_flat[start_index : start_index + samples])
		if len(result) > 0:
			return result
	return "\u200b"  # zero width space to send an "empty" message
