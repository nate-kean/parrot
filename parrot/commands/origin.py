import datetime as dt
from typing import cast

import discord
from discord.ext import commands

from parrot import origin, utils
from parrot.bot import Parrot
from parrot.utils.exceptions import TextNotFound
from parrot.utils.trace import trace


@trace
class Origin(commands.Cog):
	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.command(
		brief="Find where a phrase started and how it mutated.",
	)
	@commands.guild_only()
	@commands.cooldown(1, 20, commands.BucketType.guild)
	async def origin(self, ctx: commands.Context, *, phrase: str = "") -> None:
		"""Find the earliest known appearance of a phrase."""
		phrase = await self._resolve_phrase(ctx, phrase)
		guild = cast(discord.Guild, ctx.guild)

		messages = self.bot.crud.message.origin_messages(guild)
		report = origin.analyze_origin(phrase, messages)
		await ctx.reply(
			self._format_report(guild, report),
			allowed_mentions=discord.AllowedMentions.none(),
		)

	async def _resolve_phrase(
		self,
		ctx: commands.Context,
		phrase: str,
	) -> str:
		phrase = phrase.strip()
		if len(phrase) > 0:
			return phrase

		if (
			ctx.message.reference is None
			or ctx.message.reference.message_id is None
		):
			raise TextNotFound(
				"Give me a phrase, or reply to a message with `|origin`."
			)

		reference_message = await ctx.channel.fetch_message(
			ctx.message.reference.message_id
		)
		phrase = utils.find_text(reference_message, accept_own_commands=True)
		if phrase is None:
			raise TextNotFound("That message doesn't have any text!")
		phrase = phrase.strip()
		if len(phrase) == 0:
			raise TextNotFound("That message doesn't have any text!")
		return phrase

	def _format_report(
		self,
		guild: discord.Guild,
		report: origin.OriginReport,
	) -> str:
		lines = [
			self._quote(report.phrase, limit=180),
			"",
		]

		if report.precursor is None:
			lines.append("Precursor: none found")
		else:
			lines.append(
				"Precursor: "
				f"{self._quote(report.precursor.content)} - "
				f"{self._author_name(guild, report.precursor.author_id)}, "
				f"{self._format_time(report.precursor.id)}"
			)

		if report.first_exact is None:
			lines.extend(
				[
					"First exact use: none found",
					"Descendants: none found",
					"Current custodians: none yet",
				]
			)
			return "\n".join(lines)[:2000]

		first_exact_origin = self._author_name(
			guild,
			report.first_exact.author_id,
		)
		if report.precursor is None:
			first_exact_origin += f", {self._format_time(report.first_exact.id)}"
		else:
			first_exact_origin += (
				f", {self._format_delta(report.precursor.id, report.first_exact.id)}"
				" later"
			)
		lines.append(f"First exact use: {first_exact_origin}")

		if len(report.descendants) == 0:
			lines.append("Descendants: none found")
		else:
			lines.append(
				"Likely descendants: "
				+ ", ".join(
					self._quote(message.content, limit=80)
					for message in report.descendants
				)
			)

		if len(report.custodian_ids) == 0:
			lines.append("Current custodians: none yet")
		else:
			lines.append(
				"Current custodians: "
				+ ", ".join(
					self._author_name(guild, author_id)
					for author_id in report.custodian_ids
				)
			)

		return "\n".join(lines)[:2000]

	def _author_name(self, guild: discord.Guild, author_id: int) -> str:
		member = guild.get_member(author_id)
		if member is not None:
			return member.display_name
		user = self.bot.get_user(author_id)
		if user is not None:
			return utils.tag(user)
		return f"<@{author_id}>"

	@staticmethod
	def _quote(text: str, *, limit: int = 120) -> str:
		text = " ".join(text.split())
		if len(text) > limit:
			text = text[: limit - 3].rstrip() + "..."
		return f'"{text}"'

	@staticmethod
	def _format_time(message_id: int) -> str:
		created_at = discord.utils.snowflake_time(message_id).astimezone()
		return created_at.strftime("%I:%M %p").lstrip("0")

	@staticmethod
	def _format_delta(first_id: int, second_id: int) -> str:
		first_at = discord.utils.snowflake_time(first_id)
		second_at = discord.utils.snowflake_time(second_id)
		delta = second_at - first_at
		return _format_timedelta(delta)


def _format_timedelta(delta: dt.timedelta) -> str:
	seconds = max(0, int(delta.total_seconds()))
	if seconds < 60:
		return _plural(seconds, "second")
	minutes = seconds // 60
	if minutes < 60:
		return _plural(minutes, "minute")
	hours = minutes // 60
	if hours < 24:
		return _plural(hours, "hour")
	days = hours // 24
	return _plural(days, "day")


def _plural(amount: int, unit: str) -> str:
	if amount == 1:
		return f"1 {unit}"
	return f"{amount} {unit}s"


async def setup(bot: Parrot) -> None:
	await bot.add_cog(Origin(bot))
