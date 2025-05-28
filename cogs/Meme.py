import os
import random
from discord.ext import commands
import discord
from .Utils import fetch_json, get_image_data

class Meme(commands.Cog):
    """Search Reddit and Imgur for memes."""

    def __init__(self, bot):
        self.bot = bot
        self.imgur_client = os.getenv("IMGUR_CLIENT_ID")

    async def search_reddit(self, query: str):
        headers = {"User-Agent": "discord-bot"}
        url = f"https://www.reddit.com/search.json?q={query}&limit=50&sort=relevance"
        data = await fetch_json(url, headers=headers)
        if not data:
            return None
        posts = data.get("data", {}).get("children", [])
        random.shuffle(posts)
        for post in posts:
            url = post.get("data", {}).get("url")
            if url and any(url.lower().endswith(ext) for ext in [".jpg", ".png", ".gif"]):
                return url
        return None

    async def search_imgur(self, query: str):
        if not self.imgur_client:
            return None
        headers = {"Authorization": f"Client-ID {self.imgur_client}"}
        url = f"https://api.imgur.com/3/gallery/search/top/all/1?q={query}"
        data = await fetch_json(url, headers=headers)
        if not data or not data.get("data"):
            return None
        items = data["data"]
        random.shuffle(items)
        for item in items:
            images = item.get("images", [])
            for image in images:
                link = image.get("link")
                if link and any(link.lower().endswith(ext) for ext in [".jpg", ".png", ".gif"]):
                    return link
        return None

    @commands.command(pass_context=True)
    async def meme(self, ctx, *, query: str):
        """Search for a meme and post it."""
        url = await self.search_reddit(query)
        if not url:
            url = await self.search_imgur(query)
        if not url:
            await ctx.send("Couldn't find a meme matching that query.")
            return
        file = await get_image_data(url)
        if file:
            await ctx.send(file=discord.File(file["content"], filename=file["filename"]))
        else:
            await ctx.send(url)

async def setup(bot):
    await bot.add_cog(Meme(bot))
