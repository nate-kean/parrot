import discord


type AnyUser = discord.User | discord.Member | discord.ClientUser

type LearnableChannel = discord.TextChannel
type SpeakableChannel = discord.TextChannel | discord.Thread

# Type alias for Discord's favored Twitter Snowflake ints.
# Helps differentiate ints used as Snowflakes from ints used as anything else.
Snowflake = int  # can't call it a type though or sqlmodel gets mad
