import os
import logging
from discord.ext import commands
import discord
from .Utils import fetch_json, make_embed

logger = logging.getLogger('weather')

class Weather(commands.Cog):
    """Fetch current weather or forecasts."""

    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        if not self.api_key:
            logger.warning("OPENWEATHER_API_KEY not set - weather commands will not work")

    async def get_weather(self, city: str):
        if not self.api_key:
            logger.error("Cannot fetch weather - API key not configured")
            return None
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={self.api_key}&units=metric"
        )
        data = await fetch_json(url)
        if data is None:
            logger.error(f"Failed to fetch weather data for city: {city}")
        return data

    async def get_forecast(self, city: str):
        if not self.api_key:
            logger.error("Cannot fetch forecast - API key not configured")
            return None
        url = (
            "https://api.openweathermap.org/data/2.5/forecast"
            f"?q={city}&appid={self.api_key}&units=metric&cnt=5"
        )
        data = await fetch_json(url)
        if data is None:
            logger.error(f"Failed to fetch forecast data for city: {city}")
        return data

    @commands.command(pass_context=True)
    async def weather(self, ctx, *, city: str):
        """Show current weather for a city."""
        if not self.api_key:
            await ctx.send("Weather API key not configured. Please contact the bot administrator.")
            return

        data = await self.get_weather(city)
        if not data:
            await ctx.send(f"Unable to fetch weather information. Please check your internet connection and try again.")
            return
        if data.get("cod") != 200:
            error_msg = data.get("message", "Unknown error")
            await ctx.send(f"Error fetching weather for '{city}': {error_msg}")
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
        if not self.api_key:
            await ctx.send("Weather API key not configured. Please contact the bot administrator.")
            return

        data = await self.get_forecast(city)
        if not data:
            await ctx.send(f"Unable to fetch forecast information. Please check your internet connection and try again.")
            return
        if data.get("cod") != "200":
            error_msg = data.get("message", "Unknown error")
            await ctx.send(f"Error fetching forecast for '{city}': {error_msg}")
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
