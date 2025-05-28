import requests
from .Utils import get_image_data
from discord.ext import commands

class Pets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def dog(self, ctx):
        """Yay, dogs!"""
        woofer = requests.get('https://random.dog/woof')
        file_url = 'https://random.dog/' + str(woofer.content)[2:-1]
        file = await get_image_data(file_url)
        if file:
            await ctx.message.channel.send(file=discord.File(file["content"], filename=file["filename"]))
        else:
            await ctx.message.channel.send("Error getting picture.")

async def setup(bot):
    await bot.add_cog(Pets(bot))
