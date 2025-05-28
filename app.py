from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import os
import logging
import string
import sys
import discord
import asyncio
import traceback
from dotenv import load_dotenv

# Set up more detailed logging for debugging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler()])

# Create a single debug logger instance to be used throughout the application
debug_logger = logging.getLogger('debug')
debug_logger.setLevel(logging.DEBUG)
# Remove any existing handlers to prevent duplicate logs
for handler in debug_logger.handlers[:]:
    debug_logger.removeHandler(handler)
# Add a single handler
debug_logger.addHandler(logging.StreamHandler())
# Prevent propagation to the root logger to avoid duplicate logs
debug_logger.propagate = False

from discord.ext import commands

# Load environment variables from .env file
load_dotenv()

# set a few vars
root = logging.getLogger()
LANGUAGE = "english"
SENTENCES_COUNT = 2
cogs = ["Anime", "Games", "Greetings", "Members", "Passel", "Pets", "Thirstyboi", "CipherOracle", "Cleaner"]


bot = commands.Bot(
    intents=discord.Intents.all(),
    command_prefix='!',
    description='A bot for gaming, and maybe anime?',
    pm_help=True
)

# https://regex101.com/r/SrVpEg/2
# some base classes

# configure our logger
# Remove any existing handlers to prevent duplicate logs
for handler in root.handlers[:]:
    root.removeHandler(handler)
root.setLevel(logging.WARN)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

# configure discord
try:
    DISCORD_BOT_TOKEN = os.environ['DISCORD_BOT_TOKEN']
    debug_logger.info("Found DISCORD_BOT_TOKEN in environment variables")
except KeyError:
    debug_logger.error("DISCORD_BOT_TOKEN not found in environment variables")
    # For debugging purposes, set a dummy token
    DISCORD_BOT_TOKEN = "debug_token"
    debug_logger.warning("Using dummy token for debugging purposes")


async def load_extensions():
    for cog in cogs:
        debug_logger.info('Attempting to load extension %s', cog)
        try:
            debug_logger.debug('Loading extension path: cogs.%s', cog)
            await bot.load_extension("cogs." + cog)
            debug_logger.info('Successfully loaded extension %s', cog)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, e)
            debug_logger.error('Failed to load extension %s\n%s', cog, exc)
            debug_logger.error('Traceback: %s', traceback.format_exc())
            quit()

async def main():
    debug_logger.info("Starting bot initialization")
    try:
        debug_logger.info("Setting up bot context")
        async with bot:
            debug_logger.info("Loading extensions")
            await load_extensions()
            debug_logger.info("Starting bot with token")
            await bot.start(DISCORD_BOT_TOKEN)
    except Exception as e:
        debug_logger.error("Error in main function: %s", str(e))
        debug_logger.error("Traceback: %s", traceback.format_exc())
        raise

@bot.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == bot.user:
        return

    try:
        await bot.process_commands(message)
    except discord.NotFound:
        debug_logger.error("Message not found when processing commands.")
    except Exception as e:
        debug_logger.error("Unexpected error in on_message: %s", str(e))


@bot.event
async def on_ready():
    root.info('Logged in as %s, id: %s', bot.user.name, bot.user.id)
    await bot.change_presence(activity=discord.Game(name='RNG the Game'))


@bot.event
async def on_server_join(server):
    root.info('Bot joined: %s', server.name)


@bot.event
async def on_server_remove(server):
    root.info('Bot left: %s', server.name)

@bot.event
async def on_command_error(ctx , error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Command not found.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Missing required argument.')
    elif isinstance(error, (commands.MissingPermissions, discord.Forbidden)):
        await ctx.send('You do not have permission to use this command.')
    else:
        logging.error('An error occurred: %s', str(error))
        await ctx.send('Something went wrong. Please try again later.')

@bot.event
async def on_command_completion(ctx):
    root.info('parsed command:%s', ctx.message.content)

@bot.command(pass_context=True)
async def killbot(ctx):
    print("Shutting down!")
    try:
        await ctx.send("Shutting down.")
    except discord.HTTPException as e:
        debug_logger.error("Failed to send shutdown message: %s", str(e))
    await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
