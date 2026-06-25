import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher


_WORD = re.compile(r"[0-9a-z]+")


@dataclass(frozen=True)
class OriginMessage:
	id: int
	author_id: int
	content: str


@dataclass(frozen=True)
class OriginReport:
	phrase: str
	precursor: OriginMessage | None
	first_exact: OriginMessage | None
	descendants: tuple[OriginMessage, ...]
	custodian_ids: tuple[int, ...]


def normalize(text: str) -> str:
	"""Normalize text for mutation matching, not exact matching."""
	return "".join(_WORD.findall(text.casefold()))


def is_exact_match(phrase: str, content: str) -> bool:
	return _exact_pattern(phrase).search(content.casefold()) is not None


def mutation_score(phrase: str, content: str) -> float:
	phrase_norm = normalize(phrase)
	content_norm = normalize(content)
	if len(phrase_norm) == 0 or len(content_norm) == 0:
		return 0
	if phrase_norm in content_norm or content_norm in phrase_norm:
		return 1

	phrase_words = set(_WORD.findall(phrase.casefold()))
	content_words = set(_WORD.findall(content.casefold()))
	word_overlap = (
		len(phrase_words & content_words) / len(phrase_words | content_words)
		if len(phrase_words | content_words) > 0
		else 0
	)

	window_similarity = _best_window_similarity(phrase_norm, content_norm)
	return max(window_similarity, word_overlap)


def analyze_origin(
	phrase: str,
	messages: list[OriginMessage],
	*,
	min_score: float = 0.72,
	max_descendants: int = 3,
	max_custodians: int = 3,
) -> OriginReport:
	exact_pattern = _exact_pattern(phrase)
	ordered_messages = sorted(messages, key=lambda message: message.id)
	first_exact = next(
		(
			message
			for message in ordered_messages
			if exact_pattern.search(message.content.casefold()) is not None
		),
		None,
	)
	if first_exact is None:
		return OriginReport(
			phrase=phrase,
			precursor=_best_candidate(phrase, ordered_messages, min_score),
			first_exact=None,
			descendants=(),
			custodian_ids=(),
		)

	prior_messages = [
		message
		for message in ordered_messages
		if message.id < first_exact.id
		and exact_pattern.search(message.content.casefold()) is None
	]
	later_messages = [
		message
		for message in ordered_messages
		if message.id > first_exact.id
		and exact_pattern.search(message.content.casefold()) is None
	]
	descendants = _rank_candidates(
		phrase,
		later_messages,
		min_score,
	)[:max_descendants]

	custodian_counts: Counter[int] = Counter()
	for message in ordered_messages:
		if message.id < first_exact.id:
			continue
		if exact_pattern.search(message.content.casefold()) is not None:
			custodian_counts[message.author_id] += 1
		elif mutation_score(phrase, message.content) >= min_score:
			custodian_counts[message.author_id] += 1

	return OriginReport(
		phrase=phrase,
		precursor=_best_candidate(phrase, prior_messages, min_score),
		first_exact=first_exact,
		descendants=tuple(descendants),
		custodian_ids=tuple(
			author_id
			for author_id, _ in custodian_counts.most_common(max_custodians)
		),
	)


def _best_candidate(
	phrase: str,
	messages: list[OriginMessage],
	min_score: float,
) -> OriginMessage | None:
	ranked = _rank_candidates(phrase, messages, min_score)
	return ranked[0] if len(ranked) > 0 else None


def _rank_candidates(
	phrase: str,
	messages: list[OriginMessage],
	min_score: float,
) -> list[OriginMessage]:
	scored = [
		(mutation_score(phrase, message.content), message.id, message)
		for message in messages
	]
	scored = [
		(score, message_id, message)
		for score, message_id, message in scored
		if score >= min_score
	]
	scored.sort(key=lambda item: (-item[0], item[1]))
	return [message for _, _, message in scored]


def _exact_pattern(phrase: str) -> re.Pattern[str]:
	return re.compile(
		rf"(?<![0-9a-z]){re.escape(phrase.casefold())}(?![0-9a-z])"
	)


def _best_window_similarity(phrase: str, content: str) -> float:
	if len(content) <= len(phrase):
		return SequenceMatcher(None, phrase, content).ratio()

	window_width = max(len(phrase), 1)
	best = 0.0
	for start in range(0, len(content) - window_width + 1):
		window = content[start : start + window_width]
		best = max(best, SequenceMatcher(None, phrase, window).ratio())
	return best
