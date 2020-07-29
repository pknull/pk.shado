from .Utils import *

from discord.ext import commands
import random

class Members(commands.Cog):
    """Stuff to randomly pick members from a channel."""

    def __init__(self, bot):
        self.bot = bot


    @commands.command(pass_context=True)
    async def sr(self, ctx, count=1):
        """Pick a random user from the server."""
        if ctx.message.server is None:
            await self.bot.say("You can't do this in a private chat (you're the only one here...)")
        members = ctx.message.server.members
        actives = []
        for member in members:
            if str(member.status) == "online" and str(member.display_name) != self.bot.user.name:
                actives.append(member)
        x = 1
        bag = []
        random.shuffle(actives)
        while x <= int(count) and len(actives) > 0:
            bag.append(actives.pop().display_name)
            x += 1
        if type(bag) is list:
            embed = make_embed('👥 Members', bag)
            await self.bot.send_message(ctx.message.channel, embed=embed)
        else:
            await self.bot.say("Error parsing attacker.")

    @commands.command(pass_context=True)
    async def vr(self, ctx, amount: int):
        """Pick a random user from the voice channel you're in."""
        # First getting the voice channel object
        voice_channel = ctx.message.author.voice_channel
        if not voice_channel:
            return await self.bot.say("That is not a valid voice channel.")
        members = voice_channel.voice_members
        if len(members) < amount:
            return await self.say("Sample larger than population.")
        member_names = [x.display_name for x in members]
        msg = random.sample(member_names, int(amount))

        embed = make_embed(
            "{} random users from {}".format(str(amount), voice_channel.name),
            msg
        )
        return await self.bot.send_message(ctx.message.channel, embed=embed)


def setup(bot):
    bot.add_cog(Members(bot))
