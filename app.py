from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import os
import logging
import string
import sys
import discord

from discord.ext import commands


# set a few vars
root = logging.getLogger('bot')
LANGUAGE = "english"
SENTENCES_COUNT = 2
startup_extensions = ["Anime", "Pets", "Games", "Members", "Thirstyboi"]

bot = commands.Bot(
    command_prefix='!',
    description='A bot for gaming, and maybe anime?',
    pm_help=True
)

# https://regex101.com/r/SrVpEg/2
# some base classes


def main():
    # configure discord
    DISCORD_BOT_TOKEN = os.environ['DISCORD_BOT_TOKEN']

    # configure our logger
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)

    for extension in startup_extensions:
        try:
            bot.load_extension('cogs.'+extension)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, e)
            print('Failed to load extension {}\n{}'.format(extension, exc))

    bot.run(DISCORD_BOT_TOKEN)


@bot.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == bot.user:
        return

    await bot.change_presence(activity=discord.Game(name='RNG the Game'))

    # remove bot from message if included (in @botname scenario)
    if bot.user in message.mentions:
        directed = True
        AT_BOT = "<@" + bot.user.id + ">"
        plain_message = message.content[len(AT_BOT):]
    else:
        directed = False
        plain_message = message.content

    # simplify the message format
    plain_message = plain_message.lower().strip(string.whitespace)

    await bot.process_commands(message)


@bot.event
async def on_ready():
    root.info('Logged in as %s, id: %s', bot.user.name, bot.user.id)


@bot.event
async def on_server_join(server):
    root.info('Bot joined: %s', server.name)


@bot.event
async def on_server_remove(server):
    root.info('Bot left: %s', server.name)


@bot.event
async def on_command_completion(ctx):
    root.info('parsed command:%s', ctx.message.content)


@bot.command(pass_context=True)
async def killbot(ctx):
    print("Shutting down!")
    await bot.say("Shutting down.")
    await bot.close()


if __name__ == '__main__':
    main()
