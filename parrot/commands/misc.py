from discord.ext import commands

from parrot.bot import Parrot
from parrot.utils import ParrotEmbed, cast_not_none, tag
from parrot.utils.trace import trace


@trace
class Miscellaneous(commands.Cog):
	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.command()
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def ping(self, ctx: commands.Context) -> None:
		"""Get the bot's reponse time."""
		await ctx.reply(
			f"NEED PING??? Took **{round(self.bot.latency * 1000, 2)}** ms"
		)

	@commands.command(
		aliases=["about", "bio", "code", "github", "source", "sourcecode"]
	)
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def info(self, ctx: commands.Context) -> None:
		"""Get info about Parrot."""
		garlic_os = await self.bot.fetch_user(206235904644349953)

		bio = (
			f"Parrot can imitate everyone. "
			f"Do `{self.bot.command_prefix}imitate me` to have Parrot imitate "
			f"you, or do `{self.bot.command_prefix}help` to see what else "
			"Parrot can do."
		)

		embed = ParrotEmbed(
			title="🦜 Parrot",
			description=bio,
		)
		embed.add_field(
			name="GitHub",
			value="https://github.com/garlic-os/parrot",
		)
		embed.set_thumbnail(url=cast_not_none(self.bot.user).display_avatar.url)
		embed.set_footer(
			text=f"Parrot v4 • Made by {tag(garlic_os)}",
			icon_url=garlic_os.display_avatar.url,
		)

		await ctx.reply(embed=embed)


async def setup(bot: Parrot) -> None:
	await bot.add_cog(Miscellaneous(bot))
