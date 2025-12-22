# -*- coding: utf-8 -*-
"""
Core astrological computation module.
Handles natal chart computation, transits, and validation.
"""
import hashlib
import json
import logging
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from kerykeion import AstrologicalSubject, KerykeionChartSVG
import cairosvg

from .data import SIGN_MAP, HOUSE_SYSTEM_MAP, ZODIAC_TYPE_MAP

logger = logging.getLogger('astrologer.core')


class AstrologicalComputer:
    """Handles astrological computations, caching, and chart generation."""

    def __init__(self):
        """Initialize the astrological computer."""
        self.natal_cache: Dict[str, Dict[str, Any]] = {}
        self.transit_cache: Dict[str, Dict[str, Any]] = {}

    def angdiff(self, a: float, b: float) -> float:
        """
        Calculate angular difference between two degrees (0-360).

        Args:
            a: First angle in degrees
            b: Second angle in degrees

        Returns:
            Angular difference in degrees
        """
        d = (a - b) % 360.0
        return 360.0 - d if d > 180 else d

    def cache_key_natal(
        self,
        name: str,
        y: int,
        m: int,
        d: int,
        hh: int,
        mm: int,
        lat: float,
        lon: float,
        tz_str: str,
        house_system: str,
        zodiac_type: str,
        node_type: str
    ) -> str:
        """
        Generate deterministic cache key for natal chart.

        Returns:
            16-character hex hash
        """
        key_data = {
            "name": name,
            "datetime": f"{y:04d}-{m:02d}-{d:02d}T{hh:02d}:{mm:02d}",
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "tz": tz_str,
            "house": house_system,
            "zodiac": zodiac_type,
            "node": node_type
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def cache_key_transits(self, timestamp_bucket: int, lat: float, lon: float) -> str:
        """
        Generate cache key for transits (bucketed by time).

        Args:
            timestamp_bucket: Time bucket (e.g., 5-minute intervals)
            lat: Latitude
            lon: Longitude

        Returns:
            16-character hex hash
        """
        key_data = {
            "bucket": timestamp_bucket,
            "lat": round(lat, 6),
            "lon": round(lon, 6)
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def transit_time_bucket(self, timestamp: datetime, bucket_seconds: int = 300) -> int:
        """
        Bucket timestamp for transit caching (default: 5 minutes).

        Args:
            timestamp: Datetime to bucket
            bucket_seconds: Bucket size in seconds

        Returns:
            Bucket number
        """
        return int(timestamp.timestamp()) // bucket_seconds

    def validate_natal_chart(self, natal_data: Dict[str, Any]) -> None:
        """
        Run mathematical validations on natal chart.

        Validates:
        - Mercury within 28.5° of Sun
        - Venus within 47.5° of Sun
        - ASC/DSC opposition (180° ± 0.5°)
        - MC/IC opposition (180° ± 0.5°)

        Args:
            natal_data: Natal chart data dictionary

        Raises:
            ValueError: If validation fails
        """
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

    def compute_natal(
        self,
        name: str,
        y: int,
        m: int,
        d: int,
        hh: int,
        mm: int,
        lat: float,
        lon: float,
        tz_str: str,
        house_system: str = "placidus",
        zodiac_type: str = "tropical",
        node_type: str = "true"
    ) -> Dict[str, Any]:
        """
        Compute deterministic natal chart using Kerykeion with caching.

        Args:
            name: Subject name
            y, m, d: Birth date (year, month, day)
            hh, mm: Birth time (hour, minute)
            lat, lon: Birth location coordinates
            tz_str: Timezone string
            house_system: House system (default: placidus)
            zodiac_type: Zodiac type (default: tropical)
            node_type: Node type (default: true)

        Returns:
            Dictionary containing natal chart data
        """
        # Check cache first
        cache_key = self.cache_key_natal(name, y, m, d, hh, mm, lat, lon, tz_str,
                                         house_system, zodiac_type, node_type)
        if cache_key in self.natal_cache:
            logger.debug(f"Cache hit for natal chart: {cache_key}")
            return self.natal_cache[cache_key]

        logger.debug(f"Computing natal chart for {name} at {y}-{m}-{d} {hh}:{mm}")

        # Map house system to Kerykeion identifier
        house_id = HOUSE_SYSTEM_MAP.get(house_system.lower(), "P")

        # Map zodiac type
        zodiac_kery = ZODIAC_TYPE_MAP.get(zodiac_type.lower(), "Tropic")

        subj = AstrologicalSubject(
            name=name,
            year=y, month=m, day=d, hour=hh, minute=mm,
            city=None, nation=None,  # Force manual coordinates
            lat=lat, lng=lon, tz_str=tz_str,
            houses_system_identifier=house_id,
            zodiac_type=zodiac_kery,
            online=False  # Disable online lookups for deterministic results
        )

        # Extract core planetary positions
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
        logger.debug(f"Cached natal chart: {cache_key}")
        return result

    def compute_transits_now(self, lat: float, lon: float, tz_str: str) -> Dict[str, Any]:
        """
        Compute current transiting planets with caching.

        Args:
            lat, lon: Location coordinates
            tz_str: Timezone string

        Returns:
            Dictionary containing current transits
        """
        now = datetime.now(timezone.utc)

        # Check cache (5-minute buckets)
        bucket = self.transit_time_bucket(now, 300)
        cache_key = self.cache_key_transits(bucket, lat, lon)
        if cache_key in self.transit_cache:
            logger.debug(f"Cache hit for transits: {cache_key}")
            return self.transit_cache[cache_key]

        logger.debug(f"Computing transits for {now.isoformat()}")

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
        logger.debug(f"Cached transits: {cache_key}")
        return result

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing/replacing problematic characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        sanitized = re.sub(r'[^\w\s-]', '', filename)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        return sanitized.strip('_')

    def generate_chart_svg(
        self,
        name: str,
        y: int,
        m: int,
        d: int,
        hh: int,
        mm: int,
        lat: float,
        lon: float,
        tz_str: str
    ) -> Optional[str]:
        """
        Generate SVG natal chart using Kerykeion.

        Args:
            name: Subject name
            y, m, d: Birth date
            hh, mm: Birth time
            lat, lon: Birth coordinates
            tz_str: Timezone

        Returns:
            Path to generated SVG file or None if failed
        """
        try:
            logger.debug(f"Generating SVG chart for {name} at {lat}, {lon}")

            # Create AstrologicalSubject
            subject = AstrologicalSubject(
                name=name,
                year=y, month=m, day=d, hour=hh, minute=mm,
                lat=lat, lng=lon, tz_str=tz_str,
                online=False
            )

            logger.debug(f"Successfully created AstrologicalSubject for SVG generation")
            logger.debug(f"Subject coordinates: lat={subject.lat}, lng={subject.lng}")

            # Generate the SVG chart
            chart_generator = KerykeionChartSVG(subject)
            chart_generator.makeSVG()

            # Kerykeion saves files as "{name} - Natal Chart.svg" in the home directory
            expected_svg_path = os.path.expanduser(f"~/{name} - Natal Chart.svg")
            logger.debug(f"Expected SVG path: {expected_svg_path}")

            # Validate SVG file was created
            if os.path.exists(expected_svg_path):
                logger.debug(f"SVG chart successfully generated at: {expected_svg_path}")
                return expected_svg_path
            else:
                logger.debug(f"SVG file not found at expected location: {expected_svg_path}")
                # Check fallback location
                fallback_path = f"{name} - Natal Chart.svg"
                if os.path.exists(fallback_path):
                    logger.debug(f"Found SVG at fallback location: {fallback_path}")
                    return fallback_path
                return None

        except Exception as e:
            logger.error(f"Error generating SVG chart: {e}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return None
