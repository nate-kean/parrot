import logging
import random
import traceback

from discord.ext import commands
from discord.ext.commands.errors import CommandError, CommandNotFound

import parrot.assets
from parrot.bot import Parrot
from parrot.utils import ParrotEmbed


class ErrorHandler(commands.Cog):
	@commands.Cog.listener()
	async def on_command_error(
		self, ctx: commands.Context, error: CommandError
	) -> None:
		# Ignore Command Not Found errors
		if isinstance(error, CommandNotFound):
			return

		if str(error.__cause__).startswith("Friendly Error: "):
			# Don't log Friendly Errors; display their text directly
			error_text = str(error.__cause__)[16:]
		else:
			# Log all other kinds of errors (REAL errors)
			error_text = str(error)
			logging.error(
				"\n".join(
					traceback.format_exception(None, error, error.__traceback__)
				)
			)

		# Send the error message to the channel it came from
		embed = ParrotEmbed(
			title=random.choice(parrot.assets.failure_phrases),
			description=error_text,
			color=ParrotEmbed.Color.RED,
		)
		await ctx.send(embed=embed, reference=ctx.message)


async def setup(bot: Parrot) -> None:
	await bot.add_cog(ErrorHandler())
