import random
from .Utils import *

from discord.ext import commands

class Anime(commands.Cog):
    """Some anime stuff! Like russian roulette for your eyes!"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def headpat(self, ctx):
        """Headpats! It's CUTE!"""
        pats = requests.get("http://headp.at/js/pats.json").json()
        pat = random.choice(pats)
        file = get_image_data("http://headp.at/pats/{}".format(pat))
        await ctx.message.channel.send(file=discord.File(file["content"], filename=file["filename"]))


    @commands.command(pass_context=True)
    async def yandere(self, ctx, *tags):
        """Don't use this, you nasty weeb edgelord."""
        if str(ctx.message.channel) != 'nsfw':
            await ctx.message.channel.send("Naughty pictures need to stay in an nsfw channel")
            return
        data = requests.get("https://yande.re/post/index.json?limit={}&tags={}".format("200", '+'.join(tags))).json()
        if len(data) == 0:
            await ctx.message.channel.send("No results found.")
            return
        image = random.choice(data)
        if "file_url" in image:
            file = get_image_data(image["file_url"])
            await ctx.message.channel.send(file=discord.File(file["content"], filename=file["filename"]))
        else:
            await ctx.message.channel.send("Error getting picture.")


    @commands.command(pass_context=True)
    async def danbooru(self, ctx, *tags):
        """Don't use this, you nasty weeb edgelord."""
        if str(ctx.message.channel) != 'nsfw':
            await ctx.message.channel.send("Naughty pictures need to stay in an nsfw channel")
            return
        data = requests.get("https://danbooru.donmai.us/post/index.json?limit={}&tags={}".format("200", '+'.join(tags))).json()
        if len(data) == 0:
            await ctx.message.channel.send("No results found.")
            return
        image = random.choice(data)
        if "file_url" in image:
            file = get_image_data(image["file_url"])
            await ctx.message.channel.send(file=discord.File(file["content"], filename=file["filename"]))
        else:
            await ctx.message.channel.send("Error getting picture.")


def setup(bot):
    bot.add_cog(Anime(bot))
