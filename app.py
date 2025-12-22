import os
import logging
import string
import sys
import discord
import asyncio
import traceback
from dotenv import load_dotenv
from discord.ext import commands

# Load environment variables from .env file
load_dotenv()

# Configure logging once with unified settings
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Create a single debug logger instance to be used throughout the application
debug_logger = logging.getLogger('debug')
debug_logger.setLevel(logging.DEBUG)
debug_logger.propagate = False

# Root logger for general app logging
root = logging.getLogger()
root.setLevel(logging.WARN)
LANGUAGE = "english"
SENTENCES_COUNT = 2
cogs = [
    "AAS",
    "Anime",
    "Astrologer",
    "Games",
    "Greetings",
    "Members",
    "Passel",
    "Pets",
    "Thirstyboi",
    "CipherOracle",
    "Cleaner",
    "Weather",
    "Reminders",
    "Meme",
]


bot = commands.Bot(
    intents=discord.Intents.all(),
    command_prefix='!',
    description='A bot for gaming, and maybe anime?',
    pm_help=True
)

# configure discord
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
if not DISCORD_BOT_TOKEN:
    debug_logger.error("DISCORD_BOT_TOKEN not found in environment variables")
    debug_logger.error("Set DISCORD_BOT_TOKEN in .env file or environment")
    sys.exit(1)
debug_logger.info("DISCORD_BOT_TOKEN configured")


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
            sys.exit(1)

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
async def on_command_error(ctx, error):
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
    debug_logger.info("Shutting down!")
    try:
        await ctx.send("Shutting down.")
    except discord.HTTPException as e:
        debug_logger.error("Failed to send shutdown message: %s", str(e))

    # Clean up resources
    try:
        from cogs.Utils import close_http_session
        await close_http_session()
        debug_logger.info("HTTP session closed successfully")
    except Exception as e:
        debug_logger.error("Error closing HTTP session: %s", str(e))

    await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
