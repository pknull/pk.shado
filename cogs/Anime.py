import random
from .Utils import fetch_json, get_image_data, make_embed
from discord.ext import commands

class Anime(commands.Cog):
    """Some anime stuff! Like russian roulette for your eyes!"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def headpat(self, ctx):
        """Headpats! It's CUTE!"""
        pats = await fetch_json("http://headp.at/js/pats.json")
        if not pats:
            await ctx.message.channel.send("Error fetching headpats.")
            return
        pat = random.choice(pats)
        file = await get_image_data(f"http://headp.at/pats/{pat}")
        if file:
            await ctx.message.channel.send(file=discord.File(file["content"], filename=file["filename"]))
        else:
            await ctx.message.channel.send("Error getting picture.")


    @commands.command(pass_context=True)
    async def yandere(self, ctx, *tags):
        """Don't use this, you nasty weeb edgelord."""
        if str(ctx.message.channel) != 'nsfw':
            await ctx.message.channel.send("Naughty pictures need to stay in an nsfw channel")
            return
        data = await fetch_json("https://yande.re/post/index.json?limit={}&tags={}".format("200", '+'.join(tags)))
        if not data:
            await ctx.message.channel.send("Error fetching pictures.")
            return
        if len(data) == 0:
            await ctx.message.channel.send("No results found.")
            return
        image = random.choice(data)
        if "file_url" in image:
            file = await get_image_data(image["file_url"])
            if file:
                await ctx.message.channel.send(file=discord.File(file["content"], filename=file["filename"]))
            else:
                await ctx.message.channel.send("Error getting picture.")
        else:
            await ctx.message.channel.send("Error getting picture.")


    @commands.command(pass_context=True)
    async def danbooru(self, ctx, *tags):
        """Don't use this, you nasty weeb edgelord."""
        if str(ctx.message.channel) != 'nsfw':
            await ctx.message.channel.send("Naughty pictures need to stay in an nsfw channel")
            return
        data = await fetch_json("https://danbooru.donmai.us/post/index.json?limit={}&tags={}".format("200", '+'.join(tags)))
        if not data:
            await ctx.message.channel.send("Error fetching pictures.")
            return
        if len(data) == 0:
            await ctx.message.channel.send("No results found.")
            return
        image = random.choice(data)
        if "file_url" in image:
            file = await get_image_data(image["file_url"])
            if file:
                await ctx.message.channel.send(file=discord.File(file["content"], filename=file["filename"]))
            else:
                await ctx.message.channel.send("Error getting picture.")
        else:
            await ctx.message.channel.send("Error getting picture.")


async def setup(bot):
    await bot.add_cog(Anime(bot))
