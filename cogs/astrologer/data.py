# -*- coding: utf-8 -*-
"""
Data management module for Astrologer cog.
Handles loading external data files and provides constants.
"""
import json
import os
from typing import Dict, Tuple, List

# Config files are in the same directory as this module
DATA_DIR = os.path.dirname(__file__)

def load_timezone_regions() -> Dict[str, Dict[str, List[float]]]:
    """Load timezone region validation data from JSON."""
    filepath = os.path.join(DATA_DIR, 'timezone_regions.json')
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback to hardcoded minimal data
        return {
            'UTC': {'lat_range': [-90, 90], 'lon_range': [-180, 180]}
        }

def load_manual_coordinates() -> Dict[str, Tuple[float, float, str]]:
    """Load manual coordinate database from JSON."""
    filepath = os.path.join(DATA_DIR, 'manual_coordinates.json')
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            # Convert lists to tuples for consistency
            return {k: tuple(v) for k, v in data.items()}
    except FileNotFoundError:
        # Fallback to empty dict
        return {}

# Zodiac sign constants
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Sign mapping for Kerykeion abbreviated to full names
SIGN_MAP = {
    'Ari': 'Aries', 'Tau': 'Taurus', 'Gem': 'Gemini',
    'Can': 'Cancer', 'Leo': 'Leo', 'Vir': 'Virgo',
    'Lib': 'Libra', 'Sco': 'Scorpio', 'Sag': 'Sagittarius',
    'Cap': 'Capricorn', 'Aqu': 'Aquarius', 'Pis': 'Pisces'
}

# Zodiac date ranges (month_start, day_start, month_end, day_end)
ZODIAC_DATES = [
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

# Reading types for horoscopes
READING_TYPES = [
    "daily", "weekly", "monthly", "love", "career", "health", "spiritual"
]

# House system mappings for Kerykeion
HOUSE_SYSTEM_MAP = {
    "placidus": "P",
    "koch": "K",
    "regiomontanus": "R",
    "campanus": "C",
    "equal": "A",
    "whole_sign": "W"
}

# Zodiac type mappings for Kerykeion
ZODIAC_TYPE_MAP = {
    "tropical": "Tropic",
    "sidereal": "Sidereal"
}

# Component descriptions for readings
COMPONENT_INFO = {
    "Rising": {
        "icon": "🌅⚖️",
        "title": "THE RISING VEIL OF DESTINY",
        "description": "your outward mask and first impressions"
    },
    "Sun": {
        "icon": "☀️🔥",
        "title": "THE SOLAR FLAME OF ESSENCE",
        "description": "your core identity and life force"
    },
    "Moon": {
        "icon": "🌙✨",
        "title": "THE LUNAR TIDES OF EMOTION",
        "description": "your inner world and emotional nature"
    },
    "Mercury": {
        "icon": "☿️💫",
        "title": "THE MERCURIAL VOICE OF MIND",
        "description": "your communication and thought patterns"
    },
    "Venus": {
        "icon": "♀️💖",
        "title": "THE VENUSIAN DANCE OF LOVE",
        "description": "your relationships and aesthetic nature"
    },
    "Mars": {
        "icon": "♂️⚔️",
        "title": "THE MARTIAN FIRE OF ACTION",
        "description": "your drive and how you pursue desires"
    }
}
