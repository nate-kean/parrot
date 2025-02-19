import discord


type AnyUser = discord.User | discord.Member | discord.ClientUser

# In quotes because MessageableChannel is only available during type checking.
# String not divided to fit into 80 cols because Python doesn't support divided
# strings when they're types.
type AnyChannel = "discord.abc.MessageableChannel | discord.abc.GuildChannel | discord.abc.PrivateChannel"
type LearnableChannel = discord.TextChannel
type SpeakableChannel = discord.TextChannel | discord.Thread

# Type alias for Discord's favored Twitter Snowflake ints.
# Helps differentiate ints used as Snowflakes from ints used as anything else.
Snowflake = int  # can't call it a type though or sqlmodel gets mad
