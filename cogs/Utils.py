import requests
import io
import discord

def get_image_data(url):
    data = requests.get(url)
    content = io.BytesIO(data.content)
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
