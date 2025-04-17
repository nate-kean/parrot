from typing import TYPE_CHECKING

import discord
from discord import Forbidden, HTTPException, NotFound
from discord.ext import commands

from parrot.config import logger
from parrot.utils import cast_not_none, is_speakable, trace


if TYPE_CHECKING:
	from parrot.bot import Parrot


class WebhookManager:
	async def fetch(
		self,
		ctx: "commands.Context[Parrot]",
	) -> discord.Webhook | None:
		if not is_speakable(ctx.channel) or isinstance(
			ctx.channel, discord.Thread
		):
			return None

		# See if Parrot owns a webhook for this channel.
		webhook_id = ctx.bot.crud.channel.get_webhook_id(ctx.channel)
		if webhook_id is not None:
			try:
				# TODO: alru cache this
				return await ctx.bot.fetch_webhook(webhook_id)
			except NotFound:
				# Saved webhook ID is invalid; make a new one
				pass

		# Parrot does not have a webhook for this channel, so create one.
		try:
			parrots_avatar = await cast_not_none(
				ctx.bot.user
			).display_avatar.read()
			webhook = await ctx.channel.create_webhook(
				name=f"Parrot in #{ctx.channel.name}",
				avatar=parrots_avatar,
				reason="Automatically created by Parrot",
			)
			ctx.bot.crud.channel.set_webhook_id(ctx.channel, webhook)
			logger.info(f"{trace.format_context(ctx)}: Created new webhook")
			return webhook
		except (Forbidden, HTTPException, AttributeError):
			# - Forbidden: Parrot lacks permission to make webhooks here.
			# - AttributeError: Cannot make a webhook in this type of channel,
			#   like a DMChannel.
			# - HTTPException: 400 Bad Request; there is already the maximum
			#   number of webhooks allowed in this channel.
			return None
