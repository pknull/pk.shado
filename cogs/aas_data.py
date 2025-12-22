"""
AAS Character Data Constants

Defines skill defaults, characteristics, and constants for the BURGE
(Call of Cthulhu 7e variant) character management system.

Standard skills have base values that characters roll against if untrained.
Custom skills (not in STANDARD_SKILLS) default to 0.
"""

from typing import Dict, Set

# Characteristics with abbreviations
CHARACTERISTICS: Set[str] = {"STR", "CON", "DEX", "SIZ", "POW", "APP", "INT", "EDU"}

# Resource pools
RESOURCES: Set[str] = {"hp", "mp", "san", "luck", "xp"}

# Standard skills with base values
# Skills not in this dict are treated as custom (base 0)
STANDARD_SKILLS: Dict[str, int] = {
    # Combat
    "Dodge": 0,  # Special: DEX/2, calculated at runtime
    "Fighting (Brawl)": 25,
    "Firearms (Handgun)": 20,
    "Firearms (Rifle/Shotgun)": 25,
    "Throw": 20,

    # Investigation
    "Library Use": 20,
    "Listen": 20,
    "Spot Hidden": 25,
    "Track": 10,

    # Social
    "Charm": 15,
    "Fast Talk": 5,
    "Intimidate": 15,
    "Persuade": 10,
    "Psychology": 10,

    # Technical
    "Art/Craft (Any)": 5,
    "Electrical Repair": 10,
    "First Aid": 30,
    "Locksmith": 1,
    "Mechanical Repair": 10,
    "Medicine": 1,
    "Operate Heavy Machinery": 1,

    # Knowledge
    "Accounting": 5,
    "Anthropology": 1,
    "Appraise": 5,
    "Archaeology": 1,
    "Cthulhu Mythos": 0,  # Cannot have base
    "History": 5,
    "Law": 5,
    "Natural World": 10,
    "Occult": 5,
    "Science (Any)": 1,

    # Languages
    "Language (Own)": 0,  # Special: EDU, calculated at runtime
    "Language (Other)": 1,

    # Physical
    "Climb": 20,
    "Drive Auto": 20,
    "Jump": 20,
    "Pilot (Any)": 1,
    "Ride": 5,
    "Stealth": 20,
    "Swim": 20,

    # Other
    "Credit Rating": 0,
    "Disguise": 5,
    "Navigate": 10,
    "Sleight of Hand": 10,
    "Survival (Any)": 10,
}

# Skill name variations for fuzzy matching
SKILL_ALIASES: Dict[str, str] = {
    "brawl": "Fighting (Brawl)",
    "fight": "Fighting (Brawl)",
    "handgun": "Firearms (Handgun)",
    "pistol": "Firearms (Handgun)",
    "rifle": "Firearms (Rifle/Shotgun)",
    "shotgun": "Firearms (Rifle/Shotgun)",
    "spot": "Spot Hidden",
    "library": "Library Use",
    "firstaid": "First Aid",
    "first-aid": "First Aid",
    "mythos": "Cthulhu Mythos",
    "elec repair": "Electrical Repair",
    "mech repair": "Mechanical Repair",
    "heavy machinery": "Operate Heavy Machinery",
    "own language": "Language (Own)",
    "native language": "Language (Own)",
}


def get_skill_base(skill_name: str, characteristics: Dict[str, int] = None) -> int:
    """
    Get the base value for a skill.

    Args:
        skill_name: Name of the skill
        characteristics: Character's stats for derived bases (Dodge, Language)

    Returns:
        Base skill value (0 for custom/unknown skills)
    """
    # Check aliases first
    normalized = SKILL_ALIASES.get(skill_name.lower(), skill_name)

    # Exact match
    if normalized in STANDARD_SKILLS:
        base = STANDARD_SKILLS[normalized]

        # Calculate derived bases if characteristics provided
        if characteristics:
            if normalized == "Dodge":
                return characteristics.get("DEX", 0) // 2
            elif normalized == "Language (Own)":
                return characteristics.get("EDU", 0)

        return base

    # Partial match for parameterized skills
    for std_skill in STANDARD_SKILLS:
        if std_skill.startswith(normalized.split("(")[0].strip()):
            return STANDARD_SKILLS[std_skill]

    # Custom skill
    return 0


def is_standard_skill(skill_name: str) -> bool:
    """Check if a skill is in the standard list."""
    normalized = SKILL_ALIASES.get(skill_name.lower(), skill_name)
    if normalized in STANDARD_SKILLS:
        return True

    # Check partial match for parameterized skills
    base_name = normalized.split("(")[0].strip()
    return any(s.startswith(base_name) for s in STANDARD_SKILLS)


def normalize_skill_name(skill_name: str) -> str:
    """Normalize skill name using aliases."""
    return SKILL_ALIASES.get(skill_name.lower(), skill_name)


# Derived value formulas
def calc_hp_max(con: int, siz: int) -> int:
    """HP Max = (CON + SIZ) // 10"""
    return (con + siz) // 10


def calc_mp_max(pow_stat: int) -> int:
    """MP Max = POW // 5"""
    return pow_stat // 5


def calc_sanity_max(mythos: int = 0) -> int:
    """Sanity Max = 99 - Cthulhu Mythos skill"""
    return 99 - mythos


def calc_major_wound_threshold(con: int) -> int:
    """Major wound threshold = CON // 2"""
    return con // 2


# Success level thresholds
class SuccessLevel:
    """Constants for roll success levels."""
    CRITICAL = "critical"      # Roll of 01
    EXTREME = "extreme"        # Roll <= skill/5
    HARD = "hard"              # Roll <= skill/2
    REGULAR = "regular"        # Roll <= skill
    FAILURE = "failure"        # Roll > skill
    FUMBLE = "fumble"          # Roll of 100, or 96-99 when skill < 50


def get_success_level(roll: int, skill: int) -> str:
    """
    Determine success level for a d100 roll against a skill.

    Args:
        roll: The d100 result (1-100)
        skill: The target skill value

    Returns:
        Success level constant
    """
    # Critical success
    if roll == 1:
        return SuccessLevel.CRITICAL

    # Fumble: 100 always, or 96-99 when skill < 50
    if roll == 100 or (skill < 50 and roll >= 96):
        return SuccessLevel.FUMBLE

    # Success thresholds
    extreme_threshold = max(1, skill // 5)
    hard_threshold = max(1, skill // 2)

    if roll <= extreme_threshold:
        return SuccessLevel.EXTREME
    elif roll <= hard_threshold:
        return SuccessLevel.HARD
    elif roll <= skill:
        return SuccessLevel.REGULAR
    else:
        return SuccessLevel.FAILURE


# Display formatting
SUCCESS_DISPLAY = {
    SuccessLevel.CRITICAL: "Critical Success!",
    SuccessLevel.EXTREME: "Extreme Success!",
    SuccessLevel.HARD: "Hard Success",
    SuccessLevel.REGULAR: "Success",
    SuccessLevel.FAILURE: "Failure",
    SuccessLevel.FUMBLE: "Fumble!",
}
