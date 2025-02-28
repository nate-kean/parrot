"""
quickstart.py

One of the most complex and stateful parts of Parrot.
Here be dragons
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import Enum, auto
from typing import cast

import asyncio_atexit
import discord
from discord.ext import commands

from parrot.bot import Parrot
from parrot.utils import (
	HistoryCrawler,
	ParrotEmbed,
	checks,
	is_learnable,
)
from parrot.utils.converters import Userlike
from parrot.utils.exceptions import (
	AlreadyScanning,
	UserMissingPermissions,
	WrongChannelType,
)
from parrot.utils.trace import trace
from parrot.utils.types import Snowflake


class CancelReason(Enum):
	USER = auto()
	SYSTEM = auto()


@dataclass
class Scan:
	member_id: Snowflake
	guild_id: Snowflake
	status_message: discord.Message
	status_fmt: str
	dm_embed: discord.Embed
	crawler: HistoryCrawler
	cancel_reason: CancelReason | None = None


# Key is status message DM ID
type OngoingScans = dict[Snowflake, Scan]


@trace
class Quickstart(commands.Cog):
	def __init__(self, bot: Parrot):
		self.bot = bot
		# Keep track of Quickstart scans that are currently happening.
		self.ongoing_scans: OngoingScans = {}
		# Using asyncio_atexit even though this method isn't async, because
		# status updates Parrot/Quickstart has to send out because of what it
		# does _are_ async
		asyncio_atexit.register(self._cancel_all, loop=self.bot.loop)

	@commands.Cog.listener()
	async def on_raw_reaction_add(
		self,
		payload: discord.RawReactionActionEvent,
	) -> None:
		if payload.emoji.name != "❌":
			return
		scan_id = payload.message_id
		if scan_id not in self.ongoing_scans:
			return
		self._cancel_scan(scan_id, CancelReason.USER)

	@staticmethod
	async def _live_update_status(scan: Scan) -> None:
		while scan.crawler.running:
			scan.dm_embed.description = scan.status_fmt.format(
				num_collected=scan.crawler.num_collected
			)
			await scan.status_message.edit(embed=scan.dm_embed)
			await asyncio.sleep(2)

	@commands.command()
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def quickstart(
		self,
		ctx: commands.Context,
		user: Userlike | None = None,
	) -> None:
		"""
		Scrape your past messages in this server to get started using Parrot
		right away.
		"""
		# region Get member
		if not is_learnable(ctx.channel) or ctx.guild is None:
			raise WrongChannelType("Quickstart is only available in servers.")
		member = cast(discord.Member | None, user)
		if member is None or ctx.author == member:
			member = cast(discord.Member, ctx.author)
		else:
			if not checks.is_admin(ctx):
				raise UserMissingPermissions(
					"You can only run Quickstart on yourself."
				)
			if not member.bot:
				raise UserMissingPermissions(
					"Quickstart can only be run on behalf of bots."
				)
		self.bot.crud.member.assert_registered(member)
		# endregion

		# region Validate scan
		# You can only run one Quickstart scan in a guild at a time.
		for scan in self.ongoing_scans.values():
			if scan.member_id == member.id and scan.guild_id == member.guild.id:
				name = "you" if ctx.author.id == member.id else member.mention
				raise AlreadyScanning(
					f"❌ Quickstart is already running for {name} in this "
					"server!"
				)
		# endregion

		# try-except so we can clear this scan status in case anything
		# goes wrong (and this cog has a long history of things going wrong)
		scan_id: Snowflake | None = None
		try:
			# region Init status DM
			# Create an embed that will show the status of the Quickstart
			# operation and DM it to the user who invoked the command.
			status_fmt = (
				f"**Scanning in _{member.guild.name}_...**\n"
				"Collected {num_collected} new messages..."
			)
			dm_embed = ParrotEmbed(
				description=status_fmt.format(num_collected=0)
			)
			dm_embed.set_author(
				name="Quickstart",
				icon_url="https://i.gifer.com/ZZ5H.gif",  # Loading spinner
			)
			dm_embed.set_footer(
				text=f"Scanning for {member.mention}",
				icon_url=member.display_avatar.url,
			)
			status_message = await ctx.author.send(embed=dm_embed)
			scan_id = status_message.id

			# Add "cancel" emoji. Click event handled in this Cog's reaction
			# event handler.
			await status_message.add_reaction("❌")

			# Send a confirmation in the chat that the scan has started.
			whose = (
				"your" if ctx.author.id == member.id else f"{member.mention}'s"
			)
			chat_embed = ParrotEmbed(
				title="Quickstart is scanning",
				description=(
					"Parrot is now scanning this server and learning from "
					f"{whose} past messages.\nThis could take a few minutes."
					"\nCheck your DMs to see its progress."
				),
			)
			await ctx.reply(embed=chat_embed)
			# endregion

			# region Init crawler
			# Create an iterator representing up to 100,000 messages since the
			# user joined the server.
			histories: list[AsyncIterator[discord.Message]] = []
			learning_channel_ids = self.bot.crud.guild.get_learning_channel_ids(
				ctx.guild
			)
			for channel_id in learning_channel_ids:
				channel = await self.bot.fetch_channel(channel_id)
				if not is_learnable(channel):
					continue
				try:
					member = await channel.guild.fetch_member(member.id)
				except discord.errors.NotFound:
					continue
				histories.append(
					channel.history(
						limit=100_000,
						after=member.joined_at,
					)
				)

			# Create an object that will scan through the server's message
			# history and learn from the messages this user has posted.
			crawler = HistoryCrawler(
				histories=histories,
				action=self.bot.crud.message.record_or_update,
				filter=lambda message: message.author.id == member.id,
				limit=100_000,
			)
			# endregion

			# region Main
			# In parallel, start the crawler and periodically update the
			# status_message with its progress.
			scan = Scan(
				member_id=member.id,
				guild_id=member.guild.id,
				status_message=status_message,
				status_fmt=status_fmt,
				dm_embed=dm_embed,
				crawler=crawler,
			)
			self.ongoing_scans[scan_id] = scan
			async with asyncio.TaskGroup() as tg:
				tg.create_task(Quickstart._live_update_status(scan))
				tg.create_task(crawler.crawl())
			# endregion

			# region Finish
			# Update the status embed one last time, but DELETE it this time and
			# post a brand new one so that the user gets a new notification
			# (and to remove the "cancel" emoji).
			dm_embed = ParrotEmbed()
			if ctx.author == member:
				name = "you"
			else:
				name = f"{member.mention}"
				dm_embed.set_footer(
					text=(
						f"Scanning for {member.display_name} in "
						f"_{member.guild.name}_"
					),
					icon_url=member.display_avatar.url,
				)
			if scan.cancel_reason is not None:
				dm_embed.description = (
					"**Scan cancelled.**\n"
					f"Collected {crawler.num_collected} new messages."
				)
				if scan.cancel_reason == CancelReason.SYSTEM:
					dm_embed.description += (
						"\nCancelled by system: Parrot is restarting"
					)
				dm_embed.set_author(name="🛑 Quickstart")
			else:
				dm_embed.description = (
					"**Scan complete.**\n"
					f"Collected {crawler.num_collected} new messages."
				)
				dm_embed.set_author(name="✅ Quickstart")
			if crawler.num_collected == 0:
				dm_embed.description += (
					# type: ignore  -- embed.description is definitely not None
					f"\n😕 Couldn't find any messages from {name}."
				)
				dm_embed.color = ParrotEmbed.Color.RED.value
			if scan.cancel_reason is not None:
				dm_embed.color = ParrotEmbed.Color.GRAY.value

			async with asyncio.TaskGroup() as tg:
				tg.create_task(status_message.delete())
				tg.create_task(ctx.author.send(embed=dm_embed))
			del self.ongoing_scans[status_message.id]
			# endregion
		except:  # noqa -- we really do want to catch ANY error
			if scan_id is not None and scan_id in self.ongoing_scans:
				del self.ongoing_scans[scan_id]
			raise

	def _cancel_scan(self, scan_id: Snowflake, reason: CancelReason) -> None:
		scan = self.ongoing_scans[scan_id]
		scan.cancel_reason = reason
		scan.crawler.stop()

	def _cancel_all(self) -> None:
		for scan_id in self.ongoing_scans:
			self._cancel_scan(scan_id, CancelReason.SYSTEM)


async def setup(bot: Parrot) -> None:
	await bot.add_cog(Quickstart(bot))
