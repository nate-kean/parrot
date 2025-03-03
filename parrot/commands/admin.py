from typing import cast

import discord
from discord.ext import commands

import parrot.db.models as p
from parrot.bot import Parrot
from parrot.utils import ParrotEmbed, cast_not_none, checks
from parrot.utils.trace import trace
from parrot.utils.types import LearnableChannel


@trace
class Admin(commands.Cog):
	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.group(
		name="channels",
		aliases=["channel", "learning"],
		invoke_without_command=True,
	)
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def channels_group(self, ctx: commands.Context) -> None:
		"""Manage Parrot's learning permissions for this server."""
		await self.channels_view(ctx)

	@channels_group.command(
		name="add",
		aliases=["enable"],
		brief="Let Parrot learn in a new channel.",
	)
	@commands.check(checks.is_admin)
	async def channels_add(
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
			await ctx.reply(f"✅ Now learning in {channel.mention}.")
		else:
			await ctx.reply(f"⚠️️ Already learning in {channel.mention}!")

	@channels_group.command(
		name="remove",
		aliases=["disable", "delete"],
		brief="Remove Parrot's learning permission in a channel.",
	)
	@commands.check(checks.is_admin)
	async def channels_remove(
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
			await ctx.reply(f"❌ No longer learning in {channel.mention}.")
		else:
			await ctx.reply(f"⚠️️ Already not learning in {channel.mention}!")

	@channels_group.command(name="view", aliases=["list"])
	async def channels_view(
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
				await ctx.reply(failure_message)
				return
			guild_id = ctx.guild.id
		guild = self.bot.get_guild(guild_id)
		if guild is None:
			await ctx.reply(failure_message)
			return

		ids = self.bot.crud.guild.get_learning_channel_ids(guild)
		channel_mentions = [c.mention for c in guild.channels if c.id in ids]

		embed = ParrotEmbed(title="Parrot is learning from these channels:")
		if len(channel_mentions) == 0:
			embed.description = "None"
			await ctx.reply(embed=embed)
			return

		# TODO
		# paginator = Paginator.FromList(
		# 	ctx,
		# 	entries=channel_mentions,
		# 	template_embed=embed,
		# )
		# await paginator.run()

	# region Guild affixes
	@commands.group(name="prefix", invoke_without_command=True)
	@commands.guild_only()
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def prefix_group(self, ctx: commands.Context) -> None:
		"""Manage Parrot's imitation prefix for this server."""
		await self.prefix_get(ctx)

	@prefix_group.command(name="get")
	async def prefix_get(self, ctx: commands.Context) -> None:
		# ctx.guild guaranteed not None because this command group is guild-only
		prefix = self.bot.crud.guild.get_prefix(cast_not_none(ctx.guild))
		await ctx.reply(
			f'This server\'s default imitation prefix is: "{prefix}"'
		)

	@prefix_group.command(name="set")
	@commands.check(checks.is_admin)
	async def prefix_set(self, ctx: commands.Context, new_prefix: str) -> None:
		self.bot.crud.guild.set_prefix(cast_not_none(ctx.guild), new_prefix)
		await ctx.reply(
			f'✅ This server\'s default imitation prefix is now: "{new_prefix}"'
		)

	@prefix_group.command(name="reset", aliases=["default"])
	@commands.check(checks.is_admin)
	async def prefix_reset(self, ctx: commands.Context) -> None:
		new_prefix = p.GuildMeta.default_imitation_prefix
		self.bot.crud.guild.set_prefix(cast_not_none(ctx.guild), new_prefix)
		await ctx.reply(
			f'✅ This server\'s default imitation prefix has been reset to: "{new_prefix}"'
		)

	@commands.group(name="suffix", invoke_without_command=True)
	@commands.guild_only()
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def suffix_group(self, ctx: commands.Context) -> None:
		"""Manage Parrot's imitation suffix for this server."""
		await self.suffix_get(ctx)

	@suffix_group.command(name="get")
	async def suffix_get(self, ctx: commands.Context) -> None:
		# ctx.guild guaranteed not None because this command group is guild-only
		suffix = self.bot.crud.guild.get_suffix(cast_not_none(ctx.guild))
		await ctx.reply(
			f'This server\'s default imitation suffix is: "{suffix}"'
		)

	@suffix_group.command(name="set")
	@commands.check(checks.is_admin)
	async def suffix_set(self, ctx: commands.Context, new_suffix: str) -> None:
		self.bot.crud.guild.set_suffix(cast_not_none(ctx.guild), new_suffix)
		await ctx.reply(
			f'✅ This server\'s default imitation suffix is now: "{new_suffix}"'
		)

	@suffix_group.command(name="reset", aliases=["default"])
	@commands.check(checks.is_admin)
	async def suffix_reset(self, ctx: commands.Context) -> None:
		new_suffix = p.GuildMeta.default_imitation_suffix
		self.bot.crud.guild.set_suffix(cast_not_none(ctx.guild), new_suffix)
		await ctx.reply(
			f'✅ This server\'s default imitation suffix has been reset to: "{new_suffix}"'
		)

	# endregion

	# region Member affixes
	@commands.group(name="customprefix", invoke_without_command=True)
	@commands.guild_only()
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def custom_prefix_group(self, ctx: commands.Context) -> None:
		"""Manage your custom imitation prefix for this server."""
		await self.custom_prefix_get(ctx)

	@custom_prefix_group.command(name="get")
	async def custom_prefix_get(self, ctx: commands.Context) -> None:
		# Author is guaranteed Member because this command group is guild-only
		prefix = self.bot.crud.member.get_custom_prefix(
			cast(discord.Member, ctx.author)
		)
		await ctx.reply(f'Your custom imitation prefix is: "{prefix}"')

	@custom_prefix_group.command(name="set")
	@commands.check(checks.is_admin)
	async def custom_prefix_set(
		self,
		ctx: commands.Context,
		new_prefix: str,
	) -> None:
		self.bot.crud.member.set_custom_prefix(
			cast(discord.Member, ctx.author), new_prefix
		)
		await ctx.reply(
			f'✅ Your custom imitation prefix is now: "{new_prefix}"'
		)

	@custom_prefix_group.command(name="reset", aliases=["default", "clear"])
	@commands.check(checks.is_admin)
	async def custom_prefix_reset(self, ctx: commands.Context) -> None:
		self.bot.crud.member.set_custom_prefix(
			cast(discord.Member, ctx.author), None
		)
		await ctx.reply("✅ Your imitation prefix has been cleared")

	@commands.group(name="customsuffix", invoke_without_command=True)
	@commands.guild_only()
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def custom_suffix_group(self, ctx: commands.Context) -> None:
		"""Manage your imitation suffix for this server."""
		await self.custom_suffix_get(ctx)

	@custom_suffix_group.command(name="get")
	async def custom_suffix_get(self, ctx: commands.Context) -> None:
		# ctx.guild guaranteed not None because this command group is guild-only
		suffix = self.bot.crud.member.get_custom_suffix(
			cast(discord.Member, ctx.author)
		)
		await ctx.reply(f'Your imitation suffix is: "{suffix}"')

	@custom_suffix_group.command(name="set")
	@commands.check(checks.is_admin)
	async def custom_suffix_set(
		self,
		ctx: commands.Context,
		new_suffix: str,
	) -> None:
		self.bot.crud.member.set_custom_suffix(
			cast(discord.Member, ctx.author), new_suffix
		)
		await ctx.reply(f'✅ Your imitation suffix is now: "{new_suffix}"')

	@custom_suffix_group.command(name="reset", aliases=["default", "clear"])
	@commands.check(checks.is_admin)
	async def custom_suffix_reset(self, ctx: commands.Context) -> None:
		self.bot.crud.member.set_custom_suffix(
			cast(discord.Member, ctx.author), None
		)
		await ctx.reply("✅ Your imitation suffix has been cleared")

	# endregion


async def setup(bot: Parrot) -> None:
	await bot.add_cog(Admin(bot))
