import io
import asyncio
import aiohttp
import discord
import logging

# Global aiohttp session for reuse across all requests
_http_session = None
logger = logging.getLogger('utils')

async def get_http_session():
    """Get or create a shared aiohttp ClientSession."""
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()
    return _http_session

async def close_http_session():
    """Close the shared aiohttp ClientSession."""
    global _http_session
    if _http_session is not None and not _http_session.closed:
        await _http_session.close()
        _http_session = None

async def fetch_json(url, *, timeout=10, headers=None):
    """Fetch JSON data from a URL asynchronously."""
    try:
        session = await get_http_session()
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            resp.raise_for_status()
            return await resp.json()
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error fetching JSON from {url}: {e}")
        return None
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching JSON from {url}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching JSON from {url}: {e}")
        return None

async def get_image_data(url, *, timeout=10):
    """Retrieve image data from a URL asynchronously."""
    try:
        session = await get_http_session()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            resp.raise_for_status()
            data = await resp.read()
        content = io.BytesIO(data)
        filename = url.rsplit("/", 1)[-1]
        return {"content": content, "filename": filename}
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error fetching image from {url}: {e}")
        return None
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching image from {url}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching image from {url}: {e}")
        return None

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
