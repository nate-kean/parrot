from discord.ext import commands

import parrot.db.models as p
from parrot.bot import Parrot
from parrot.utils import ParrotEmbed, cast_not_none, checks, trace
from parrot.utils.types import LearnableChannel


class Admin(commands.Cog):
	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.group(
		name="channels",
		aliases=["channel", "learning"],
		invoke_without_command=True,
	)
	@commands.cooldown(2, 4, commands.BucketType.user)
	@trace
	async def channels_group(self, ctx: commands.Context) -> None:
		"""Manage Parrot's learning permissions for this server."""
		await self.channels_view(ctx)

	@channels_group.command(
		name="add",
		aliases=["enable"],
		brief="Let Parrot learn in a new channel.",
	)
	@commands.check(checks.is_admin)
	@trace
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
	@trace
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
	@trace
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

	@commands.group(name="prefix", invoke_without_command=True)
	@commands.guild_only()
	@commands.cooldown(2, 4, commands.BucketType.user)
	@trace
	async def prefix_group(self, ctx: commands.Context) -> None:
		"""Manage Parrot's imitation prefix for this server."""
		await self.prefix_get(ctx)

	@prefix_group.command(name="get")
	@trace
	async def prefix_get(self, ctx: commands.Context) -> None:
		# ctx.guild guaranteed not None because this command group is guild-only
		prefix = self.bot.crud.guild.get_prefix(cast_not_none(ctx.guild))
		await ctx.reply(f'Parrot\'s imitation prefix is: "{prefix}"')

	@prefix_group.command(name="set")
	@commands.check(checks.is_admin)
	@trace
	async def prefix_set(self, ctx: commands.Context, new_prefix: str) -> None:
		self.bot.crud.guild.set_prefix(cast_not_none(ctx.guild), new_prefix)
		await ctx.reply(f'✅ Parrot\'s imitation prefix is now: "{new_prefix}"')

	@prefix_group.command(name="reset", aliases=["default"])
	@commands.check(checks.is_admin)
	@trace
	async def prefix_reset(self, ctx: commands.Context) -> None:
		new_prefix = p.GuildMeta.default_imitation_prefix
		self.bot.crud.guild.set_prefix(cast_not_none(ctx.guild), new_prefix)
		await ctx.reply(
			f'✅ Parrot\'s imitation prefix has been reset to: "{new_prefix}"'
		)

	@commands.group(name="suffix", invoke_without_command=True)
	@commands.guild_only()
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def suffix_group(self, ctx: commands.Context) -> None:
		"""Manage Parrot's imitation suffix for this server."""
		await self.suffix_get(ctx)

	@suffix_group.command(name="get")
	@trace
	async def suffix_get(self, ctx: commands.Context) -> None:
		# ctx.guild guaranteed not None because this command group is guild-only
		suffix = self.bot.crud.guild.get_suffix(cast_not_none(ctx.guild))
		await ctx.reply(f'Parrot\'s imitation suffix is: "{suffix}"')

	@suffix_group.command(name="set")
	@commands.check(checks.is_admin)
	@trace
	async def suffix_set(self, ctx: commands.Context, new_suffix: str) -> None:
		self.bot.crud.guild.set_suffix(cast_not_none(ctx.guild), new_suffix)
		await ctx.reply(f'✅ Parrot\'s imitation suffix is now: "{new_suffix}"')

	@suffix_group.command(name="reset", aliases=["default"])
	@commands.check(checks.is_admin)
	@trace
	async def suffix_reset(self, ctx: commands.Context) -> None:
		new_suffix = p.GuildMeta.default_imitation_suffix
		self.bot.crud.guild.set_suffix(cast_not_none(ctx.guild), new_suffix)
		await ctx.reply(
			f'✅ Parrot\'s imitation suffix has been reset to: "{new_suffix}"'
		)


async def setup(bot: Parrot) -> None:
	await bot.add_cog(Admin(bot))
