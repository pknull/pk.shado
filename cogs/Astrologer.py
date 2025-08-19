# -*- coding: utf-8 -*-
import random
import openai
import os
import pickle
import asyncio
from datetime import datetime
from discord.ext import commands
from kerykeion import AstrologicalSubject

class Astrologer(commands.Cog):
    def __init__(self, bot, user_birth_data=None):
        self.bot = bot
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.custom_uri = os.getenv("ASTROLOGER_API_URI", None)
        # Load existing birth data or start with empty dict
        self.user_birth_data = self.load_birth_data() if user_birth_data is None else user_birth_data
        
        self.zodiac_signs = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]
        
        self.zodiac_dates = [
            (3, 21, 4, 19),   # Aries: Mar 21 - Apr 19
            (4, 20, 5, 20),   # Taurus: Apr 20 - May 20
            (5, 21, 6, 20),   # Gemini: May 21 - Jun 20
            (6, 21, 7, 22),   # Cancer: Jun 21 - Jul 22
            (7, 23, 8, 22),   # Leo: Jul 23 - Aug 22
            (8, 23, 9, 22),   # Virgo: Aug 23 - Sep 22
            (9, 23, 10, 22),  # Libra: Sep 23 - Oct 22
            (10, 23, 11, 21), # Scorpio: Oct 23 - Nov 21
            (11, 22, 12, 21), # Sagittarius: Nov 22 - Dec 21
            (12, 22, 1, 19),  # Capricorn: Dec 22 - Jan 19
            (1, 20, 2, 18),   # Aquarius: Jan 20 - Feb 18
            (2, 19, 3, 20)    # Pisces: Feb 19 - Mar 20
        ]
        
        self.reading_types = [
            "daily", "weekly", "monthly", "love", "career", "health", "spiritual"
        ]
        
        # Start autosave task
        self.bot.loop.create_task(self.autosave())

    async def autosave(self):
        """Auto save user birth data in the background."""
        while not self.bot.is_closed():
            self.save_birth_data()
            await asyncio.sleep(300)  # Save every 5 minutes

    def save_birth_data(self, filename="astrologer_birth_data.pickle"):
        """Save user birth data to file."""
        with open(filename, "wb") as fp:
            pickle.dump(self.user_birth_data, fp)

    def load_birth_data(self, filename="astrologer_birth_data.pickle"):
        """Load user birth data from file."""
        try:
            with open(filename, "rb") as fp:
                return pickle.load(fp)
        except FileNotFoundError:
            return {}

    def get_birth_chart(self, birth_data):
        """Create astrological subject from birth data."""
        if isinstance(birth_data, dict):
            birthday = birth_data['datetime']
            location = birth_data.get('location', 'Unknown')
        else:
            birthday = birth_data
            location = 'Unknown'
        
        try:
            # Use offline mode to avoid geonames errors for now
            subject = AstrologicalSubject(
                name="User",
                year=birthday.year,
                month=birthday.month,
                day=birthday.day,
                hour=birthday.hour,
                minute=birthday.minute,
                city=location,
                online=False,
                lng=0,  # Greenwich default
                lat=51.5074,  # Greenwich default
                tz_str="GMT"
            )
            return subject
        except Exception:
            return None

    def get_zodiac_sign(self, birthday):
        """Determine zodiac sign from birthday (fallback method)."""
        month, day = birthday.month, birthday.day
        
        for i, (start_month, start_day, end_month, end_day) in enumerate(self.zodiac_dates):
            if (month == start_month and day >= start_day) or (month == end_month and day <= end_day):
                return self.zodiac_signs[i]
        
        return None

    def get_zodiac_sign_ephemeris(self, birth_data):
        """Get zodiac sign using Kerykeion ephemeris data."""
        subject = self.get_birth_chart(birth_data)
        if subject:
            try:
                sun_sign = subject.sun.sign
                # Map short names to full names
                sign_map = {
                    'Ari': 'Aries', 'Tau': 'Taurus', 'Gem': 'Gemini',
                    'Can': 'Cancer', 'Leo': 'Leo', 'Vir': 'Virgo',
                    'Lib': 'Libra', 'Sco': 'Scorpio', 'Sag': 'Sagittarius',
                    'Cap': 'Capricorn', 'Aqu': 'Aquarius', 'Pis': 'Pisces'
                }
                return sign_map.get(sun_sign, sun_sign.capitalize())
            except Exception:
                pass
        
        # Fallback to basic calculation
        if isinstance(birth_data, dict):
            birthday = birth_data['datetime']
        else:
            birthday = birth_data
        return self.get_zodiac_sign(birthday)

    async def generate_reading(self, sign, reading_type="daily", user_name=None):
        # Use the provided name or fall back to the sign
        name_to_use = user_name if user_name else sign
        
        prompt = (
            f"You are a mystical astrologer with deep wisdom of the stars and cosmic energies.\n\n"
            f"Provide an insightful {reading_type} astrological reading for {name_to_use}, who is a {sign}.\n\n"
            f"Include guidance about:\n"
            f"- Current planetary influences\n"
            f"- Opportunities and challenges\n"
            f"- Advice for personal growth\n\n"
            f"Write in a mystical, encouraging tone with specific astrological insights.\n"
            f"Address {name_to_use} directly by name throughout the reading.\n\n"
            f"Reading:"
        )

        try:
            if self.custom_uri:
                client = openai.OpenAI(base_url=self.custom_uri)
            else:
                client = openai.OpenAI()
                
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )

            return response.choices[0].message.content.strip()
        except openai.APIError as e:
            return f"The stars are clouded today: {e}"
        except Exception as e:
            return f"A cosmic disturbance occurred: {e}"

    @commands.command(name='astrology', aliases=['horoscope', 'stars'])
    async def astrology(self, ctx, sign: str = None, reading_type: str = "daily"):
        user_id = ctx.author.id
        chosen_randomly = False
        
        # Check if user has a stored birthday
        if not sign and user_id in self.user_birth_data:
            birth_data = self.user_birth_data[user_id]
            sign = self.get_zodiac_sign_ephemeris(birth_data)
            header_suffix = " (based on your birth chart)"
            # Use user's name for personalized readings
            user_name = ctx.author.display_name
        elif not sign:
            sign = random.choice(self.zodiac_signs)
            chosen_randomly = True
            header_suffix = " (randomly chosen - use !setbirthday to get personalized readings)"
            user_name = sign  # Use sign name for random readings
        else:
            sign = sign.capitalize()
            header_suffix = ""
            user_name = sign  # Use sign name for manual sign readings
            if sign not in self.zodiac_signs:
                await ctx.send(f"```\nUnknown zodiac sign: {sign}\nValid signs: {', '.join(self.zodiac_signs)}\n```")
                return
        
        if reading_type not in self.reading_types:
            reading_type = "daily"
        
        reading = await self.generate_reading(sign, reading_type, user_name)
        
        header = f"🌟 {reading_type.capitalize()} Reading for {user_name} 🌟"
        if chosen_randomly:
            header += header_suffix
        elif header_suffix:
            header += header_suffix
        
        message = f"{header}\n\n{reading}"
        
        await ctx.send(f"```\n{message}\n```")

    @commands.command(name='setbirthday')
    async def set_birthday(self, ctx, *, birth_info: str = None):
        """Set your birth information for personalized astrology readings.
        
        Format: YYYY-MM-DD HH:MM "City, State/Province, Country" 
        Examples: 1990-03-15 14:30 "Phoenix, Arizona, USA" or "London, England, UK"
        """
        if not birth_info:
            await ctx.send(
                "```\nPlease provide your birth info in the format:\n"
                "YYYY-MM-DD HH:MM \"City, State/Province, Country\"\n"
                "Examples:\n"
                "!setbirthday 1990-03-15 14:30 \"Phoenix, Arizona, USA\"\n"
                "!setbirthday 1985-07-22 09:15 \"London, England, UK\"\n"
                "!setbirthday 1992-12-03 18:45 \"Toronto, Ontario, Canada\"\n```"
            )
            return
        
        try:
            # Split the input - look for quoted location at the end
            if '"' in birth_info:
                datetime_part = birth_info.split('"')[0].strip()
                location = birth_info.split('"')[1]
            else:
                # If no quotes, assume last part after space is location
                parts = birth_info.rsplit(' ', 1)
                if len(parts) == 2:
                    datetime_part, location = parts
                else:
                    datetime_part = birth_info
                    location = "Unknown"
            
            birthday = datetime.strptime(datetime_part, "%Y-%m-%d %H:%M")
            user_id = ctx.author.id
            
            # Store as dictionary with datetime and location
            self.user_birth_data[user_id] = {
                'datetime': birthday,
                'location': location
            }
            
            sign = self.get_zodiac_sign_ephemeris(self.user_birth_data[user_id])
            await ctx.send(
                f"```\n🌟 Birth information set successfully! 🌟\n"
                f"Birthday: {birthday.strftime('%B %d, %Y at %I:%M %p')}\n"
                f"Location: {location}\n"
                f"Zodiac Sign: {sign}\n"
                f"Use !astrology to get personalized readings\n```"
            )
        except ValueError:
            await ctx.send(
                "```\nInvalid format. Please use:\n"
                "YYYY-MM-DD HH:MM \"City, State/Province, Country\"\n"
                "Examples:\n"
                "!setbirthday 1990-03-15 14:30 \"Phoenix, Arizona, USA\"\n"
                "!setbirthday 1985-07-22 09:15 \"London, England, UK\"\n```"
            )

    @commands.command(name='mybirthday')
    async def my_birthday(self, ctx):
        """Check your stored birth information and zodiac sign."""
        user_id = ctx.author.id
        
        if user_id not in self.user_birth_data:
            await ctx.send(
                "```\nNo birth information set. Use the command:\n"
                "!setbirthday YYYY-MM-DD HH:MM \"City, State/Province, Country\"\n"
                "Example: !setbirthday 1990-03-15 14:30 \"Phoenix, Arizona, USA\"\n```"
            )
            return
        
        birth_data = self.user_birth_data[user_id]
        
        # Handle both old format (direct datetime) and new format (dict)
        if isinstance(birth_data, dict):
            birthday = birth_data['datetime']
            location = birth_data.get('location', 'Unknown')
        else:
            birthday = birth_data
            location = 'Unknown'
        
        sign = self.get_zodiac_sign_ephemeris(birth_data)
        
        await ctx.send(
            f"```\n🌟 Your Astrological Info 🌟\n"
            f"Birthday: {birthday.strftime('%B %d, %Y at %I:%M %p')}\n"
            f"Location: {location}\n"
            f"Zodiac Sign: {sign}\n```"
        )

    @commands.command(name='removebirthday')
    async def remove_birthday(self, ctx):
        """Remove your stored birth information."""
        user_id = ctx.author.id
        
        if user_id in self.user_birth_data:
            del self.user_birth_data[user_id]
            await ctx.send("```\n🌟 Birth information removed successfully\n```")
        else:
            await ctx.send("```\nNo birth information found to remove\n```")

    @commands.command(name='zodiac')
    async def zodiac_info(self, ctx):
        signs_list = "\n".join([f"• {sign}" for sign in self.zodiac_signs])
        types_list = "\n".join([f"• {rtype}" for rtype in self.reading_types])
        
        info_message = (
            "🌟 Astrologer Commands 🌟\n\n"
            "Usage: !astrology [sign] [type]\n"
            "Aliases: !horoscope, !stars\n\n"
            f"Zodiac Signs:\n{signs_list}\n\n"
            f"Reading Types:\n{types_list}\n\n"
            "Examples:\n"
            "• !astrology Leo daily\n"
            "• !horoscope Pisces love\n"
            "• !stars (random sign, daily reading)"
        )
        
        await ctx.send(f"```\n{info_message}\n```")

    @commands.command(name='natalchart', aliases=['chart', 'birthchart'])
    async def natal_chart(self, ctx):
        """Get detailed natal chart information including planets and houses."""
        user_id = ctx.author.id
        
        if user_id not in self.user_birth_data:
            await ctx.send(
                "```\nNo birth information set. Use the command:\n"
                "!setbirthday YYYY-MM-DD HH:MM \"City, State/Province, Country\"\n"
                "Example: !setbirthday 1990-03-15 14:30 \"Phoenix, Arizona, USA\"\n```"
            )
            return
        
        birth_data = self.user_birth_data[user_id]
        subject = self.get_birth_chart(birth_data)
        
        if not subject:
            await ctx.send("```\nUnable to generate birth chart. Please check your birth information.\n```")
            return
        
        try:
            # Sign mapping for full names
            sign_map = {
                'Ari': 'Aries', 'Tau': 'Taurus', 'Gem': 'Gemini',
                'Can': 'Cancer', 'Leo': 'Leo', 'Vir': 'Virgo',
                'Lib': 'Libra', 'Sco': 'Scorpio', 'Sag': 'Sagittarius',
                'Cap': 'Capricorn', 'Aqu': 'Aquarius', 'Pis': 'Pisces'
            }
            
            # Get key planetary positions directly from subject
            sun_sign = sign_map.get(subject.sun.sign, subject.sun.sign.capitalize())
            moon_sign = sign_map.get(subject.moon.sign, subject.moon.sign.capitalize())
            mercury_sign = sign_map.get(subject.mercury.sign, subject.mercury.sign.capitalize())
            venus_sign = sign_map.get(subject.venus.sign, subject.venus.sign.capitalize())
            mars_sign = sign_map.get(subject.mars.sign, subject.mars.sign.capitalize())
            
            # Get rising sign (ascendant)
            rising_sign = sign_map.get(subject.first_house.sign, subject.first_house.sign.capitalize())
            
            chart_info = (
                f"🌟 Natal Chart for {ctx.author.display_name} 🌟\n\n"
                f"☀️ Sun: {sun_sign}\n"
                f"🌙 Moon: {moon_sign}\n"
                f"⬆️ Rising: {rising_sign}\n\n"
                f"PLANETS:\n"
                f"☿ Mercury: {mercury_sign}\n"
                f"♀ Venus: {venus_sign}\n"
                f"♂ Mars: {mars_sign}\n\n"
                f"HOUSES:\n"
                f"1st House (Self): {sign_map.get(subject.first_house.sign, subject.first_house.sign.capitalize())}\n"
                f"7th House (Relationships): {sign_map.get(subject.seventh_house.sign, subject.seventh_house.sign.capitalize())}\n"
                f"10th House (Career): {sign_map.get(subject.tenth_house.sign, subject.tenth_house.sign.capitalize())}\n"
                f"4th House (Home): {sign_map.get(subject.fourth_house.sign, subject.fourth_house.sign.capitalize())}"
            )
            
            await ctx.send(f"```\n{chart_info}\n```")
            
        except Exception as e:
            await ctx.send(f"```\nError generating chart: {e}\nUsing basic zodiac calculation instead.\n```")
            # Fallback to basic sign
            sign = self.get_zodiac_sign_ephemeris(birth_data)
            await ctx.send(f"```\nYour Sun sign: {sign}\n```")

async def setup(bot):
    await bot.add_cog(Astrologer(bot))