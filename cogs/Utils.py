import io
import asyncio
import aiohttp
import discord

async def fetch_json(url, *, timeout=10):
    """Fetch JSON data from a URL asynchronously."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None

async def get_image_data(url, *, timeout=10):
    """Retrieve image data from a URL asynchronously."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.read()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None
    content = io.BytesIO(data)
    filename = url.rsplit("/", 1)[-1]
    return {"content": content, "filename": filename}

def make_embed(title: str, msg):
    embed = discord.Embed(
        title=title
    )

    if isinstance(msg, list):
        embed.description = "\n".join(str(x) for x in msg)
    elif isinstance(msg, dict):
        for k, v in msg.items():
            embed.add_field(name=k, value=v, inline=False)
    else:
        embed.description = msg

    return embed
