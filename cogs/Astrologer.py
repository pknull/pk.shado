# -*- coding: utf-8 -*-
"""
Astrologer Discord Cog - Streamlined version using modular architecture.
Provides astrological readings, natal charts, and horoscopes.
"""
import random
import openai
import os
import json
import asyncio
import logging
import time
import shutil
import tempfile
import discord
from datetime import datetime
from typing import Dict, Any, Optional
from discord.ext import commands
from kerykeion import AstrologicalSubject

# Import our new modules
from .astrologer_data import (
    ZODIAC_SIGNS, SIGN_MAP, ZODIAC_DATES, READING_TYPES, COMPONENT_INFO
)
from .astrologer_geocoding import GeocodingService
from .astrologer_core import AstrologicalComputer

logger = logging.getLogger('astrologer')


class Astrologer(commands.Cog):
    """Astrological readings and natal chart computations."""

    def __init__(self, bot, user_birth_data=None):
        """
        Initialize the Astrologer cog.

        Args:
            bot: Discord bot instance
            user_birth_data: Optional pre-loaded birth data dictionary
        """
        self.bot = bot
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.custom_uri = os.getenv("ASTROLOGER_API_URI", None)

        # Initialize services
        geonames_username = os.getenv("GEONAMES_USERNAME")
        self.geocoding = GeocodingService(geonames_username)
        self.computer = AstrologicalComputer()

        # Load user birth data
        self.user_birth_data = self.load_birth_data() if user_birth_data is None else user_birth_data

        # Start autosave task
        if hasattr(self.bot, 'loop') and self.bot.loop:
            self.bot.loop.create_task(self.autosave())

        logger.info("Astrologer cog initialized successfully")

    # ===== Data Persistence (JSON) =====

    async def autosave(self):
        """Auto save user birth data in the background."""
        while not self.bot.is_closed():
            self.save_birth_data()
            await asyncio.sleep(300)  # Save every 5 minutes

    def save_birth_data(self, filename="data/astrologer_birth_data.json"):
        """
        Save user birth data to JSON file.

        Args:
            filename: Path to JSON file
        """
        try:
            # Convert datetime objects to ISO strings for JSON serialization
            json_data = {}
            for user_id, data in self.user_birth_data.items():
                user_data = data.copy()
                if 'datetime' in user_data and isinstance(user_data['datetime'], datetime):
                    user_data['datetime'] = user_data['datetime'].isoformat()
                json_data[str(user_id)] = user_data

            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(json_data, f, indent=2)
            logger.debug(f"Saved birth data for {len(json_data)} users")
        except Exception as e:
            logger.error(f"Error saving birth data: {e}")

    def load_birth_data(self, filename="data/astrologer_birth_data.json") -> Dict[int, Dict[str, Any]]:
        """
        Load user birth data from JSON file.

        Args:
            filename: Path to JSON file

        Returns:
            Dictionary mapping user IDs to birth data
        """
        try:
            with open(filename, 'r') as f:
                json_data = json.load(f)

            # Convert ISO strings back to datetime objects
            birth_data = {}
            for user_id_str, data in json_data.items():
                user_data = data.copy()
                if 'datetime' in user_data and isinstance(user_data['datetime'], str):
                    user_data['datetime'] = datetime.fromisoformat(user_data['datetime'])
                birth_data[int(user_id_str)] = user_data

            logger.info(f"Loaded birth data for {len(birth_data)} users")
            return birth_data
        except FileNotFoundError:
            logger.info("No existing birth data file found, starting fresh")
            return {}
        except Exception as e:
            logger.error(f"Error loading birth data: {e}")
            return {}

    # ===== Zodiac Sign Helpers =====

    def get_zodiac_sign(self, birthday: datetime) -> Optional[str]:
        """
        Determine zodiac sign from birthday (fallback method).

        Args:
            birthday: Birth datetime

        Returns:
            Zodiac sign name or None
        """
        month, day = birthday.month, birthday.day

        for i, (start_month, start_day, end_month, end_day) in enumerate(ZODIAC_DATES):
            if (month == start_month and day >= start_day) or (month == end_month and day <= end_day):
                return ZODIAC_SIGNS[i]

        return None

    def get_zodiac_sign_ephemeris(self, birth_data: Dict[str, Any]) -> Optional[str]:
        """
        Get zodiac sign using ephemeris data.

        Args:
            birth_data: Birth data dictionary

        Returns:
            Zodiac sign name
        """
        if 'lat' in birth_data and 'lon' in birth_data:
            try:
                birthday = birth_data['datetime']
                natal_data = self.computer.compute_natal(
                    name="User",
                    y=birthday.year, m=birthday.month, d=birthday.day,
                    hh=birthday.hour, mm=birthday.minute,
                    lat=birth_data['lat'], lon=birth_data['lon'],
                    tz_str=birth_data['tz_str']
                )
                sun_sign = natal_data['natal']['six']['sun']['sign']
                return SIGN_MAP.get(sun_sign, sun_sign.capitalize())
            except Exception as e:
                logger.error(f"Error computing zodiac sign from ephemeris: {e}")

        # Fallback to basic calculation
        if isinstance(birth_data, dict):
            birthday = birth_data['datetime']
        else:
            birthday = birth_data
        return self.get_zodiac_sign(birthday)

    # ===== OpenAI Reading Generation =====

    async def generate_component_reading(
        self,
        component_name: str,
        sign_data: Dict[str, Any],
        user_name: str,
        birth_info: str
    ) -> list:
        """
        Generate a focused reading for a single astrological component.

        Args:
            component_name: Component name (Sun, Moon, Rising, etc.)
            sign_data: Sign data dictionary with 'sign' key
            user_name: User's display name
            birth_info: Birth information string

        Returns:
            List of reading sections
        """
        comp_info = COMPONENT_INFO.get(component_name, {
            "icon": "🔮",
            "title": f"THE {component_name.upper()}",
            "description": "your astrological influence"
        })
        sign_name = SIGN_MAP.get(sign_data['sign'], sign_data['sign'])

        prompt = (
            f"You are an ancient mystic astrologer. Generate a detailed reading for {user_name}, {birth_info}.\n\n"
            f"Focus on their {component_name} in {sign_name} - {comp_info['description']}.\n\n"
            f"Format your response as separate sections using this exact structure:\n\n"
            f"TITLE: {comp_info['icon']} {comp_info['title']} IN {sign_name.upper()} {comp_info['icon']}\n\n"
            f"ESSENCE: [Write 2-3 sentences about their core nature with this placement]\n\n"
            f"TRAITS: [Write 2-3 sentences about personality traits and behaviors]\n\n"
            f"ADVICE: [Write 2-3 sentences of mystical advice or warnings]\n\n"
            f"Use baroque, mystical language. Address {user_name} directly. Each section should be complete thoughts."
        )

        try:
            if self.custom_uri:
                client = openai.OpenAI(base_url=self.custom_uri)
            else:
                client = openai.OpenAI()

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400
            )

            content = response.choices[0].message.content.strip()
            return self.parse_structured_reading(content)

        except openai.APIError as e:
            return [f"The stars are clouded today: {e}"]
        except Exception as e:
            return [f"A cosmic disturbance occurred: {e}"]

    def parse_structured_reading(self, content: str) -> list:
        """
        Parse structured reading into separate message sections.

        Args:
            content: Raw reading content

        Returns:
            List of reading sections
        """
        sections = []
        parts = content.split('\n\n')
        current_section = ""

        for part in parts:
            part = part.strip()
            if part.startswith('TITLE:'):
                if current_section:
                    sections.append(current_section.strip())
                current_section = part.replace('TITLE:', '').strip()
            elif part.startswith('ESSENCE:'):
                current_section += f"\n\n{part.replace('ESSENCE:', '').strip()}"
            elif part.startswith('TRAITS:'):
                if current_section:
                    sections.append(current_section.strip())
                current_section = part.replace('TRAITS:', '').strip()
            elif part.startswith('ADVICE:'):
                if current_section:
                    sections.append(current_section.strip())
                current_section = part.replace('ADVICE:', '').strip()
            else:
                if current_section:
                    current_section += f"\n\n{part}"

        if current_section:
            sections.append(current_section.strip())

        return sections if sections else [content]

    # ===== Discord Commands =====

    @commands.command(name='astrology', aliases=['horoscope', 'stars'])
    async def astrology(self, ctx, reading_type: str = "daily", sign: str = None):
        """Get an astrological reading."""
        user_id = ctx.author.id
        chosen_randomly = False

        # Handle legacy usage where first argument might be a zodiac sign
        if reading_type.capitalize() in ZODIAC_SIGNS:
            original_sign = reading_type.capitalize()
            reading_type = sign if sign else "daily"
            sign = original_sign

        # Validate and normalize reading type
        if reading_type not in READING_TYPES:
            reading_type = "daily"

        # Check if user has stored birth data
        if not sign and user_id in self.user_birth_data:
            birth_data = self.user_birth_data[user_id]

            # Get current transits and generate multi-part reading
            if 'lat' in birth_data and 'lon' in birth_data:
                try:
                    transits = self.computer.compute_transits_now(
                        lat=birth_data['lat'],
                        lon=birth_data['lon'],
                        tz_str=birth_data['tz_str']
                    )

                    moon_sign = transits['transits']['moon']['sign']
                    moon_sign_full = SIGN_MAP.get(moon_sign, moon_sign)

                    # Get natal data
                    birthday = birth_data['datetime']
                    natal_data = self.computer.compute_natal(
                        name=ctx.author.display_name,
                        y=birthday.year, m=birthday.month, d=birthday.day,
                        hh=birthday.hour, mm=birthday.minute,
                        lat=birth_data['lat'], lon=birth_data['lon'],
                        tz_str=birth_data['tz_str']
                    )

                    six = natal_data['natal']['six']
                    birth_info = f"born on {birthday.strftime('%B %d, %Y')} at {birthday.strftime('%I:%M %p')}"

                    # Send header message
                    header = f"🌟 **Cosmic Reading for {ctx.author.display_name}** 🌟\n_Current Moon Transit: {moon_sign_full} • Preparing your celestial blueprint..._"
                    await ctx.send(header)

                    # Generate and send individual component readings
                    components = [
                        ("Rising", six['asc']),
                        ("Sun", six['sun']),
                        ("Moon", six['moon'])
                    ]

                    for component_name, sign_data in components:
                        sections = await self.generate_component_reading(
                            component_name, sign_data, ctx.author.display_name, birth_info
                        )

                        for section in sections:
                            if section.strip():
                                await ctx.send(section)
                                await asyncio.sleep(0.5)

                    return
                except Exception as e:
                    logger.error(f"Error computing transits: {e}")
                    await ctx.send(f"```\nError computing transits: {e}\nFalling back to basic reading.\n```")

            # Fallback - use birth data for basic reading
            sign = self.get_zodiac_sign_ephemeris(birth_data)
            header_suffix = " (based on your birth chart)"
            user_name = ctx.author.display_name

        elif not sign:
            sign = random.choice(ZODIAC_SIGNS)
            chosen_randomly = True
            header_suffix = " (randomly chosen - use !setbirthday for personalized readings)"
            user_name = sign
        else:
            sign = sign.capitalize()
            header_suffix = ""
            user_name = sign
            if sign not in ZODIAC_SIGNS:
                await ctx.send(f"```\nUnknown zodiac sign: {sign}\nValid signs: {', '.join(ZODIAC_SIGNS)}\n```")
                return

        # Basic fallback reading
        await ctx.send(
            f"```\n🌟 {reading_type.capitalize()} Reading for {user_name} 🌟{header_suffix}\n\n"
            f"Basic {sign} reading - use !setbirthday with your birth location for detailed multi-part readings!\n\n"
            f"✨ The stars await your complete birth information to reveal deeper truths... ✨\n```"
        )

    @commands.command(name='setbirthday')
    async def set_birthday(self, ctx, *, birth_info: str = None):
        """
        Set your birth information for personalized astrology readings.

        Format: YYYY-MM-DD HH:MM "City, State/Province, Country"
        Or with coordinates: YYYY-MM-DD HH:MM "lat,lon,timezone"

        Examples:
            !setbirthday 1990-03-15 14:30 "Phoenix, Arizona, USA"
            !setbirthday 1976-01-27 00:24 "33.4484,-112.074,America/Phoenix"
        """
        if not birth_info:
            await ctx.send(
                "```\nPlease provide your birth info in one of these formats:\n"
                "YYYY-MM-DD HH:MM \"City, State/Province, Country\"\n"
                "YYYY-MM-DD HH:MM \"latitude,longitude,timezone\"\n"
                "Examples:\n"
                "!setbirthday 1990-03-15 14:30 \"Phoenix, Arizona, USA\"\n"
                "!setbirthday 1976-01-27 00:24 \"33.4484,-112.074,America/Phoenix\"\n```"
            )
            return

        try:
            # Parse birth info
            if '"' in birth_info:
                datetime_part = birth_info.split('"')[0].strip()
                location = birth_info.split('"')[1]
            else:
                parts = birth_info.rsplit(' ', 1)
                if len(parts) == 2:
                    datetime_part, location = parts
                else:
                    datetime_part = birth_info
                    location = "Unknown"

            birthday = datetime.strptime(datetime_part, "%Y-%m-%d %H:%M")
            user_id = ctx.author.id

            # Check if location is coordinates
            def parse_coordinates(location_str):
                """Parse coordinate string: 'lat,lon,timezone' -> (lat, lon, timezone)"""
                try:
                    parts = location_str.split(',')
                    if len(parts) == 3:
                        lat = float(parts[0].strip())
                        lon = float(parts[1].strip())
                        tz = parts[2].strip()
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            return lat, lon, tz
                    return None
                except (ValueError, IndexError):
                    return None

            # Try coordinate parsing first
            coord_result = parse_coordinates(location)
            if coord_result:
                lat, lon, tz_str = coord_result
                logger.debug(f"Using direct coordinates: lat={lat}, lon={lon}, tz={tz_str}")

                # Validate timezone
                try:
                    import pytz
                    pytz.timezone(tz_str)

                    self.user_birth_data[user_id] = {
                        'datetime': birthday,
                        'location': f"{lat},{lon}",
                        'lat': lat,
                        'lon': lon,
                        'tz_str': tz_str
                    }
                    self.save_birth_data()

                    await ctx.send(
                        f"✅ **Birth information saved!**\n"
                        f"📅 **Date/Time:** {birthday.strftime('%B %d, %Y at %I:%M %p')}\n"
                        f"🌍 **Coordinates:** {lat}, {lon}\n"
                        f"🕒 **Timezone:** {tz_str}\n"
                        f"Use `!astrology` for your personalized reading!"
                    )
                    return

                except pytz.UnknownTimezoneError:
                    await ctx.send(f"❌ Invalid timezone: '{tz_str}'. Use a valid timezone like 'America/Phoenix'.")
                    return

            # Geocode the location
            logger.debug(f"Geocoding location: '{location}'")
            result = self.geocoding.geocode(location)

            if result is None:
                await ctx.send(
                    f"```\nError looking up location: {location}\n"
                    f"Please try a more specific location like:\n"
                    f"• \"Phoenix, Arizona, USA\"\n"
                    f"• \"London, England, UK\"\n"
                    f"• \"Toronto, Ontario, Canada\"\n```"
                )
                return

            lat, lon, tz_str = result

            # Validate coordinates with timezone
            if not self.geocoding.validate_coordinates_timezone(lat, lon, tz_str, location):
                logger.warning(f"Coordinate validation failed for {location}")

            # Store birth data
            self.user_birth_data[user_id] = {
                'datetime': birthday,
                'location': location,
                'lat': lat,
                'lon': lon,
                'tz_str': tz_str
            }
            self.save_birth_data()

            # Compute natal chart to get accurate sign
            natal_data = self.computer.compute_natal(
                name=ctx.author.display_name,
                y=birthday.year, m=birthday.month, d=birthday.day,
                hh=birthday.hour, mm=birthday.minute,
                lat=lat, lon=lon, tz_str=tz_str
            )
            sun_sign = SIGN_MAP.get(natal_data['natal']['six']['sun']['sign'],
                                    natal_data['natal']['six']['sun']['sign'])

            await ctx.send(
                f"```\n🌟 Birth information set successfully! 🌟\n"
                f"Birthday: {birthday.strftime('%B %d, %Y at %I:%M %p')}\n"
                f"Location: {location}\n"
                f"Coordinates: {lat:.4f}, {lon:.4f}\n"
                f"Timezone: {tz_str}\n"
                f"Sun Sign: {sun_sign}\n"
                f"Configuration: tropical • placidus • true node • engine=kerykeion@4.26.3\n"
                f"Use !natalchart for detailed chart or !astrology for daily reading\n```"
            )

        except ValueError:
            await ctx.send(
                "```\nInvalid format. Please use:\n"
                "YYYY-MM-DD HH:MM \"City, State/Province, Country\"\n"
                "Examples:\n"
                "!setbirthday 1990-03-15 14:30 \"Phoenix, Arizona, USA\"\n```"
            )

    @commands.command(name='mybirthday')
    async def my_birthday(self, ctx):
        """Check your stored birth information and zodiac sign."""
        user_id = ctx.author.id

        if user_id not in self.user_birth_data:
            await ctx.send(
                "```\nNo birth information set. Use the command:\n"
                "!setbirthday YYYY-MM-DD HH:MM \"City, State, Country\"\n"
                "Example: !setbirthday 1976-01-27 00:24 \"Phoenix, Arizona, USA\"\n```"
            )
            return

        birth_data = self.user_birth_data[user_id]
        birthday = birth_data['datetime']

        if 'lat' in birth_data and 'lon' in birth_data:
            lat, lon = birth_data['lat'], birth_data['lon']
            tz_str = birth_data.get('tz_str', 'Unknown')

            try:
                natal_data = self.computer.compute_natal(
                    name=ctx.author.display_name,
                    y=birthday.year, m=birthday.month, d=birthday.day,
                    hh=birthday.hour, mm=birthday.minute,
                    lat=lat, lon=lon, tz_str=tz_str
                )
                sun_sign = SIGN_MAP.get(natal_data['natal']['six']['sun']['sign'],
                                       natal_data['natal']['six']['sun']['sign'])
            except Exception:
                sun_sign = "Error computing"

            await ctx.send(
                f"```\n🌟 Your Astrological Info 🌟\n"
                f"Birthday: {birthday.strftime('%B %d, %Y at %I:%M %p')}\n"
                f"Coordinates: {lat}, {lon}\n"
                f"Timezone: {tz_str}\n"
                f"Sun Sign: {sun_sign}\n"
                f"Configuration: tropical • placidus • true node • engine=kerykeion@4.26.3\n```"
            )
        else:
            # Legacy format
            location = birth_data.get('location', 'Unknown')
            sign = self.get_zodiac_sign_ephemeris(birth_data)
            await ctx.send(
                f"```\n🌟 Your Astrological Info (Legacy Format) 🌟\n"
                f"Birthday: {birthday.strftime('%B %d, %Y at %I:%M %p')}\n"
                f"Location: {location}\n"
                f"Zodiac Sign: {sign}\n"
                f"Note: Use !setbirthday with your birth location for precise results\n```"
            )

    @commands.command(name='removebirthday')
    async def remove_birthday(self, ctx):
        """Remove your stored birth information."""
        user_id = ctx.author.id

        if user_id in self.user_birth_data:
            del self.user_birth_data[user_id]
            self.save_birth_data()
            await ctx.send("```\n🌟 Birth information removed successfully\n```")
        else:
            await ctx.send("```\nNo birth information found to remove\n```")

    @commands.command(name='settimezone')
    async def set_timezone(self, ctx, tz_string: str = None):
        """
        Set or update your timezone for more accurate readings.

        Examples: America/New_York, Europe/London, Asia/Tokyo
        Use !listtimezones for common timezone names.
        """
        user_id = ctx.author.id

        if user_id not in self.user_birth_data:
            await ctx.send(
                "```\nPlease set your birth information first using:\n"
                "!setbirthday YYYY-MM-DD HH:MM \"City, State, Country\"\n```"
            )
            return

        if not tz_string:
            await ctx.send(
                "```\nPlease provide a timezone string. Examples:\n"
                "!settimezone America/New_York\n"
                "!settimezone Europe/London\n"
                "!settimezone Asia/Tokyo\n"
                "Use !listtimezones for more options\n```"
            )
            return

        try:
            from zoneinfo import ZoneInfo
            test_zone = ZoneInfo(tz_string)

            self.user_birth_data[user_id]['tz_str'] = tz_string
            self.save_birth_data()

            await ctx.send(
                f"```\n🌟 Timezone updated to {tz_string}\n"
                f"Use !mybirthday to verify your updated info\n```"
            )

        except Exception:
            await ctx.send(
                f"```\nInvalid timezone: {tz_string}\n"
                f"Please use a valid timezone string like:\n"
                f"America/New_York, Europe/London, Asia/Tokyo\n"
                f"Use !listtimezones for more options\n```"
            )

    @commands.command(name='listtimezones')
    async def list_timezones(self, ctx):
        """List common timezone strings for use with !settimezone."""
        timezone_examples = (
            "🌍 Common Timezones 🌍\n\n"
            "NORTH AMERICA:\n"
            "• America/New_York (Eastern)\n"
            "• America/Chicago (Central)\n"
            "• America/Denver (Mountain)\n"
            "• America/Los_Angeles (Pacific)\n"
            "• America/Phoenix (Arizona)\n"
            "• America/Toronto (Toronto)\n"
            "• America/Vancouver (Vancouver)\n\n"
            "EUROPE:\n"
            "• Europe/London (UK)\n"
            "• Europe/Paris (France/Germany)\n"
            "• Europe/Rome (Italy)\n"
            "• Europe/Madrid (Spain)\n"
            "• Europe/Amsterdam (Netherlands)\n\n"
            "ASIA/PACIFIC:\n"
            "• Asia/Tokyo (Japan)\n"
            "• Asia/Shanghai (China)\n"
            "• Asia/Kolkata (India)\n"
            "• Australia/Sydney (Sydney)\n"
            "• Australia/Melbourne (Melbourne)\n\n"
            "Usage: !settimezone Europe/London"
        )

        await ctx.send(f"```\n{timezone_examples}\n```")

    @commands.command(name='zodiac')
    async def zodiac_info(self, ctx):
        """Show information about astrology commands."""
        signs_list = "\n".join([f"• {sign}" for sign in ZODIAC_SIGNS])
        types_list = "\n".join([f"• {rtype}" for rtype in READING_TYPES])

        info_message = (
            "🌟 Astrologer Commands 🌟\n\n"
            "READINGS:\n"
            "• !astrology [reading_type] [sign_override]\n"
            "• !horoscope, !stars (aliases)\n\n"
            "PERSONAL DATA:\n"
            "• !setbirthday YYYY-MM-DD HH:MM \"Location\"\n"
            "• !mybirthday (view your info)\n"
            "• !removebirthday\n"
            "• !settimezone [timezone]\n"
            "• !listtimezones (common timezones)\n\n"
            "CHARTS:\n"
            "• !natalchart (detailed birth chart)\n"
            "• !chartimage (visual SVG natal chart)\n\n"
            f"Reading Types:\n{types_list}\n\n"
            "Examples:\n"
            "• !astrology daily (uses your stored sign)\n"
            "• !astrology love Leo (love reading for Leo)\n"
            "• !setbirthday 1990-03-15 14:30 \"Phoenix, Arizona, USA\"\n"
            "• !settimezone America/New_York"
        )

        await ctx.send(f"```\n{info_message}\n```")

    @commands.command(name='natalchart', aliases=['chart', 'birthchart'])
    async def natal_chart(self, ctx):
        """Get detailed natal chart with deterministic computation."""
        user_id = ctx.author.id

        if user_id not in self.user_birth_data:
            await ctx.send(
                "```\nNo birth information set. Use the command:\n"
                "!setbirthday YYYY-MM-DD HH:MM \"City, State, Country\"\n"
                "Example: !setbirthday 1976-01-27 00:24 \"Phoenix, Arizona, USA\"\n```"
            )
            return

        birth_data = self.user_birth_data[user_id]

        if 'lat' not in birth_data or 'lon' not in birth_data:
            await ctx.send(
                "```\nOld birth data format. Please reset with coordinates:\n"
                "!setbirthday YYYY-MM-DD HH:MM \"City, State, Country\"\n```"
            )
            return

        try:
            birthday = birth_data['datetime']
            natal_data = self.computer.compute_natal(
                name=ctx.author.display_name,
                y=birthday.year, m=birthday.month, d=birthday.day,
                hh=birthday.hour, mm=birthday.minute,
                lat=birth_data['lat'], lon=birth_data['lon'],
                tz_str=birth_data['tz_str']
            )

            six = natal_data['natal']['six']
            houses = natal_data['natal']['houses']

            chart_info = (
                f"🌟 Natal Chart for {ctx.author.display_name} 🌟\n\n"
                f"☀️ Sun: {SIGN_MAP.get(six['sun']['sign'], six['sun']['sign'])}\n"
                f"🌙 Moon: {SIGN_MAP.get(six['moon']['sign'], six['moon']['sign'])}\n"
                f"⬆️ Rising: {SIGN_MAP.get(six['asc']['sign'], six['asc']['sign'])}\n\n"
                f"PLANETS:\n"
                f"☿ Mercury: {SIGN_MAP.get(six['mercury']['sign'], six['mercury']['sign'])}\n"
                f"♀ Venus: {SIGN_MAP.get(six['venus']['sign'], six['venus']['sign'])}\n"
                f"♂ Mars: {SIGN_MAP.get(six['mars']['sign'], six['mars']['sign'])}\n\n"
                f"HOUSES:\n"
                f"1st House (Self): {SIGN_MAP.get(houses['1']['sign'], houses['1']['sign'])}\n"
                f"4th House (Home): {SIGN_MAP.get(houses['4']['sign'], houses['4']['sign'])}\n"
                f"7th House (Relationships): {SIGN_MAP.get(houses['7']['sign'], houses['7']['sign'])}\n"
                f"10th House (Career): {SIGN_MAP.get(houses['10']['sign'], houses['10']['sign'])}\n\n"
                f"tropical • placidus • true node • engine=kerykeion@4.26.3"
            )

            await ctx.send(f"```\n{chart_info}\n```")

        except Exception as e:
            logger.error(f"Error generating natal chart: {e}")
            await ctx.send(
                f"```\nError generating natal chart: {e}\n"
                f"Please check your birth information and try again.\n```"
            )

    @commands.command(name='chartimage', aliases=['visualchart', 'svgchart'])
    async def visual_chart(self, ctx):
        """Generate and send a visual SVG natal chart."""
        user_id = ctx.author.id

        # Prevent duplicate execution within 5 seconds
        current_time = time.time()
        if hasattr(self, '_last_chart_execution'):
            if user_id in self._last_chart_execution:
                time_diff = current_time - self._last_chart_execution[user_id]
                if time_diff < 5:
                    logger.info(f"Preventing duplicate chart execution for user {user_id}")
                    return
        else:
            self._last_chart_execution = {}

        self._last_chart_execution[user_id] = current_time

        if user_id not in self.user_birth_data:
            await ctx.send(
                "```\nNo birth information set. Use the command:\n"
                "!setbirthday YYYY-MM-DD HH:MM \"City, State, Country\"\n"
                "Example: !setbirthday 1976-01-27 00:24 \"Phoenix, Arizona, USA\"\n```"
            )
            return

        birth_data = self.user_birth_data[user_id]

        if 'lat' not in birth_data or 'lon' not in birth_data:
            await ctx.send(
                "```\nOld birth data format. Please reset with coordinates:\n"
                "!setbirthday YYYY-MM-DD HH:MM \"City, State, Country\"\n```"
            )
            return

        try:
            loading_msg = await ctx.send("🌟 Generating your natal chart... please wait ✨")

            birthday = birth_data['datetime']
            svg_path = self.computer.generate_chart_svg(
                name=ctx.author.display_name,
                y=birthday.year, m=birthday.month, d=birthday.day,
                hh=birthday.hour, mm=birthday.minute,
                lat=birth_data['lat'], lon=birth_data['lon'],
                tz_str=birth_data['tz_str']
            )

            if svg_path is None or not os.path.exists(svg_path):
                await loading_msg.edit(content="❌ Chart generation failed. Please try again.")
                return

            # Prepare file for Discord using secure temp file
            sanitized_name = self.computer.sanitize_filename(ctx.author.display_name)
            discord_filename = f"natal_chart_{sanitized_name}_{user_id}.svg"

            # Use tempfile for secure temporary storage
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.svg', delete=False) as tmp:
                temp_svg_path = tmp.name
                with open(svg_path, 'rb') as src:
                    shutil.copyfileobj(src, tmp)

            try:
                # Send SVG file
                with open(temp_svg_path, 'rb') as f:
                    svg_file = discord.File(f, filename=discord_filename)
                    await ctx.send(
                        f"🌟 **Visual Natal Chart for {ctx.author.display_name}** 🌟\n"
                        f"📅 Born: {birthday.strftime('%B %d, %Y at %I:%M %p')}\n"
                        f"📍 Location: {birth_data['location']} ({birth_data['lat']:.4f}, {birth_data['lon']:.4f})\n"
                        f"⚙️ System: Tropical • Placidus Houses • True Node\n"
                        f"📎 Format: SVG (scalable vector chart)",
                        file=svg_file
                    )
                logger.debug(f"Successfully sent SVG chart file")
            finally:
                # Clean up temp files
                for file_path in [svg_path, temp_svg_path]:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except OSError as e:
                        logger.warning(f"Could not clean up file {file_path}: {e}")

            await loading_msg.delete()

        except Exception as e:
            logger.error(f"Error in visual_chart command: {e}")
            await ctx.send(
                f"```\nError generating visual chart: {e}\n"
                f"Please check your birth information and try again.\n```"
            )
            try:
                await loading_msg.delete()
            except:
                pass


async def setup(bot):
    """Setup function for Discord cog."""
    await bot.add_cog(Astrologer(bot))
