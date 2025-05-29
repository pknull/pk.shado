import os
from discord.ext import commands
import discord
from .Utils import fetch_json, make_embed

class Weather(commands.Cog):
    """Fetch current weather or forecasts."""

    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("OPENWEATHER_API_KEY")

    async def get_weather(self, city: str):
        if not self.api_key:
            return None
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={self.api_key}&units=metric"
        )
        return await fetch_json(url)

    async def get_forecast(self, city: str):
        if not self.api_key:
            return None
        url = (
            "https://api.openweathermap.org/data/2.5/forecast"
            f"?q={city}&appid={self.api_key}&units=metric&cnt=5"
        )
        return await fetch_json(url)

    @commands.command(pass_context=True)
    async def weather(self, ctx, *, city: str):
        """Show current weather for a city."""
        data = await self.get_weather(city)
        if not data or data.get("cod") != 200:
            await ctx.send("Unable to fetch weather information.")
            return
        main = data["main"]
        desc = data["weather"][0]["description"]
        msg = [
            f"Temperature: {main['temp']} °C",
            f"Humidity: {main['humidity']}%",
            f"Conditions: {desc}"
        ]
        embed = make_embed(f"Weather in {data['name']}", msg)
        await ctx.send(embed=embed)

    @commands.command(pass_context=True)
    async def forecast(self, ctx, *, city: str):
        """Show a short forecast for a city."""
        data = await self.get_forecast(city)
        if not data or data.get("cod") != "200":
            await ctx.send("Unable to fetch forecast information.")
            return
        entries = []
        for item in data.get("list", []):
            time = item.get("dt_txt")
            temp = item["main"]["temp"]
            desc = item["weather"][0]["description"]
            entries.append(f"{time}: {temp} °C, {desc}")
        embed = make_embed(f"Forecast for {data['city']['name']}", entries)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Weather(bot))
