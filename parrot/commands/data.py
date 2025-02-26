import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from tempfile import TemporaryFile
from typing import Any, cast

import discord
import ujson
from discord.ext import commands

from parrot.bot import Parrot
from parrot.utils import (
	ParrotEmbed,
	cast_not_none,
	checks,
	tag,
)
from parrot.utils.converters import Memberlike, Userlike
from parrot.utils.exceptions import (
	NoDataError,
	UserPermissionError,
)
from parrot.utils.trace import trace
from parrot.utils.types import Snowflake


type UserOrMember = discord.User | discord.Member

# Key: Message ID of a forget command
type ConfirmationStore = dict[Snowflake, Data.Confirmation]


@trace
class Data(commands.Cog):
	"""Do things w/ ur data"""

	@dataclass
	class Confirmation:
		requestor: UserOrMember  # The forget command message's author
		subject_user: UserOrMember  # User for whose data to be forgotten

	def __init__(self, bot: Parrot):
		self.bot = bot
		self.pending_full_confirmations: ConfirmationStore = {}
		self.pending_guild_confirmations: ConfirmationStore = {}

	@commands.command(aliases=["checkout", "data"])
	@commands.cooldown(2, 3600, commands.BucketType.user)
	async def download(self, ctx: commands.Context) -> None:
		"""Download a copy of your data."""
		user = ctx.author

		# Upload to file.io, a free filesharing service where the file is
		# deleted once it's downloaded.
		# We can't trust that it will fit in a Discord message.
		# TODO: Use a better service, like a self-hosted Pastebin.
		with TemporaryFile("w+", encoding="utf-8") as f:
			ujson.dump(self.bot.crud.user.get_raw(user), f)
			f.seek(0)  # Prepare the file to be read back over
			async with self.bot.http_session.post(
				"https://file.io/", data={"file": f, "expiry": "6h"}
			) as response:
				download_url = (await response.json())["link"]

		# DM the user their download link.
		embed_download_link = ParrotEmbed(
			title="Link to download your data",
			description=download_url,
		)
		embed_download_link.set_footer(text="Link expires in 6 hours.")
		# No need to wait
		asyncio.create_task(user.send(embed=embed_download_link))

		# Tell them to check their DMs.
		embed_download_ready = ParrotEmbed(
			title="Download ready",
			color=ParrotEmbed.Color.GREEN,
			description="A link to download your data has been DM'd to you.",
		)
		await ctx.reply(embed=embed_download_ready)

	@commands.command(aliases=["pfp", "profilepic", "profilepicture"])
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def avatar(
		self,
		ctx: commands.Context,
		who: Memberlike | None = None,
	) -> None:
		"""Show your Imitate Clone's avatar."""
		who = who or cast(discord.Member, ctx.author)
		avatar_url = await self.bot.antiavatars.fetch(who)
		await ctx.reply(avatar_url)

	async def _start_forget(
		self,
		/,
		ctx: commands.Context,
		*,
		who: UserOrMember | None,
		confirmation_store: ConfirmationStore,
		are_you_sure_message_fmt: str,
	) -> None:
		who = who or ctx.author

		if who != ctx.author and not checks.is_admin(ctx) and not who.bot:
			raise UserPermissionError(
				"You are not allowed to make Parrot forget other users."
			)

		if not self.bot.crud.user.exists(who):
			raise NoDataError(f"No data available for user {tag(who)}.")

		confirm_code = ctx.message.id

		# Keep track of this confirmation while it's still pending.
		confirmation_store[confirm_code] = Data.Confirmation(
			requestor=ctx.author,
			subject_user=who,
		)

		embed = ParrotEmbed(
			title="Are you sure?",
			color=ParrotEmbed.Color.ORANGE,
			description=are_you_sure_message_fmt.format(
				who=who.mention,
				confirm_code=confirm_code,
			),
		).set_footer(text="Action will be automatically canceled in 1 minute.")
		sent_message = await ctx.reply(embed=embed)

		# Delete the confirmation after 1 minute.
		await asyncio.sleep(60)
		try:
			del confirmation_store[confirm_code]
		except KeyError:
			pass
		embed.description = "Request expired."
		await sent_message.edit(embed=embed)

	async def _confirm_forget(
		self,
		/,
		ctx: commands.Context,
		*,
		confirmation_store: ConfirmationStore,
		done_message: str,
		confirm_code: Snowflake | None,
		action: Callable[[UserOrMember], Coroutine[Any, Any, Any]],
	) -> None:
		if confirm_code is None:
			await ctx.reply("Error: confirmation code is missing.")
			return

		# You'd think that since this argument is typed as an int, it would come
		# in as an int. But noooo, it comes in as a string
		confirm_code = Snowflake(confirm_code)
		confirmation = confirmation_store.get(confirm_code, None)

		if confirmation is not None and confirmation.requestor == ctx.author:
			user = confirmation.subject_user

			# Perform the destructive action.
			await action(user)

			# Invalidate this confirmation code.
			del confirmation_store[confirm_code]

			embed = ParrotEmbed(
				title=f"Parrot has forgotten {tag(user)}.",
				color=ParrotEmbed.Color.GRAY,
				description=done_message,
			)
			await ctx.reply(embed=embed)
		else:
			await ctx.reply(f"Confirmation code `{confirm_code}` is invalid.")

	@commands.group(name="forget", invoke_without_command=True)
	async def forget_group(self, ctx: commands.Context) -> None:
		await ctx.send_help(self.forget_group)

	@forget_group.group(name="everywhere", invoke_without_command=True)
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def forget_everywhere(
		self,
		ctx: commands.Context,
		who: Userlike | None = None,
	) -> None:
		"""Delete ALL your data from Parrot."""
		are_you_sure_message_fmt = (
			"This will permanently delete the data of {who} from Parrot.\n"
			f"`{self.bot.command_prefix}"
			f"{self.forget_everywhere_confirm.qualified_name} {{confirm_code}}`"
		)
		await self._start_forget(
			ctx,
			who=who,
			confirmation_store=self.pending_full_confirmations,
			are_you_sure_message_fmt=are_you_sure_message_fmt,
		)

	@forget_everywhere.command(name="confirm", hidden=True)
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def forget_everywhere_confirm(
		self,
		ctx: commands.Context,
		confirm_code: int,
	) -> None:
		done_message = (
			"All of the data that Parrot has collected from this "
			"user has been deleted."
		)
		await self._confirm_forget(
			ctx,
			confirmation_store=self.pending_full_confirmations,
			confirm_code=confirm_code,
			action=self.bot.crud.user.delete_all_data,
			done_message=done_message,
		)

	@forget_group.group(name="here", invoke_without_command=True)
	@commands.cooldown(2, 4, commands.BucketType.user)
	@commands.guild_only()
	async def forget_here(
		self,
		ctx: commands.Context,
		who: Userlike | None = None,
	) -> None:
		"""Delete your messages in this server."""
		are_you_sure_message_fmt = (
			"This will permanently delete the messages collected from {who} "
			f"in server {cast_not_none(ctx.guild).name}.\n"
			"To confirm, paste the following command:\n"
			f"`{self.bot.command_prefix}"
			f"{self.forget_here_confirm.qualified_name} {{confirm_code}}`"
		)
		await self._start_forget(
			ctx,
			who=who,
			confirmation_store=self.pending_guild_confirmations,
			are_you_sure_message_fmt=are_you_sure_message_fmt,
		)

	@forget_here.command(name="confirm", hidden=True)
	@commands.cooldown(2, 4, commands.BucketType.user)
	@commands.guild_only()
	async def forget_here_confirm(
		self,
		ctx: commands.Context,
		confirm_code: int | None = None,
	) -> None:
		done_message = (
			"All of the messages that Parrot has collected from this "
			"user in this server have been deleted."
		)
		# Will only ever receive Members because this command is guild-only.
		# Casting just to satisfy, uh, my own API, that I made...
		member_leave_guild = cast(
			Callable[[UserOrMember], Coroutine[Any, Any, bool]],
			self.bot.crud.member.leave,
		)
		await self._confirm_forget(
			ctx,
			confirmation_store=self.pending_guild_confirmations,
			confirm_code=confirm_code,
			action=member_leave_guild,
			done_message=done_message,
		)


async def setup(bot: Parrot) -> None:
	await bot.add_cog(Data(bot))
