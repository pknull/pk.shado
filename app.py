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

from discord.ext import commands

# Load environment variables from .env file
load_dotenv()

# set a few vars
root = logging.getLogger()
LANGUAGE = "english"
SENTENCES_COUNT = 2
cogs = ["Anime", "Games", "Greetings", "Members", "Passel", "Pets", "Thirstyboi", "CipherOracle"]


bot = commands.Bot(
    intents=discord.Intents.all(),
    command_prefix='!',
    description='A bot for gaming, and maybe anime?',
    pm_help=True
)

# https://regex101.com/r/SrVpEg/2
# some base classes

# configure our logger
root.setLevel(logging.WARN)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

# configure discord
DISCORD_BOT_TOKEN = os.environ['DISCORD_BOT_TOKEN']


async def load_extensions():
    for cog in cogs:
        print('Attempting to load extension ' + cog)
        try:
            await bot.load_extension("cogs." + cog)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, e)
            print('Failed to load extension {}\n{}'.format(cog, exc))
            print(traceback.format_exc())
            quit()

async def main():
    async with bot:
        await load_extensions()
        await bot.start(DISCORD_BOT_TOKEN)

@bot.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == bot.user:
        return

    await bot.process_commands(message)


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
    await ctx.send("Shutting down.")
    await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
