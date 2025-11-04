# Stdlib imports
import datetime
import json
import asyncio
import logging

# Third party and local imports
from .Utils import *
from discord.ext import commands

logger = logging.getLogger('thirstyboi')

class UserData:
    '''Class to handle user preferences.'''

    def __init__(self, guild=None, channel=None):
        '''
        :guild I believe this is the server. This is proably not needed
        :channel The channal which the user has commands sent to
        '''
        self.dm = False
        self.pause = True
        self.drink_break = datetime.timedelta(seconds=3600)
        self.last_drink = datetime.datetime.now()
        self.total = 0
        self.guild = guild
        self.channel = channel
        self.reminded = False

    def can_dm(self):
        '''Setter for dm.'''
        return self.dm
    
    def paused(self):
        '''Turn off dm.'''
        return self.pause

    def toggle_dm(self):
        '''Toggle the current status of dm.'''
        self.dm = not self.dm

    def toggle_pause(self):
        '''Toggle the current status of pause.'''
        self.pause = not self.pause

    def drink(self):
        '''Congrats! you drank water. Imagine living.'''
        self.last_drink = datetime.datetime.now()
        self.total += 1
        self.reminded = False

    def next_drink(self) -> int:
        '''Return when the user should drink next.'''
        return self.last_drink + self.drink_break

    def should_drink(self) -> bool:
        '''Return bool if user should drink or not.'''
        return datetime.datetime.now() >= self.next_drink()
    
    def times_drunk(self) -> int:
        '''Return the user's total times drank water.'''
        return self.total

    def set_break(self, time):
        '''Manually set the drink break.'''
        self.drink_break = time

    def update_channel(self, guild, channel):
        """Update the channel and the GUID of the user."""
        self.guild = guild
        self.channel = channel

    def was_reminded(self):
        '''Check if the user was reminded.'''
        return self.reminded

    def remind(self):
        '''We have reminded the user. Set to true.'''
        self.reminded = True

class Thirst(commands.Cog):
    """Help the thirsty bois quench their thirst!"""

    def __init__(self, bot, users, allowed_chan):
        '''Initialize with the bot object.'''
        # Store object vars
        self.bot = bot
        self.users = users
        self.allowed_chan = allowed_chan

        # Self set params
        self.interval = 69

        # Begin background task since object is loaded
        self.bot.loop.create_task(self.autosave())

    def _check_channel_permissions(self, ctx):
        """Check if command is allowed in this channel/DM. Returns (is_dm, is_allowed)."""
        is_dm = ctx.guild is None
        if not is_dm:
            # Check if guild is in allowed channels
            if ctx.guild.id not in self.allowed_chan:
                logger.debug(f"Command not allowed - guild {ctx.guild.id} not in allowed channels")
                return is_dm, False
            # Check if channel is in allowed channels for this guild
            if ctx.channel.id not in self.allowed_chan[ctx.guild.id]:
                logger.debug(f"Command not allowed - channel {ctx.channel.id} not in allowed channels for guild {ctx.guild.id}")
                return is_dm, False
        return is_dm, True

    def _get_or_create_user(self, ctx):
        """Get existing user or create new UserData for the author."""
        user_id = ctx.author.id
        if user_id in self.users:
            return self.users[user_id]

        # Create new user
        is_dm = ctx.guild is None
        if not is_dm:
            user = UserData(ctx.guild.id, ctx.channel.id)
        else:
            user = UserData(None, ctx.channel.id)

        self.users[user_id] = user
        return user

    async def autosave(self):
        '''Auto save the bot information in the background on interval.'''
        while not self.bot.is_closed():
            dat_export(self.users, self.allowed_chan)
            await asyncio.sleep(self.interval)

    async def remind(self, user: int):
        '''Setup to remind specific user.'''
        # Create user struct
        user_data: UserData = self.users[user]
        # Check if their time is less than time now
        if user_data.next_drink() < datetime.datetime.now():
            return
        # ONce here, its time to set remind timer
        # Fix timer
        time = user_data.next_drink() - datetime.datetime.now()
        # Sleep it and wait
        await asyncio.sleep(time.seconds + time.days*24*60*60)
        if not (user_data.paused() or user_data.was_reminded()):
            await self.bot.get_channel(user_data.channel).send("Remember to stay hydrated <@%i>!" % user)
            user_data.remind()

    @commands.command(name="sip", pass_context=True, brief="Tells the bot you've hydrated yourself.")
    async def sip(self, ctx: commands.Context, *time):
        '''Tells the bot you've hydrated yourself'''
        # Check permissions
        dm, is_allowed = self._check_channel_permissions(ctx)
        if not is_allowed:
            return

        # Get or create user
        user = self._get_or_create_user(ctx)

        # Check if the user has previous time, then reset (time is a passed in param)
        if time.__len__() > 0:
            time = read_timedelta(list(time))
        else:
            time = user.drink_break

        # If the user is paused then just yeet
        if user.paused():
            await self.stop(ctx)

        # Check if the user wants dbs or not
        if (dm and user.can_dm()) or not dm:
            if not dm:
                user.update_channel(ctx.guild.id, ctx.channel.id)
            else:
                user.update_channel(None, ctx.channel.id)
            user.set_break(time)
            user.drink()
            time = user.next_drink() - datetime.datetime.now()
            await ctx.send("Great! I will remind you to drink again in %s" % neat_timedelta(time))
        else:
            await ctx.send("You have not enabled direct messages. Enable them with ``!dmme`` first")
            return
        await self.remind(ctx.author.id)


    @commands.command(name="total", pass_context=True, brief="Displays how many times you have drank water.")
    async def total(self, ctx: commands.Context):
        '''Tells the user how many times they have drank.'''
        # Check permissions
        dm, is_allowed = self._check_channel_permissions(ctx)
        if not is_allowed:
            return

        # Get or create user
        user = self._get_or_create_user(ctx)

        if user.paused():
            await self.stop(ctx)

        if (dm and user.can_dm()) or not dm:
            await ctx.send("In total you've drank %i times" % user.times_drunk())
        else:
            await ctx.send("You have not enabled direct messages. Enable them with ``!dmme`` first")
            return

    @commands.command(name="stop", pass_context=True)
    async def stop(self, ctx: commands.Context):
        '''Stops the bot from sending users messages.'''
        # Check permissions
        dm, is_allowed = self._check_channel_permissions(ctx)
        if not is_allowed:
            return

        # Get or create user
        user = self._get_or_create_user(ctx)

        if (dm and user.can_dm()) or not dm:
            user.toggle_pause()
            if user.paused():
                await ctx.send("I will stop messaging you")
            else:
                await ctx.send("I will resume messaging you")

    @commands.command(name="dmme", pass_context=True)
    async def dmme(self, ctx: commands.Context):
        '''Start the bot sending messages to a user.'''
        # Check permissions
        dm, is_allowed = self._check_channel_permissions(ctx)
        if not is_allowed:
            return

        # Get or create user
        user = self._get_or_create_user(ctx)

        if user.paused():
            await self.stop(ctx)

        user.toggle_dm()
        if user.can_dm():
            await ctx.send("I will now be able to send you direct messages")
        else:
            await ctx.send("I will no longer be able to send you direct messages")

    @commands.command(name="allow_c", pass_context=True)
    @commands.has_permissions(manage_channels=True)
    async def allow_c(self, ctx: commands.Context):
        '''Allows editors or modorators of channels to toggle this option on channel.'''
        guild = ctx.guild.id
        channel = ctx.channel.id
        if guild in self.allowed_chan.keys():
            if channel in self.allowed_chan[guild]:
                self.allowed_chan.get(guild).remove(channel)
                await ctx.send("Removed <#%i> from the list of allowed channels" % channel)
            else:
                self.allowed_chan.get(guild).add(channel)
                await ctx.send("Added <#%i> to the list of allowed channels" % channel)
        else:
            self.allowed_chan[guild] = {channel}
            await ctx.send("Added <#%i> to the list of allowed channels" % channel)

def dat_export(usrdat, allwchan, filename: str = "data/thirstyboi_data.json"):
    """Export data to JSON file."""
    import os
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Convert UserData objects to dictionaries and datetime objects to ISO strings
    user_data_dict = {}
    for user_id, user_obj in usrdat.items():
        user_data_dict[str(user_id)] = {
            'dm': user_obj.dm,
            'pause': user_obj.pause,
            'drink_break_seconds': user_obj.drink_break.total_seconds(),
            'last_drink': user_obj.last_drink.isoformat(),
            'total': user_obj.total,
            'guild': user_obj.guild,
            'channel': user_obj.channel,
            'reminded': user_obj.reminded
        }

    # Convert set to list for JSON serialization
    allowed_chan_dict = {}
    for guild_id, channel_set in allwchan.items():
        allowed_chan_dict[str(guild_id)] = list(channel_set)

    data = {
        'users': user_data_dict,
        'allowed_channels': allowed_chan_dict
    }

    with open(filename, 'w') as fp:
        json.dump(data, fp, indent=2)

def dat_import(filename: str = "data/thirstyboi_data.json"):
    """Import data from JSON file."""
    try:
        with open(filename, 'r') as fp:
            data = json.load(fp)

        # Convert dictionaries back to UserData objects
        users = {}
        for user_id_str, user_dict in data.get('users', {}).items():
            user = UserData(
                guild=user_dict.get('guild'),
                channel=user_dict.get('channel')
            )
            user.dm = user_dict.get('dm', False)
            user.pause = user_dict.get('pause', True)
            user.drink_break = datetime.timedelta(seconds=user_dict.get('drink_break_seconds', 3600))
            user.last_drink = datetime.datetime.fromisoformat(user_dict.get('last_drink'))
            user.total = user_dict.get('total', 0)
            user.reminded = user_dict.get('reminded', False)
            users[int(user_id_str)] = user

        # Convert list back to set
        allowed_chan = {}
        for guild_id_str, channel_list in data.get('allowed_channels', {}).items():
            allowed_chan[int(guild_id_str)] = set(channel_list)

        return users, allowed_chan

    except FileNotFoundError:
        logger.info("No existing thirstyboi data file found, starting fresh")
        return {}, {}
    except Exception as e:
        logger.error(f"Error loading thirstyboi data: {e}")
        return {}, {}

async def setup(bot):
    '''Return the cog object for thirsty boi.'''
    # Init local vars
    users = None
    allowed_chan = None
    
    # Attempt to read in user data
    try:
        users, allowed_chan = dat_import()
    except:
        # If pickle or read fail, somethings fucked, just remake it
        users = dict()
        allowed_chan = dict()

        # Export it out so the file exists
        dat_export(users, allowed_chan)

    await bot.add_cog(Thirst(bot, users, allowed_chan))

############ Pretty formatting utilities ################
def read_timedelta(args: list):
    keys = ["D", "M", "S", "H"]
    units = {key: 0 for key in keys}
    for arg in args:
        units[arg[-1:].upper()] = int(arg[:-1])
    return datetime.timedelta(days=units["D"], minutes=units["M"]+60*units["H"], seconds=units["S"])

def neat_timedelta(time: datetime.timedelta):
    seconds = time.seconds
    hours = seconds // (60*60)
    minutes = (seconds // 60) - (hours * 60)
    names = {"days": time.days, "hours": hours, "minutes": minutes, "seconds": seconds % 60}
    keys = names.keys()
    ret = ""
    for key in keys:
        if names[key] == 1:
            ret += ("1 %s " % key[:-1])
        elif names[key] > 1:
            ret += ("%i %s " % (names[key], key))
    if ret == "":
        return "0 seconds"
    else:
        return ret.strip()
