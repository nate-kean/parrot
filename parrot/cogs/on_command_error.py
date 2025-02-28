import random
import traceback

from discord.ext import commands
from discord.ext.commands.errors import (
	CommandError,
	CommandInvokeError,
	CommandNotFound,
)

import parrot.assets
from parrot.bot import Parrot
from parrot.config import logger
from parrot.utils import ParrotEmbed
from parrot.utils.exceptions import FriendlyError


class CommandErrorHandler(commands.Cog):
	@commands.Cog.listener()
	async def on_command_error(
		self, ctx: commands.Context, error: CommandError
	) -> None:
		# Ignore Command Not Found errors
		if isinstance(error, CommandNotFound):
			return

		if isinstance(error, CommandInvokeError) and isinstance(
			error.original, FriendlyError
		):
			# Prettify Friendly Error text
			name = error.original.__class__.__name__
			error_text = f"{name}: {error.original}"
			notes = "\n".join(error.original.__notes__)
			if len(notes) > 0:
				error_text += "\n" + notes
			# Don't log Friendly Errors
		else:
			# Log all other kinds of errors (REAL errors)
			error_text = str(error)
			logger.error(
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
		await ctx.reply(embed=embed)


async def setup(bot: Parrot) -> None:
	await bot.add_cog(CommandErrorHandler())
