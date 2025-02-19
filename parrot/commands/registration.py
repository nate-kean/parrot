from typing import cast

import discord
from discord.ext import commands

from parrot.bot import Parrot
from parrot.utils import ParrotEmbed, trace
from parrot.utils.converters import Userlike
from parrot.utils.exceptions import UserPermissionError


class Registration(commands.Cog):
	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.command(
		aliases=["agree", "accept", "initiate", "initate"],
		brief="Register with Parrot.",
	)
	@commands.cooldown(2, 4, commands.BucketType.user)
	@commands.guild_only()
	@trace
	async def register(
		self, ctx: commands.Context, who: Userlike | None = None
	) -> None:
		"""Register to let Parrot imitate you."""
		# Pylance doesn't get along with `commands.Converter`s
		who_ = cast(discord.Member | None, who)
		if who_ is None:
			who_ = cast(discord.Member, ctx.author)
		elif who_.id != ctx.author.id:
			raise UserPermissionError("You can only register yourself.")

		# Update the "is_registered" field on this user in the database.
		self.bot.crud.member.set_registered(who_, True)

		embed = ParrotEmbed(
			title="✅ Registered!",
			color=ParrotEmbed.Color.GREEN,
			description=(
				"Now Parrot can start learning your speech patterns and "
				"imitate you."
			),
		)
		embed.add_field(
			name="Tip:",
			value=(
				f"Try the `{self.bot.command_prefix}quickstart` command to "
				"immediately give Parrot a dataset to imitate you from! It "
				"will scan your past messages to create a model of how you "
				"speak so you can start using Parrot right away."
			),
		)

		await ctx.send(embed=embed)

	@commands.command(
		aliases=["disagree", "unaccept", "uninitiate", "uninitate"],
		brief="Unregister with Parrot.",
	)
	@commands.cooldown(2, 4, commands.BucketType.user)
	@commands.guild_only()
	@trace
	async def unregister(
		self, ctx: commands.Context, who: Userlike | None = None
	) -> None:
		"""
		Remove your registration from Parrot.
		Parrot will stop collecting your messages and will not be able to
		imitate you until you register again.
		"""
		who_ = cast(discord.Member | None, who)
		if who_ is None:
			who_ = cast(discord.Member, ctx.author)
		elif who_.id != ctx.author.id:
			raise UserPermissionError("You can only unregister yourself.")

		self.bot.crud.member.set_registered(who_, False)

		embed = ParrotEmbed(
			title="Unregistered!",
			color=ParrotEmbed.Color.GRAY,
			description=(
				"Parrot will no longer be able to imitate you and it "
				"has stopped collecting your messages.\n\n_If you're done with "
				"Parrot and don't want it to have your messages anymore, or if "
				"you just want a fresh start, you can do "
				f"`{self.bot.command_prefix}forget me` and your existing data "
				"will be permanently deleted from Parrot._"
			),
		)

		await ctx.send(embed=embed)

	@commands.command(
		aliases=[
			"registrationstatus",
			"registration",
			"checkregistration",
			"checkregistered",
			"registered",
			"amiregistered",
		],
		brief="Check if you're registered with Parrot.",
	)
	@commands.cooldown(2, 4, commands.BucketType.user)
	@commands.guild_only()
	@trace
	async def status(
		self, ctx: commands.Context, who: Userlike | None = None
	) -> None:
		"""
		Check if you're registered with Parrot.
		You need to be registered for Parrot to be able to analyze your messages
		and imitate you.
		"""
		who_ = cast(discord.Member | None, who)
		if who_ is None:
			who_ = cast(discord.Member, ctx.author)
		subject_verb = (
			"You are" if who_.id == ctx.author.id else f"{who_.mention} is"
		)
		if who_.bot:
			await ctx.send("✅ Bots do not need to be registered.")
			return
		if self.bot.crud.member.is_registered(who_):
			await ctx.send(
				f"✅ {subject_verb} currently registered with Parrot."
			)
		else:
			await ctx.send(
				f"❌ {subject_verb} not currently registered with Parrot."
			)

	@commands.command(
		name="togglerandomwawa",
		brief="Un/block Parrot from randomly doing |wawa on you.",
	)
	@commands.cooldown(2, 4, commands.BucketType.user)
	@trace
	async def toggle_random_wawa(self, ctx: commands.Context) -> None:
		wants = self.bot.crud.user.toggle_random_wawa(ctx.author)
		await ctx.send(f"✅ Random wawa {'en' if wants else 'dis'}abled")


async def setup(bot: Parrot) -> None:
	await bot.add_cog(Registration(bot))
