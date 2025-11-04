# -*- coding: utf-8 -*-
"""
Geocoding module for Astrologer cog.
Handles location lookups, coordinate validation, and timezone management.
"""
import json
import logging
import requests
from typing import Optional, Tuple
from timezonefinder import TimezoneFinder

from .astrologer_data import load_timezone_regions, load_manual_coordinates

logger = logging.getLogger('astrologer.geocoding')


class GeocodingService:
    """Service for geocoding locations and validating coordinates."""

    def __init__(self, geonames_username: Optional[str] = None):
        """
        Initialize the geocoding service.

        Args:
            geonames_username: Optional Geonames API username
        """
        self.geonames_username = geonames_username
        self.timezone_finder = TimezoneFinder()
        self.timezone_regions = load_timezone_regions()
        self.manual_coords = load_manual_coordinates()

        if geonames_username:
            logger.info(f"GeocodingService initialized with Geonames username: {geonames_username}")
        else:
            logger.warning("GeocodingService initialized without Geonames username - using manual lookups only")

    def validate_coordinates_timezone(
        self,
        lat: float,
        lon: float,
        tz_str: str,
        original_location: Optional[str] = None
    ) -> bool:
        """
        Validate that coordinates roughly match timezone region and original location context.

        Args:
            lat: Latitude
            lon: Longitude
            tz_str: Timezone string
            original_location: Original location string for context validation

        Returns:
            True if coordinates and timezone are consistent
        """
        # Check if original location suggests a different region than returned timezone
        if original_location:
            location_lower = original_location.lower()

            # US location indicators - only countries/states, not cities
            us_indicators = ['usa', 'united states', 'america', 'arizona', 'california',
                           'texas', 'florida', 'new york', 'illinois', 'nevada', 'washington']
            # European location indicators - only countries, not cities
            europe_indicators = ['uk', 'united kingdom', 'england', 'britain', 'france',
                                'germany', 'italy', 'spain', 'netherlands', 'belgium']

            input_suggests_us = any(indicator in location_lower for indicator in us_indicators)
            input_suggests_europe = any(indicator in location_lower for indicator in europe_indicators)

            timezone_suggests_us = tz_str.startswith('America/')
            timezone_suggests_europe = tz_str.startswith('Europe/')

            logger.debug(f"Location context analysis:")
            logger.debug(f"  - Input suggests US: {input_suggests_us}")
            logger.debug(f"  - Input suggests Europe: {input_suggests_europe}")
            logger.debug(f"  - Timezone suggests US: {timezone_suggests_us}")
            logger.debug(f"  - Timezone suggests Europe: {timezone_suggests_europe}")

            # Major region mismatch detection
            if input_suggests_us and timezone_suggests_europe:
                logger.error(f"MAJOR MISMATCH - US location input returned European timezone!")
                return False
            if input_suggests_europe and timezone_suggests_us:
                logger.error(f"MAJOR MISMATCH - European location input returned US timezone!")
                return False

        # Get expected region for timezone
        region = self.timezone_regions.get(tz_str)
        if not region:
            # If timezone not in our validation map, do basic sanity check
            return -90 <= lat <= 90 and -180 <= lon <= 180

        lat_min, lat_max = region['lat_range']
        lon_min, lon_max = region['lon_range']

        # Check if coordinates fall within expected region
        lat_valid = lat_min <= lat <= lat_max
        lon_valid = lon_min <= lon <= lon_max

        logger.debug(f"Timezone validation for {tz_str}:")
        logger.debug(f"  - Expected lat range: {lat_min} to {lat_max}, actual: {lat} ({'PASS' if lat_valid else 'FAIL'})")
        logger.debug(f"  - Expected lon range: {lon_min} to {lon_max}, actual: {lon} ({'PASS' if lon_valid else 'FAIL'})")

        return lat_valid and lon_valid

    def geonames_api_geocode(self, location_str: str) -> Optional[Tuple[float, float, str]]:
        """
        Direct Geonames API geocoding with proper error handling.

        Args:
            location_str: Location string to geocode

        Returns:
            Tuple of (latitude, longitude, timezone) or None if failed
        """
        if not self.geonames_username:
            logger.debug("No Geonames username configured, skipping API call")
            return None

        try:
            # Clean location string for API call
            location_query = location_str.strip()
            logger.debug(f"Calling Geonames API for: '{location_query}'")

            # Geonames API search endpoint
            url = "http://api.geonames.org/searchJSON"
            params = {
                'q': location_query,
                'maxRows': 5,
                'username': self.geonames_username,
                'featureClass': 'P',  # Populated places (cities, towns, villages)
                'orderby': 'relevance'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Geonames API response: {json.dumps(data, indent=2)}")

            if 'geonames' not in data or not data['geonames']:
                logger.debug(f"No results found for '{location_query}'")
                return None

            # Get the best result
            result = data['geonames'][0]
            lat = float(result['lat'])
            lon = float(result['lng'])

            # Get timezone using timezonefinder
            timezone_str = self.timezone_finder.timezone_at(lat=lat, lng=lon)
            if not timezone_str:
                logger.debug(f"Could not determine timezone for {lat}, {lon}")
                timezone_str = "UTC"

            logger.debug(f"Geonames API success: {result['name']}, {result.get('adminName1', '')}, "
                        f"{result.get('countryName', '')} -> {lat}, {lon}, {timezone_str}")
            return lat, lon, timezone_str

        except requests.exceptions.RequestException as e:
            logger.error(f"Geonames API request error: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Geonames API response parsing error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected Geonames API error: {e}")
            return None

    def manual_location_lookup(self, location_str: str) -> Optional[Tuple[float, float, str]]:
        """
        Manual coordinate lookup for common locations when geocoding fails.

        Args:
            location_str: Location string to look up

        Returns:
            Tuple of (latitude, longitude, timezone) or None if not found
        """
        # Normalize location string for lookup
        location_lower = location_str.lower().strip()

        # Direct lookup
        if location_lower in self.manual_coords:
            lat, lon, tz = self.manual_coords[location_lower]
            logger.debug(f"Manual lookup SUCCESS for '{location_str}' -> {lat}, {lon}, {tz}")
            return (lat, lon, tz)

        # Partial matching for variations
        for key, (lat, lon, tz) in self.manual_coords.items():
            # Check if location contains key words
            key_words = key.replace(',', '').split()
            location_words = location_lower.replace(',', '').split()

            # If all key words are found in location (match first 2 words: city, state/country)
            if all(word in location_words for word in key_words[:2]):
                logger.debug(f"Manual partial match SUCCESS for '{location_str}' -> '{key}' -> {lat}, {lon}, {tz}")
                return (lat, lon, tz)

        logger.debug(f"Manual lookup FAILED for '{location_str}' - no match found")
        return None

    def geocode(self, location_str: str) -> Optional[Tuple[float, float, str]]:
        """
        Geocode a location string using multiple strategies.

        Tries in order:
        1. Geonames API (if username configured)
        2. Manual coordinate database

        Args:
            location_str: Location string to geocode

        Returns:
            Tuple of (latitude, longitude, timezone) or None if all methods fail
        """
        logger.debug(f"Geocoding location: '{location_str}'")

        # Try Geonames API first
        result = self.geonames_api_geocode(location_str)
        if result:
            return result

        # Fall back to manual lookup
        logger.debug("Geonames API failed or not configured, trying manual lookup")
        result = self.manual_location_lookup(location_str)
        if result:
            return result

        logger.warning(f"All geocoding methods failed for: '{location_str}'")
        return None
