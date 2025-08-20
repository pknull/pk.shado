# -*- coding: utf-8 -*-
import random
import openai
import os
import pickle
import asyncio
import math
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from discord.ext import commands
from kerykeion import AstrologicalSubject

class Astrologer(commands.Cog):
    def __init__(self, bot, user_birth_data=None):
        self.bot = bot
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.custom_uri = os.getenv("ASTROLOGER_API_URI", None)
        # Load existing birth data or start with empty dict
        self.user_birth_data = self.load_birth_data() if user_birth_data is None else user_birth_data
        
        # Initialize caches
        self.natal_cache = {}  # Cache for natal charts
        self.transit_cache = {}  # Cache for transits
        
        self.zodiac_signs = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]
        
        # Sign mapping for Kerykeion abbreviated to full names
        self.sign_map = {
            'Ari': 'Aries', 'Tau': 'Taurus', 'Gem': 'Gemini',
            'Can': 'Cancer', 'Leo': 'Leo', 'Vir': 'Virgo',
            'Lib': 'Libra', 'Sco': 'Scorpio', 'Sag': 'Sagittarius',
            'Cap': 'Capricorn', 'Aqu': 'Aquarius', 'Pis': 'Pisces'
        }
        
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
        
        # Start autosave task (skip if no loop available, e.g., in testing)
        if hasattr(self.bot, 'loop') and self.bot.loop:
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

    def angdiff(self, a: float, b: float) -> float:
        """Calculate angular difference between two degrees (0-360)."""
        d = (a - b) % 360.0
        return 360.0 - d if d > 180 else d

    def cache_key_natal(self, name: str, y: int, m: int, d: int, hh: int, mm: int,
                       lat: float, lon: float, tz_str: str, 
                       house_system: str, zodiac_type: str, node_type: str) -> str:
        """Generate deterministic cache key for natal chart."""
        key_data = {
            "name": name, "datetime": f"{y:04d}-{m:02d}-{d:02d}T{hh:02d}:{mm:02d}",
            "lat": round(lat, 6), "lon": round(lon, 6), "tz": tz_str,
            "house": house_system, "zodiac": zodiac_type, "node": node_type
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def cache_key_transits(self, timestamp_bucket: int, lat: float, lon: float) -> str:
        """Generate cache key for transits (bucketed by time)."""
        key_data = {
            "bucket": timestamp_bucket,
            "lat": round(lat, 6), "lon": round(lon, 6)
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def transit_time_bucket(self, timestamp: datetime, bucket_seconds: int = 300) -> int:
        """Bucket timestamp for transit caching (default: 5 minutes)."""
        return int(timestamp.timestamp()) // bucket_seconds

    def compute_natal(self, name: str, y: int, m: int, d: int, hh: int, mm: int,
                     lat: float, lon: float, tz_str: str,
                     house_system: str = "placidus", 
                     zodiac_type: str = "tropical", 
                     node_type: str = "true") -> Dict[str, Any]:
        """Compute deterministic natal chart using Kerykeion with caching."""
        # Check cache first
        cache_key = self.cache_key_natal(name, y, m, d, hh, mm, lat, lon, tz_str, house_system, zodiac_type, node_type)
        if cache_key in self.natal_cache:
            return self.natal_cache[cache_key]
        
        # Map house system to Kerykeion identifier 
        house_map = {
            "placidus": "P", "koch": "K", "regiomontanus": "R", 
            "campanus": "C", "equal": "A", "whole_sign": "W"
        }
        house_id = house_map.get(house_system.lower(), "P")
        
        # Map zodiac type
        zodiac_map = {"tropical": "Tropic", "sidereal": "Sidereal"}
        zodiac_kery = zodiac_map.get(zodiac_type.lower(), "Tropic")
        
        subj = AstrologicalSubject(
            name=name,
            year=y, month=m, day=d, hour=hh, minute=mm,
            city=None, nation=None,  # Force manual coordinates
            lat=lat, lng=lon, tz_str=tz_str,
            houses_system_identifier=house_id,
            zodiac_type=zodiac_kery,
            online=False  # Disable online lookups for deterministic results
        )
        
        # Extract core planetary positions with proper attribute access
        six = {
            "sun": {"lon": subj.sun.abs_pos, "sign": subj.sun.sign},
            "moon": {"lon": subj.moon.abs_pos, "sign": subj.moon.sign},
            "mercury": {"lon": subj.mercury.abs_pos, "sign": subj.mercury.sign},
            "venus": {"lon": subj.venus.abs_pos, "sign": subj.venus.sign},
            "mars": {"lon": subj.mars.abs_pos, "sign": subj.mars.sign},
            "asc": {"lon": subj.first_house.abs_pos, "sign": subj.first_house.sign},
            "mc": {"lon": subj.tenth_house.abs_pos, "sign": subj.tenth_house.sign}
        }
        
        # Extract all 12 houses
        houses = {}
        house_attrs = [
            'first_house', 'second_house', 'third_house', 'fourth_house',
            'fifth_house', 'sixth_house', 'seventh_house', 'eighth_house',
            'ninth_house', 'tenth_house', 'eleventh_house', 'twelfth_house'
        ]
        
        for i, attr in enumerate(house_attrs, 1):
            house_data = getattr(subj, attr)
            houses[str(i)] = {
                "lon": house_data.abs_pos, 
                "sign": house_data.sign
            }
        
        result = {
            "input": {
                "name": name,
                "tz": tz_str, "lat": lat, "lon": lon, 
                "house_system": house_system,
                "zodiac": zodiac_type, "node": node_type
            },
            "natal": {"six": six, "houses": houses},
            "engine": "kerykeion@4.26.3"
        }
        
        # Validate the chart
        self.validate_natal_chart(result)
        
        # Cache the result
        self.natal_cache[cache_key] = result
        return result

    def compute_transits_now(self, lat: float, lon: float, tz_str: str) -> Dict[str, Any]:
        """Compute current transiting planets with caching."""
        now = datetime.now(timezone.utc)
        
        # Check cache (5-minute buckets)
        bucket = self.transit_time_bucket(now, 300)
        cache_key = self.cache_key_transits(bucket, lat, lon)
        if cache_key in self.transit_cache:
            return self.transit_cache[cache_key]
        
        y, m, d = now.year, now.month, now.day
        hh, mm = now.hour, now.minute
        
        tr = AstrologicalSubject(
            name="transits",
            year=y, month=m, day=d, hour=hh, minute=mm,
            city=None, nation=None,
            lat=lat, lng=lon, tz_str="UTC",  # Always UTC for transits
            houses_system_identifier="P",  # Placidus
            zodiac_type="Tropic",  # Tropical
            online=False
        )
        
        result = {
            "utc_now": now.isoformat(),
            "transits": {
                "sun": {"lon": tr.sun.abs_pos, "sign": tr.sun.sign},
                "moon": {"lon": tr.moon.abs_pos, "sign": tr.moon.sign},
                "mercury": {
                    "lon": tr.mercury.abs_pos, 
                    "sign": tr.mercury.sign,
                    "rx": getattr(tr.mercury, 'retrograde', False)
                },
                "venus": {"lon": tr.venus.abs_pos, "sign": tr.venus.sign},
                "mars": {"lon": tr.mars.abs_pos, "sign": tr.mars.sign},
            }
        }
        
        # Cache the result
        self.transit_cache[cache_key] = result
        return result

    def validate_natal_chart(self, natal_data: Dict[str, Any]) -> None:
        """Run mathematical validations on natal chart."""
        natal = natal_data["natal"]
        
        # Solar neighborhood validation
        six = natal["six"]
        sun_lon = six["sun"]["lon"]
        mercury_dist = self.angdiff(sun_lon, six["mercury"]["lon"])
        venus_dist = self.angdiff(sun_lon, six["venus"]["lon"])
        
        if mercury_dist > 28.5:
            raise ValueError(f"Mercury too far from Sun: {mercury_dist:.2f}°")
        if venus_dist > 47.5:
            raise ValueError(f"Venus too far from Sun: {venus_dist:.2f}°")
        
        # Opposition validation
        houses = natal["houses"]
        asc_lon = six["asc"]["lon"]
        mc_lon = six["mc"]["lon"]
        dsc_lon = houses["7"]["lon"]
        ic_lon = houses["4"]["lon"]
        
        asc_dsc_diff = abs(self.angdiff(asc_lon, dsc_lon) - 180.0)
        mc_ic_diff = abs(self.angdiff(mc_lon, ic_lon) - 180.0)
        
        if asc_dsc_diff > 0.5:
            raise ValueError(f"ASC/DSC not opposed: {asc_dsc_diff:.3f}°")
        if mc_ic_diff > 0.5:
            raise ValueError(f"MC/IC not opposed: {mc_ic_diff:.3f}°")

    def get_birth_chart(self, birth_data):
        """Legacy wrapper for existing code compatibility."""
        if isinstance(birth_data, dict):
            birthday = birth_data['datetime']
            lat = birth_data.get('lat', 33.4484)  # Default Phoenix
            lon = birth_data.get('lon', -112.0740)
            tz_str = birth_data.get('tz_str', 'America/Phoenix')
        else:
            birthday = birth_data
            lat, lon, tz_str = 33.4484, -112.0740, 'America/Phoenix'
        
        try:
            result = self.compute_natal(
                name="User",
                y=birthday.year, m=birthday.month, d=birthday.day,
                hh=birthday.hour, mm=birthday.minute,
                lat=lat, lon=lon, tz_str=tz_str
            )
            # Convert back to legacy AstrologicalSubject for compatibility
            return AstrologicalSubject(
                name="User",
                year=birthday.year, month=birthday.month, day=birthday.day,
                hour=birthday.hour, minute=birthday.minute,
                city=None, nation=None,
                lat=lat, lng=lon, tz_str=tz_str,
                houses_system_identifier="P",  # Placidus
                zodiac_type="Tropic",  # Tropical
                online=False
            )
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

    async def generate_component_reading(self, component_name, sign_data, user_name, birth_info):
        """Generate a focused reading for a single astrological component."""
        
        # Map component names to mystical descriptions
        component_info = {
            "Rising": {"icon": "🌅⚖️", "title": "THE RISING VEIL OF DESTINY", "description": "your outward mask and first impressions"},
            "Sun": {"icon": "☀️🔥", "title": "THE SOLAR FLAME OF ESSENCE", "description": "your core identity and life force"},
            "Moon": {"icon": "🌙✨", "title": "THE LUNAR TIDES OF EMOTION", "description": "your inner world and emotional nature"},
            "Mercury": {"icon": "☿️💫", "title": "THE MERCURIAL VOICE OF MIND", "description": "your communication and thought patterns"}, 
            "Venus": {"icon": "♀️💖", "title": "THE VENUSIAN DANCE OF LOVE", "description": "your relationships and aesthetic nature"},
            "Mars": {"icon": "♂️⚔️", "title": "THE MARTIAN FIRE OF ACTION", "description": "your drive and how you pursue desires"}
        }
        
        comp_info = component_info.get(component_name, {"icon": "🔮", "title": f"THE {component_name.upper()}", "description": "your astrological influence"})
        sign_name = self.sign_map.get(sign_data['sign'], sign_data['sign'])
        
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
                max_tokens=400  # Higher limit for structured response
            )

            content = response.choices[0].message.content.strip()
            
            # Parse the structured response into sections
            sections = self.parse_structured_reading(content)
            return sections
            
        except openai.APIError as e:
            return f"The stars are clouded today: {e}"
        except Exception as e:
            return f"A cosmic disturbance occurred: {e}"

    def parse_structured_reading(self, content):
        """Parse structured reading into separate message sections."""
        sections = []
        
        # Split by the section headers
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
                # Continuation of current section
                if current_section:
                    current_section += f"\n\n{part}"
        
        # Add the last section
        if current_section:
            sections.append(current_section.strip())
        
        # Fallback if parsing fails
        if not sections:
            sections = [content]
            
        return sections

    @commands.command(name='astrology', aliases=['horoscope', 'stars'])
    async def astrology(self, ctx, reading_type: str = "daily", sign: str = None):
        user_id = ctx.author.id
        chosen_randomly = False
        
        # Handle legacy usage where first argument might be a zodiac sign
        if reading_type.capitalize() in self.zodiac_signs:
            # First arg is actually a zodiac sign, swap them
            original_sign = reading_type.capitalize()
            reading_type = sign if sign else "daily"  # Use second arg as reading type, default to daily
            sign = original_sign
        
        # Validate and normalize reading type
        if reading_type not in self.reading_types:
            reading_type = "daily"
        
        # Initialize variables for birth data
        birthday = None
        chart = None
        
        # Check if user has stored birth data with coordinates
        if not sign and user_id in self.user_birth_data:
            birth_data = self.user_birth_data[user_id]
            
            # Get current transits and generate multi-part reading
            if 'lat' in birth_data and 'lon' in birth_data:
                try:
                    transits = self.compute_transits_now(
                        lat=birth_data['lat'], 
                        lon=birth_data['lon'], 
                        tz_str=birth_data['tz_str']
                    )
                    
                    moon_sign = transits['transits']['moon']['sign']
                    
                    # Get natal data
                    birthday = birth_data['datetime']
                    natal_data = self.compute_natal(
                        name=ctx.author.display_name,
                        y=birthday.year, m=birthday.month, d=birthday.day,
                        hh=birthday.hour, mm=birthday.minute,
                        lat=birth_data['lat'], lon=birth_data['lon'], 
                        tz_str=birth_data['tz_str']
                    )
                    
                    six = natal_data['natal']['six']
                    moon_sign_full = self.sign_map.get(moon_sign, moon_sign)
                    
                    # Build birth info string
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
                        sections = await self.generate_component_reading(component_name, sign_data, ctx.author.display_name, birth_info)
                        
                        # Send each section as a separate message
                        for section in sections:
                            if section.strip():
                                await ctx.send(section)
                                await asyncio.sleep(0.5)  # Short delay between sections
                    
                    return
                except Exception as e:
                    await ctx.send(f"```\nError computing transits: {e}\nFalling back to basic reading.\n```")
            
            # Fallback - use birth data if available for a basic multi-part reading
            sign = self.get_zodiac_sign_ephemeris(birth_data)
            
            # Try to get chart data for multi-part reading
            birthday = birth_data['datetime']
            if 'lat' in birth_data and 'lon' in birth_data:
                try:
                    natal_data = self.compute_natal(
                        name=ctx.author.display_name,
                        y=birthday.year, m=birthday.month, d=birthday.day,
                        hh=birthday.hour, mm=birthday.minute,
                        lat=birth_data['lat'], lon=birth_data['lon'], 
                        tz_str=birth_data['tz_str']
                    )
                    
                    six = natal_data['natal']['six']
                    birth_info = f"born on {birthday.strftime('%B %d, %Y')} at {birthday.strftime('%I:%M %p')}"
                    
                    # Send header
                    header = f"🌟 **Personal Reading for {ctx.author.display_name}** 🌟\n_Based on your birth chart • {sign} essence revealed..._"
                    await ctx.send(header)
                    
                    # Send key components
                    key_components = [("Sun", six['sun']), ("Moon", six['moon'])]
                    for component_name, sign_data in key_components:
                        sections = await self.generate_component_reading(component_name, sign_data, ctx.author.display_name, birth_info)
                        
                        # Send each section as a separate message
                        for section in sections:
                            if section.strip():
                                await ctx.send(section)
                                await asyncio.sleep(0.5)
                    
                    return
                except Exception:
                    pass  # Fall through to single message
                    
            header_suffix = " (based on your birth chart)"
            user_name = ctx.author.display_name
        elif not sign:
            sign = random.choice(self.zodiac_signs)
            chosen_randomly = True
            header_suffix = " (randomly chosen - use !setbirthday for personalized readings)"
            user_name = sign
        else:
            sign = sign.capitalize()
            header_suffix = ""
            user_name = sign
            if sign not in self.zodiac_signs:
                await ctx.send(f"```\nUnknown zodiac sign: {sign}\nValid signs: {', '.join(self.zodiac_signs)}\n```")
                return
        
        # Fallback to single-message basic reading
        await ctx.send(f"```\n🌟 {reading_type.capitalize()} Reading for {user_name} 🌟{header_suffix if not chosen_randomly else header_suffix}\n\nBasic {sign} reading - use !setbirthday with your birth location for detailed multi-part readings!\n\n✨ The stars await your complete birth information to reveal deeper truths... ✨\n```")

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
            
            # Use Kerykeion to get coordinates and timezone from location
            try:
                # Try different location formats for better compatibility
                locations_to_try = [location]
                
                # If the format is "City, State, Country", try variations
                if ", " in location:
                    parts = [p.strip() for p in location.split(',')]
                    if len(parts) >= 3:
                        city, state, country = parts[0], parts[1], parts[2]
                        # Try different formats
                        locations_to_try.extend([
                            f"{city}, {state}",  # Just city and state
                            f"{city}, {country}",  # City and country
                            city,  # Just city name
                        ])
                
                temp_subj = None
                last_error = None
                
                # Try each location format until one works
                for loc_attempt in locations_to_try:
                    try:
                        temp_subj = AstrologicalSubject(
                            name="temp",
                            year=birthday.year, month=birthday.month, day=birthday.day,
                            hour=birthday.hour, minute=birthday.minute,
                            city=loc_attempt, online=True  # Enable online lookup
                        )
                        # If we get here, the lookup succeeded
                        break
                    except Exception as e:
                        last_error = e
                        continue
                
                if temp_subj is None:
                    raise last_error or Exception("All location formats failed")
                
                # Extract the coordinates and timezone that Kerykeion found
                lat = temp_subj.lat
                lon = temp_subj.lng
                tz_str = temp_subj.tz_str
                
                # Store deterministic birth data with Kerykeion's coordinates
                self.user_birth_data[user_id] = {
                    'datetime': birthday,
                    'location': location,
                    'lat': lat,
                    'lon': lon,
                    'tz_str': tz_str
                }
                
                # Compute natal chart to get accurate sign using exact coordinates
                natal_data = self.compute_natal(
                    name=ctx.author.display_name,
                    y=birthday.year, m=birthday.month, d=birthday.day,
                    hh=birthday.hour, mm=birthday.minute,
                    lat=lat, lon=lon, tz_str=tz_str
                )
                sun_sign = self.sign_map.get(natal_data['natal']['six']['sun']['sign'], natal_data['natal']['six']['sun']['sign'])
                
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
                
            except Exception as e:
                await ctx.send(
                    f"```\nError looking up location: {location}\n"
                    f"Please try a more specific location like:\n"
                    f"• \"Phoenix, Arizona, USA\"\n"
                    f"• \"London, England, UK\"\n"
                    f"• \"Toronto, Ontario, Canada\"\n"
                    f"• \"Phoenix, AZ\" (without country)\n"
                    f"• \"Phoenix\" (city name only)\n"
                    f"Error details: No data found for this city, try again! Maybe check your connection?\n```"
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
                "!setbirthday YYYY-MM-DD HH:MM \"City, State, Country\"\n"
                "Example: !setbirthday 1976-01-27 00:24 \"Phoenix, Arizona, USA\"\n```"
            )
            return
        
        birth_data = self.user_birth_data[user_id]
        birthday = birth_data['datetime']
        
        # Display deterministic coordinates if available
        if 'lat' in birth_data and 'lon' in birth_data:
            lat, lon = birth_data['lat'], birth_data['lon']
            tz_str = birth_data.get('tz_str', 'Unknown')
            
            try:
                natal_data = self.compute_natal(
                    name=ctx.author.display_name,
                    y=birthday.year, m=birthday.month, d=birthday.day,
                    hh=birthday.hour, mm=birthday.minute,
                    lat=lat, lon=lon, tz_str=tz_str
                )
                sun_sign = self.sign_map.get(natal_data['natal']['six']['sun']['sign'], natal_data['natal']['six']['sun']['sign'])
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
            await ctx.send("```\n🌟 Birth information removed successfully\n```")
        else:
            await ctx.send("```\nNo birth information found to remove\n```")

    @commands.command(name='settimezone')
    async def set_timezone(self, ctx, tz_string: str = None):
        """Set or update your timezone for more accurate readings.
        
        Examples: America/New_York, Europe/London, Asia/Tokyo, Australia/Sydney
        Use !listtimezones for common timezone names.
        """
        user_id = ctx.author.id
        
        if user_id not in self.user_birth_data:
            await ctx.send("```\nPlease set your birth information first using:\n"
                          "!setbirthday YYYY-MM-DD HH:MM \"City, State, Country\"\n```")
            return
        
        if not tz_string:
            await ctx.send("```\nPlease provide a timezone string. Examples:\n"
                          "!settimezone America/New_York\n"
                          "!settimezone Europe/London\n"
                          "!settimezone Asia/Tokyo\n"
                          "Use !listtimezones for more options\n```")
            return
        
        try:
            # Test if the timezone is valid by creating a datetime with it
            from zoneinfo import ZoneInfo
            test_zone = ZoneInfo(tz_string)
            
            # Update the user's timezone
            self.user_birth_data[user_id]['tz_str'] = tz_string
            
            await ctx.send(f"```\n🌟 Timezone updated to {tz_string}\n"
                          f"Use !mybirthday to verify your updated info\n```")
            
        except Exception as e:
            await ctx.send(f"```\nInvalid timezone: {tz_string}\n"
                          f"Please use a valid timezone string like:\n"
                          f"America/New_York, Europe/London, Asia/Tokyo\n"
                          f"Use !listtimezones for more options\n```")

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
        signs_list = "\n".join([f"• {sign}" for sign in self.zodiac_signs])
        types_list = "\n".join([f"• {rtype}" for rtype in self.reading_types])
        
        info_message = (
            "🌟 Astrologer Commands 🌟\n\n"
            "READINGS:\n"
            "• !astrology [reading_type] [sign_override]\n"
            "• !horoscope, !stars (aliases)\n\n"
            "PERSONAL DATA:\n"
            "• !setbirthday YYYY-MM-DD HH:MM \"Location\"\n"
            "• !mybirthday (view your info)\n"
            "• !removebirthday\n"
            "• !settimezone [timezone] (adjust timezone)\n"
            "• !listtimezones (common timezones)\n\n"
            "CHARTS:\n"
            "• !natalchart (detailed birth chart)\n\n"
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
        """Get detailed natal chart with deterministic Kerykeion computation."""
        user_id = ctx.author.id
        
        if user_id not in self.user_birth_data:
            await ctx.send(
                "```\nNo birth information set. Use the command:\n"
                "!setbirthday YYYY-MM-DD HH:MM \"City, State, Country\"\n"
                "Example: !setbirthday 1976-01-27 00:24 \"Phoenix, Arizona, USA\"\n```"
            )
            return
        
        birth_data = self.user_birth_data[user_id]
        
        # Ensure we have deterministic coordinates
        if 'lat' not in birth_data or 'lon' not in birth_data:
            await ctx.send("```\nOld birth data format. Please reset with coordinates:\n"
                          "!setbirthday YYYY-MM-DD HH:MM \"City, State, Country\"\n```")
            return
        
        try:
            birthday = birth_data['datetime']
            natal_data = self.compute_natal(
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
                f"☀️ Sun: {self.sign_map.get(six['sun']['sign'], six['sun']['sign'])}\n"
                f"🌙 Moon: {self.sign_map.get(six['moon']['sign'], six['moon']['sign'])}\n"
                f"⬆️ Rising: {self.sign_map.get(six['asc']['sign'], six['asc']['sign'])}\n\n"
                f"PLANETS:\n"
                f"☿ Mercury: {self.sign_map.get(six['mercury']['sign'], six['mercury']['sign'])}\n"
                f"♀ Venus: {self.sign_map.get(six['venus']['sign'], six['venus']['sign'])}\n"
                f"♂ Mars: {self.sign_map.get(six['mars']['sign'], six['mars']['sign'])}\n\n"
                f"HOUSES:\n"
                f"1st House (Self): {self.sign_map.get(houses['1']['sign'], houses['1']['sign'])}\n"
                f"4th House (Home): {self.sign_map.get(houses['4']['sign'], houses['4']['sign'])}\n"
                f"7th House (Relationships): {self.sign_map.get(houses['7']['sign'], houses['7']['sign'])}\n"
                f"10th House (Career): {self.sign_map.get(houses['10']['sign'], houses['10']['sign'])}\n\n"
                f"tropical • placidus • true node • engine=kerykeion@4.26.3"
            )
            
            await ctx.send(f"```\n{chart_info}\n```")
            
        except Exception as e:
            await ctx.send(f"```\nError generating natal chart: {e}\n"
                          f"Please check your birth information and try again.\n```")

async def setup(bot):
    await bot.add_cog(Astrologer(bot))