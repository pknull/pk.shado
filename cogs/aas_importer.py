"""
AAS Character Importer

Parses Dhole's House JSON exports and converts them to BURGE character format.
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from .aas_data import STANDARD_SKILLS, is_standard_skill

logger = logging.getLogger('aas.importer')


class ImportError(Exception):
    """Raised when import fails."""
    pass


def parse_dholes_house_json(json_data: str) -> Tuple[Dict[str, Any], int]:
    """
    Parse Dhole's House JSON export into BURGE character format.

    Args:
        json_data: Raw JSON string from Dhole's House export

    Returns:
        Tuple of (character_dict, skills_count)

    Raises:
        ImportError: If JSON is invalid or missing required fields
    """
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        raise ImportError(f"Could not parse JSON: {e}")

    # Validate structure
    if "Investigator" not in data:
        raise ImportError("Invalid Dhole's House format: missing Investigator data")

    inv = data["Investigator"]

    # Extract personal details
    personal = inv.get("PersonalDetails", {})
    name = personal.get("Name", "Unknown Investigator")
    occupation = personal.get("Occupation", "")

    # Extract characteristics
    chars = inv.get("Characteristics", {})
    characteristics = {
        "STR": _safe_int(chars.get("STR", 0)),
        "CON": _safe_int(chars.get("CON", 0)),
        "DEX": _safe_int(chars.get("DEX", 0)),
        "SIZ": _safe_int(chars.get("SIZ", 0)),
        "POW": _safe_int(chars.get("POW", 0)),
        "APP": _safe_int(chars.get("APP", 0)),
        "INT": _safe_int(chars.get("INT", 0)),
        "EDU": _safe_int(chars.get("EDU", 0)),
    }

    # Extract resources
    hp_current = _safe_int(chars.get("HitPts", 0))
    hp_max = _safe_int(chars.get("HitPtsMax", 0))
    mp_current = _safe_int(chars.get("MagicPts", 0))
    mp_max = _safe_int(chars.get("MagicPtsMax", 0))
    luck = _safe_int(chars.get("Luck", 0))
    san_current = _safe_int(chars.get("Sanity", 0))
    san_max = _safe_int(chars.get("SanityMax", 99))

    # Calculate HP/MP max from characteristics if not provided
    if hp_max == 0:
        hp_max = (characteristics["CON"] + characteristics["SIZ"]) // 10
    if mp_max == 0:
        mp_max = characteristics["POW"] // 5
    if hp_current == 0:
        hp_current = hp_max
    if mp_current == 0:
        mp_current = mp_max

    # Extract skills
    # Dhole's House format: {"Skills": {"Skill": [...]}}
    skills = {}
    skills_container = inv.get("Skills", {})
    if isinstance(skills_container, dict):
        skills_list = skills_container.get("Skill", [])
    else:
        # Fallback for flat list format
        skills_list = skills_container if isinstance(skills_container, list) else []
    mythos_value = 0

    for skill_entry in skills_list:
        skill_name = skill_entry.get("name", "")
        skill_value = _safe_int(skill_entry.get("value", 0))
        subskill = skill_entry.get("subskill", "None")

        if not skill_name:
            continue

        # Handle subskills (e.g., Science (Chemistry))
        if subskill and subskill != "None":
            full_name = f"{skill_name} ({subskill})"
        else:
            full_name = skill_name

        # Track Cthulhu Mythos for sanity max calculation
        if skill_name == "Cthulhu Mythos":
            mythos_value = skill_value

        # Only store non-zero skills or important ones
        if skill_value > 0:
            is_custom = not is_standard_skill(full_name)
            skills[full_name] = {
                "value": skill_value,
                "checked": False,
                "eligible": False,
                "custom": is_custom,
            }

    # Adjust sanity max for mythos
    if mythos_value > 0:
        san_max = min(san_max, 99 - mythos_value)

    # Build character dict
    now = datetime.now(timezone.utc).isoformat()
    character = {
        "name": name,
        "occupation": occupation,
        "created_at": now,
        "last_updated": now,
        "version": 1,
        "characteristics": characteristics,
        "resources": {
            "hp": {"current": hp_current, "max": hp_max},
            "mp": {"current": mp_current, "max": mp_max},
            "luck": {"current": luck, "starting": luck},
            "sanity": {"current": san_current, "max": san_max, "mythos": mythos_value},
            "xp": 0,
        },
        "skills": skills,
        "conditions": {
            "major_wound": False,
        },
        "pending": [],
        "changelog": [],
    }

    return (character, len(skills))


def export_to_dholes_house(character: Dict[str, Any]) -> str:
    """
    Export BURGE character to Dhole's House compatible JSON format.

    Args:
        character: BURGE character dict

    Returns:
        JSON string in Dhole's House format
    """
    chars = character.get("characteristics", {})
    resources = character.get("resources", {})
    skills = character.get("skills", {})

    # Build skills list with Dhole's House format
    skills_list = []
    for skill_name, skill_data in skills.items():
        value = skill_data.get("value", 0)

        # Parse skill name for potential subskill
        if "(" in skill_name and ")" in skill_name:
            base_name = skill_name.split("(")[0].strip()
            subskill = skill_name.split("(")[1].rstrip(")")
        else:
            base_name = skill_name
            subskill = None

        skill_entry = {
            "name": base_name,
            "value": str(value),
            "half": str(value // 2),
            "fifth": str(value // 5),
        }
        if subskill:
            skill_entry["subskill"] = subskill

        skills_list.append(skill_entry)

    # Values as strings to match Dhole's House format
    hp = resources.get("hp", {})
    mp = resources.get("mp", {})
    luck = resources.get("luck", {})
    san = resources.get("sanity", {})

    dholes_format = {
        "Investigator": {
            "Header": {
                "Title": "Investigator Export: Character Sheet",
                "Creator": "pk.shado Discord Bot",
                "GameName": "Call of Cthulhu TM",
                "GameVersion": "7th Edition",
                "Version": "0.5.0"
            },
            "PersonalDetails": {
                "Name": character.get("name", "Unknown"),
                "Occupation": character.get("occupation", ""),
            },
            "Characteristics": {
                "STR": str(chars.get("STR", 0)),
                "CON": str(chars.get("CON", 0)),
                "DEX": str(chars.get("DEX", 0)),
                "SIZ": str(chars.get("SIZ", 0)),
                "POW": str(chars.get("POW", 0)),
                "APP": str(chars.get("APP", 0)),
                "INT": str(chars.get("INT", 0)),
                "EDU": str(chars.get("EDU", 0)),
                "HitPts": str(hp.get("current", 0)),
                "HitPtsMax": str(hp.get("max", 0)),
                "MagicPts": str(mp.get("current", 0)),
                "MagicPtsMax": str(mp.get("max", 0)),
                "Luck": str(luck.get("current", 0)),
                "Sanity": str(san.get("current", 0)),
                "SanityMax": str(san.get("max", 99)),
            },
            "Skills": {
                "Skill": skills_list
            },
        }
    }

    return json.dumps(dholes_format, indent=2)


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
