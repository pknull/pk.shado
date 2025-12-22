"""
AAS Dice Roller

Call of Cthulhu 7e percentile dice mechanics with bonus/penalty dice support.
Uses rpg-dice library for roll execution.
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, Tuple
from dice_roller.DiceThrower import DiceThrower

from .data import (
    SuccessLevel,
    get_success_level,
    SUCCESS_DISPLAY,
)

logger = logging.getLogger('aas.roller')


@dataclass
class RollResult:
    """Result of a skill or characteristic check."""
    roll: int                    # Final d100 result
    target: int                  # Target value to roll against
    success_level: str           # SuccessLevel constant
    difficulty: str              # regular, hard, extreme
    bonus_dice: int              # Number of bonus dice applied
    penalty_dice: int            # Number of penalty dice applied
    tens_rolls: list[int]        # All tens digit rolls (for display)
    units_roll: int              # The units digit roll
    skill_name: str              # Name of skill/characteristic
    is_base: bool                # True if using base/default value
    is_custom: bool              # True if custom skill (not standard)

    @property
    def success_text(self) -> str:
        """Human-readable success level."""
        return SUCCESS_DISPLAY.get(self.success_level, "Unknown")

    @property
    def effective_target(self) -> int:
        """Target value after difficulty adjustment."""
        if self.difficulty == "hard":
            return max(1, self.target // 2)
        elif self.difficulty == "extreme":
            return max(1, self.target // 5)
        return self.target

    @property
    def is_success(self) -> bool:
        """True if roll succeeded at any level."""
        return self.success_level in (
            SuccessLevel.CRITICAL,
            SuccessLevel.EXTREME,
            SuccessLevel.HARD,
            SuccessLevel.REGULAR,
        )


def parse_modifier(modifier: str) -> Tuple[int, int]:
    """
    Parse a modifier string into bonus/penalty dice counts.

    Args:
        modifier: String like "+1", "-2", "+2", etc.

    Returns:
        Tuple of (bonus_dice, penalty_dice)
    """
    if not modifier:
        return (0, 0)

    match = re.match(r'^([+-])(\d+)$', modifier.strip())
    if not match:
        return (0, 0)

    sign, count = match.groups()
    count = int(count)

    if sign == '+':
        return (count, 0)
    else:
        return (0, count)


def roll_d100(bonus_dice: int = 0, penalty_dice: int = 0) -> Tuple[int, list[int], int]:
    """
    Roll a d100 with optional bonus/penalty dice.

    Bonus dice: roll extra tens digits, keep lowest.
    Penalty dice: roll extra tens digits, keep highest.
    These cancel out 1:1.

    Args:
        bonus_dice: Number of bonus dice to add
        penalty_dice: Number of penalty dice to add

    Returns:
        Tuple of (final_roll, all_tens_rolls, units_roll)
    """
    thrower = DiceThrower()

    # Roll units digit (0-9, where 0 = 10 for purposes of 00+0=100)
    units_result = thrower.throw("1d10")
    # DiceThrower returns {'natural': [list], 'modified': [list], 'total': str}
    if isinstance(units_result, dict) and units_result.get('natural'):
        units = units_result['natural'][0]  # Get first die result
    else:
        units = 0
    # d10 gives 1-10, we need 0-9 for units
    units = units % 10  # Convert: 10→0, 1-9 stay same

    # Calculate net dice modifier
    net_modifier = bonus_dice - penalty_dice

    # Roll tens digits
    if net_modifier > 0:
        # Bonus: roll extra, keep lowest
        dice_count = 1 + net_modifier
        tens_notation = f"{dice_count}d10kl1"
    elif net_modifier < 0:
        # Penalty: roll extra, keep highest
        dice_count = 1 + abs(net_modifier)
        tens_notation = f"{dice_count}d10kh1"
    else:
        # No modifier: single tens die
        tens_notation = "1d10"

    tens_result = thrower.throw(tens_notation)

    if isinstance(tens_result, dict):
        # 'natural' is list of all dice rolled
        # 'modified' is list of kept dice after kl/kh
        tens_rolls = tens_result.get('natural', [0])
        kept_list = tens_result.get('modified', tens_rolls)
        kept_tens = kept_list[0] if kept_list else 0
    else:
        tens_rolls = [0]
        kept_tens = 0

    # Convert tens: 10→0 (representing 00)
    kept_tens = kept_tens % 10
    tens_rolls = [t % 10 for t in tens_rolls]

    # Calculate final roll
    # 00 + 0 = 100, otherwise tens*10 + units
    if kept_tens == 0 and units == 0:
        final_roll = 100
    else:
        final_roll = (kept_tens * 10) + units
        if final_roll == 0:
            final_roll = 100  # 00 + 10 case

    return (final_roll, tens_rolls, units)


def skill_check(
    skill_name: str,
    skill_value: int,
    difficulty: str = "regular",
    bonus_dice: int = 0,
    penalty_dice: int = 0,
    is_base: bool = False,
    is_custom: bool = False,
) -> RollResult:
    """
    Perform a skill check.

    Args:
        skill_name: Name of the skill being tested
        skill_value: Current skill value (0-100)
        difficulty: "regular", "hard", or "extreme"
        bonus_dice: Number of bonus dice
        penalty_dice: Number of penalty dice
        is_base: True if this is an untrained skill using base value
        is_custom: True if this is a custom (non-standard) skill

    Returns:
        RollResult with all roll details
    """
    # Calculate effective target based on difficulty
    if difficulty == "hard":
        target = max(1, skill_value // 2)
    elif difficulty == "extreme":
        target = max(1, skill_value // 5)
    else:
        target = skill_value

    # Roll the dice
    roll, tens_rolls, units = roll_d100(bonus_dice, penalty_dice)

    # Determine success level (always against full skill for level determination)
    success_level = get_success_level(roll, target)

    return RollResult(
        roll=roll,
        target=skill_value,
        success_level=success_level,
        difficulty=difficulty,
        bonus_dice=bonus_dice,
        penalty_dice=penalty_dice,
        tens_rolls=tens_rolls,
        units_roll=units,
        skill_name=skill_name,
        is_base=is_base,
        is_custom=is_custom,
    )


def characteristic_check(
    char_name: str,
    char_value: int,
    difficulty: str = "regular",
    bonus_dice: int = 0,
    penalty_dice: int = 0,
) -> RollResult:
    """
    Perform a characteristic check (STR, DEX, etc).
    Same mechanics as skill check.
    """
    return skill_check(
        skill_name=char_name,
        skill_value=char_value,
        difficulty=difficulty,
        bonus_dice=bonus_dice,
        penalty_dice=penalty_dice,
        is_base=False,
        is_custom=False,
    )


def roll_dice(notation: str) -> Optional[dict]:
    """
    Roll dice using rpg-dice notation.
    Wrapper for resource pool changes (1d6 sanity loss, etc).

    Args:
        notation: Dice notation like "1d6", "2d4+1"

    Returns:
        Dict with 'natural' (sum), 'total' (str), 'rolls' (list) keys, or None on error
    """
    try:
        result = DiceThrower().throw(notation)
        if isinstance(result, dict):
            # Convert to simpler format for callers
            # DiceThrower returns: {'natural': [list], 'modified': [list], 'total': str}
            natural_list = result.get('natural', [0])
            modified_list = result.get('modified', natural_list)
            total = int(result.get('total', 0))
            return {
                'natural': total,  # Sum of dice for compatibility
                'modified': total,
                'rolls': natural_list,
                'total': total,
            }
        return None
    except Exception as e:
        logger.error(f"Dice roll error: {e}")
        return None


def format_roll_result(result: RollResult) -> str:
    """
    Format a roll result for display.

    Returns multiline string suitable for Discord message.
    """
    lines = []

    # Header with skill and target
    target_display = result.effective_target
    skill_suffix = ""
    if result.is_base:
        skill_suffix = " (base)"
    elif result.is_custom and result.target == 0:
        skill_suffix = " (unset)"

    if result.difficulty != "regular":
        lines.append(f"**{result.skill_name}** ({result.difficulty.title()}: {target_display}){skill_suffix}")
    else:
        lines.append(f"**{result.skill_name}** ({target_display}){skill_suffix}")

    # Roll result
    lines.append(f"Roll: **{result.roll}** - {result.success_text}")

    # Dice details if bonus/penalty
    if result.bonus_dice > 0:
        tens_str = ", ".join(str(t * 10 if t > 0 else "00") for t in result.tens_rolls)
        lines.append(f"Bonus dice: {result.bonus_dice} (tens: {tens_str})")
    elif result.penalty_dice > 0:
        tens_str = ", ".join(str(t * 10 if t > 0 else "00") for t in result.tens_rolls)
        lines.append(f"Penalty dice: {result.penalty_dice} (tens: {tens_str})")

    return "\n".join(lines)
