import asyncio
from discord.ext import commands
from .Utils import make_embed

# Simple helpers copied from Thirstyboi

def parse_time(argument: str):
    unit = argument[-1].lower()
    num = argument[:-1]
    try:
        num = int(num)
    except ValueError:
        return None
    if unit == 's':
        return num
    if unit == 'm':
        return num * 60
    if unit == 'h':
        return num * 60 * 60
    if unit == 'd':
        return num * 60 * 60 * 24
    return None

class Reminders(commands.Cog):
    """Allow users to set reminders and simple timers."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def remind(self, ctx, time: str, *, message: str):
        """Remind the user with a message after a certain time."""
        seconds = parse_time(time)
        if seconds is None:
            await ctx.send('Invalid time format. Use 10s, 5m, 1h or 1d.')
            return
        await ctx.send(f'Reminder set for {time}.')
        await asyncio.sleep(seconds)
        await ctx.send(f'{ctx.author.mention} Reminder: {message}')

    @commands.command(pass_context=True)
    async def timer(self, ctx, time: str):
        """Start a timer and alert when done."""
        seconds = parse_time(time)
        if seconds is None:
            await ctx.send('Invalid time format. Use 10s, 5m, 1h or 1d.')
            return
        await ctx.send(f'Timer started for {time}.')
        await asyncio.sleep(seconds)
        await ctx.send(f'{ctx.author.mention} Your timer for {time} is up!')

async def setup(bot):
    await bot.add_cog(Reminders(bot))
