from discord.ext import commands

import parrot.db.models as p
from parrot.bot import Parrot

# from parrot.utils import Paginator, ParrotEmbed, cast_not_none, checks, tag
from parrot.utils import (
	ParrotEmbed,
	cast_not_none,
	checks,
	send_help,
	tag,
	trace,
)
from parrot.utils.types import LearnableChannel


class Admin(commands.Cog):
	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.command()
	@commands.check(checks.is_admin)
	@commands.cooldown(2, 4, commands.BucketType.user)
	@trace
	async def delete(self, ctx: commands.Context, message_id: int) -> None:
		"""Delete a message that Parrot sent (including imitation messages)."""
		message = await ctx.fetch_message(message_id)
		guild = ctx.guild
		me = guild.me if guild is not None else self.bot.user
		if message.webhook_id is None:
			author = message.author
		else:
			webhook = await self.bot.fetch_webhook(message.webhook_id)
			author = webhook.user
		if author == me:
			await message.delete()
			await ctx.message.add_reaction("✅")
		else:
			await ctx.send("❌ Parrot can only delete its own messages.")
			await ctx.message.add_reaction("❌")

	@commands.group(
		aliases=["channels", "learning"],
		invoke_without_command=True,
	)
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def channel(
		self,
		ctx: commands.Context,
		action: str | None = None,
		channel: LearnableChannel | None = None,
	) -> None:
		"""Manage Parrot's learning permissions for this server."""
		if action is None:
			await send_help(ctx)

	@channel.command(
		aliases=["enable"],
		brief="Let Parrot learn in a new channel.",
	)
	@commands.check(checks.is_admin)
	@trace
	async def add(
		self,
		ctx: commands.Context,
		channel: LearnableChannel,
	) -> None:
		"""
		Give Parrot permission to learn in a new channel.
		Parrot will start to collect messages from registered users in this
		channel.
		"""
		changed = self.bot.crud.channel.set_can_learn_here(channel, True)
		if changed:
			await ctx.send(f"✅ Now learning in {channel.mention}.")
		else:
			await ctx.send(f"⚠️️ Already learning in {channel.mention}!")

	@channel.command(
		aliases=["disable", "delete"],
		brief="Remove Parrot's learning permission in a channel.",
	)
	@commands.check(checks.is_admin)
	@trace
	async def remove(
		self,
		ctx: commands.Context,
		channel: LearnableChannel,
	) -> None:
		"""
		Remove Parrot's permission to learn in a channel.
		Parrot will stop collecting messages in this channel.
		"""
		changed = self.bot.crud.channel.set_can_learn_here(channel, False)
		if changed:
			await ctx.send(f"❌ No longer learning in {channel.mention}.")
		else:
			await ctx.send(f"⚠️️ Already not learning in {channel.mention}!")

	@channel.command(name="learning")
	@trace
	async def view(
		self,
		ctx: commands.Context,
		guild_id: int | None = None,
	) -> None:
		raise NotImplementedError(
			"This command is out of order while pagination still hasn't been "
			"reimplemented"
		)
		failure_message = (
			"Parrot can't speak in DMs. Try passing in a guild ID."
		)
		if guild_id is None:
			if ctx.guild is None:
				await ctx.send(failure_message)
				return
			guild_id = ctx.guild.id
		guild = self.bot.get_guild(guild_id)
		if guild is None:
			await ctx.send(failure_message)
			return

		ids = self.bot.crud.guild.get_learning_channel_ids(guild)
		channel_mentions = [c.mention for c in guild.channels if c.id in ids]

		embed = ParrotEmbed(title="Parrot is learning from these channels:")
		if len(channel_mentions) == 0:
			embed.description = "None"
			await ctx.send(embed=embed)
			return

		# TODO
		# paginator = Paginator.FromList(
		# 	ctx,
		# 	entries=channel_mentions,
		# 	template_embed=embed,
		# )
		# await paginator.run()

	@commands.group(invoke_without_command=True)
	@commands.cooldown(2, 4, commands.BucketType.user)
	@commands.check(checks.is_admin)
	@trace
	async def nickname(
		self, ctx: commands.Context, action: str | None = None
	) -> None:
		"""Manage Parrot's nickname for this server."""
		if action is None:
			await send_help(ctx)

	@nickname.command(name="set")
	@trace
	async def nickname_set(
		self, ctx: commands.Context, *, new_nick: str | None = None
	) -> None:
		"""Change Parrot's nickname."""
		if new_nick is None:
			await send_help(ctx)
			return
		if ctx.guild is None:
			await ctx.send("Discord nicknames are only available in servers.")
			return

		await ctx.guild.me.edit(
			nick=new_nick,
			reason=f"Requested by {tag(ctx.author)}",
		)
		await ctx.send(f"✅ Parrot's nickname is now: {ctx.guild.me.nick}")

	@nickname.command(name="remove", aliases=["delete"])
	@trace
	async def nickname_remove(self, ctx: commands.Context) -> None:
		"""Get rid of Parrot's nickname."""
		if ctx.guild is None:
			await ctx.send("Discord nicknames are only available in servers.")
			return
		await ctx.guild.me.edit(
			nick=None,
			reason=f"Requested by {tag(ctx.author)}",
		)
		await ctx.send("✅ Parrot's nickname has been removed.")

	@commands.group(invoke_without_command=True)
	@commands.guild_only()
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def prefix(
		self,
		ctx: commands.Context,
		action: str | None = None,
		new_prefix: str | None = None,
	) -> None:
		"""Manage Parrot's imitation prefix for this server."""
		if action is not None and action != "get":
			await send_help(ctx)
			return
		await self.prefix_get(ctx)

	@prefix.command()
	@trace
	async def prefix_get(self, ctx: commands.Context) -> None:
		# ctx.guild guaranteed not None because this command group is guild-only
		prefix = self.bot.crud.guild.get_prefix(cast_not_none(ctx.guild))
		await ctx.send(f"Parrot's imitation prefix is: `{prefix}`")

	@prefix.command()
	@commands.check(checks.is_admin)
	@trace
	async def prefix_set(self, ctx: commands.Context, new_prefix: str) -> None:
		self.bot.crud.guild.set_prefix(cast_not_none(ctx.guild), new_prefix)
		await ctx.send(f"✅ Parrot's imitation prefix is now: `{new_prefix}`")

	@prefix.command(aliases=["reset", "default"])
	@commands.check(checks.is_admin)
	@trace
	async def prefix_clear(self, ctx: commands.Context) -> None:
		new_prefix = p.GuildMeta.default_imitation_prefix
		self.bot.crud.guild.set_prefix(cast_not_none(ctx.guild), new_prefix)
		await ctx.send(
			f"✅ Parrot's imitation prefix has been reset to: `{new_prefix}`"
		)

	@commands.group(invoke_without_command=True)
	@commands.guild_only()
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def suffix(
		self,
		ctx: commands.Context,
		action: str | None = None,
		new_suffix: str | None = None,
	) -> None:
		"""Manage Parrot's imitation suffix for this server."""
		if action is not None and action != "get":
			await send_help(ctx)
			return
		await self.suffix_get(ctx)

	@suffix.command()
	@trace
	async def suffix_get(self, ctx: commands.Context) -> None:
		# ctx.guild guaranteed not None because this command group is guild-only
		suffix = self.bot.crud.guild.get_suffix(cast_not_none(ctx.guild))
		await ctx.send(f"Parrot's imitation suffix is: `{suffix}`")

	@suffix.command()
	@commands.check(checks.is_admin)
	@trace
	async def suffix_set(self, ctx: commands.Context, new_suffix: str) -> None:
		self.bot.crud.guild.set_suffix(cast_not_none(ctx.guild), new_suffix)
		await ctx.send(f"✅ Parrot's imitation suffix is now: `{new_suffix}`")

	@suffix.command(aliases=["reset", "default"])
	@commands.check(checks.is_admin)
	@trace
	async def suffix_clear(self, ctx: commands.Context) -> None:
		new_suffix = p.GuildMeta.default_imitation_suffix
		self.bot.crud.guild.set_suffix(cast_not_none(ctx.guild), new_suffix)
		await ctx.send(
			f"✅ Parrot's imitation suffix has been reset to: `{new_suffix}`"
		)


async def setup(bot: Parrot) -> None:
	await bot.add_cog(Admin(bot))
