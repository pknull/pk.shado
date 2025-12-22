"""
Test suite for AAS dice roller mechanics.

Tests CoC d100 mechanics, bonus/penalty dice, skill checks,
and roll result formatting.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogs.aas_roller import (
    parse_modifier,
    roll_d100,
    skill_check,
    characteristic_check,
    roll_dice,
    format_roll_result,
    RollResult,
)
from cogs.aas_data import SuccessLevel


class TestParseModifier:
    """Tests for modifier string parsing."""

    def test_positive_modifier(self):
        """Positive modifiers give bonus dice."""
        assert parse_modifier("+1") == (1, 0)
        assert parse_modifier("+2") == (2, 0)
        assert parse_modifier("+5") == (5, 0)

    def test_negative_modifier(self):
        """Negative modifiers give penalty dice."""
        assert parse_modifier("-1") == (0, 1)
        assert parse_modifier("-2") == (0, 2)
        assert parse_modifier("-3") == (0, 3)

    def test_none_modifier(self):
        """None returns no modifiers."""
        assert parse_modifier(None) == (0, 0)

    def test_empty_string(self):
        """Empty string returns no modifiers."""
        assert parse_modifier("") == (0, 0)

    def test_invalid_format(self):
        """Invalid format returns no modifiers."""
        assert parse_modifier("abc") == (0, 0)
        assert parse_modifier("1") == (0, 0)
        assert parse_modifier("++1") == (0, 0)

    def test_whitespace_handling(self):
        """Whitespace should be handled."""
        assert parse_modifier(" +1 ") == (1, 0)
        assert parse_modifier(" -2 ") == (0, 2)


class TestRollD100:
    """Tests for d100 roll mechanics."""

    def test_roll_in_valid_range(self):
        """Rolls should be 1-100."""
        for _ in range(100):
            roll, tens, units = roll_d100()
            assert 1 <= roll <= 100, f"Roll {roll} out of range"

    def test_returns_tens_and_units(self):
        """Should return tens rolls and units roll."""
        roll, tens_rolls, units = roll_d100()
        assert isinstance(tens_rolls, list)
        assert len(tens_rolls) >= 1
        assert isinstance(units, int)
        assert 0 <= units <= 9

    def test_bonus_dice_multiple_tens(self):
        """Bonus dice should roll extra tens."""
        roll, tens_rolls, units = roll_d100(bonus_dice=2)
        assert len(tens_rolls) == 3  # 1 base + 2 bonus

    def test_penalty_dice_multiple_tens(self):
        """Penalty dice should roll extra tens."""
        roll, tens_rolls, units = roll_d100(penalty_dice=2)
        assert len(tens_rolls) == 3  # 1 base + 2 penalty

    def test_bonus_and_penalty_cancel(self):
        """Bonus and penalty should cancel out."""
        roll, tens_rolls, units = roll_d100(bonus_dice=2, penalty_dice=2)
        assert len(tens_rolls) == 1  # Net zero


class TestRollD100Statistical:
    """Statistical tests for dice fairness (run many times)."""

    def test_roll_distribution_reasonable(self):
        """Rolls should be roughly uniformly distributed."""
        rolls = [roll_d100()[0] for _ in range(1000)]

        # Check we get values across the range
        assert min(rolls) <= 10, "Should see low rolls"
        assert max(rolls) >= 90, "Should see high rolls"

        # Mean should be roughly 50
        mean = sum(rolls) / len(rolls)
        assert 40 < mean < 60, f"Mean {mean} seems biased"

    def test_bonus_dice_favor_lower(self):
        """Bonus dice should tend toward lower rolls."""
        normal_rolls = [roll_d100()[0] for _ in range(500)]
        bonus_rolls = [roll_d100(bonus_dice=2)[0] for _ in range(500)]

        normal_mean = sum(normal_rolls) / len(normal_rolls)
        bonus_mean = sum(bonus_rolls) / len(bonus_rolls)

        # Bonus should be lower on average
        assert bonus_mean < normal_mean, "Bonus dice should lower average"

    def test_penalty_dice_favor_higher(self):
        """Penalty dice should tend toward higher rolls."""
        normal_rolls = [roll_d100()[0] for _ in range(500)]
        penalty_rolls = [roll_d100(penalty_dice=2)[0] for _ in range(500)]

        normal_mean = sum(normal_rolls) / len(normal_rolls)
        penalty_mean = sum(penalty_rolls) / len(penalty_rolls)

        # Penalty should be higher on average
        assert penalty_mean > normal_mean, "Penalty dice should raise average"


class TestSkillCheck:
    """Tests for skill check function."""

    def test_returns_roll_result(self):
        """Should return RollResult dataclass."""
        result = skill_check("Library Use", 50)
        assert isinstance(result, RollResult)

    def test_skill_name_stored(self):
        """Skill name should be in result."""
        result = skill_check("Library Use", 50)
        assert result.skill_name == "Library Use"

    def test_target_stored(self):
        """Target value should be in result."""
        result = skill_check("Library Use", 75)
        assert result.target == 75

    def test_difficulty_regular(self):
        """Regular difficulty uses full skill."""
        result = skill_check("Test", 50, difficulty="regular")
        assert result.difficulty == "regular"
        assert result.effective_target == 50

    def test_difficulty_hard(self):
        """Hard difficulty uses half skill."""
        result = skill_check("Test", 50, difficulty="hard")
        assert result.difficulty == "hard"
        assert result.effective_target == 25

    def test_difficulty_extreme(self):
        """Extreme difficulty uses fifth of skill."""
        result = skill_check("Test", 50, difficulty="extreme")
        assert result.difficulty == "extreme"
        assert result.effective_target == 10

    def test_bonus_dice_recorded(self):
        """Bonus dice should be recorded."""
        result = skill_check("Test", 50, bonus_dice=2)
        assert result.bonus_dice == 2

    def test_penalty_dice_recorded(self):
        """Penalty dice should be recorded."""
        result = skill_check("Test", 50, penalty_dice=1)
        assert result.penalty_dice == 1

    def test_is_base_flag(self):
        """is_base flag should be passed through."""
        result = skill_check("Test", 50, is_base=True)
        assert result.is_base is True

    def test_is_custom_flag(self):
        """is_custom flag should be passed through."""
        result = skill_check("Wizardry", 30, is_custom=True)
        assert result.is_custom is True

    def test_success_level_calculated(self):
        """Success level should be determined."""
        result = skill_check("Test", 50)
        assert result.success_level in [
            SuccessLevel.CRITICAL, SuccessLevel.EXTREME,
            SuccessLevel.HARD, SuccessLevel.REGULAR,
            SuccessLevel.FAILURE, SuccessLevel.FUMBLE
        ]


class TestRollResultProperties:
    """Tests for RollResult computed properties."""

    def test_success_text(self):
        """success_text should return readable string."""
        result = RollResult(
            roll=5, target=50, success_level=SuccessLevel.EXTREME,
            difficulty="regular", bonus_dice=0, penalty_dice=0,
            tens_rolls=[0], units_roll=5, skill_name="Test",
            is_base=False, is_custom=False
        )
        assert result.success_text == "Extreme Success!"

    def test_effective_target_regular(self):
        """effective_target at regular difficulty."""
        result = RollResult(
            roll=25, target=50, success_level=SuccessLevel.REGULAR,
            difficulty="regular", bonus_dice=0, penalty_dice=0,
            tens_rolls=[2], units_roll=5, skill_name="Test",
            is_base=False, is_custom=False
        )
        assert result.effective_target == 50

    def test_effective_target_hard(self):
        """effective_target at hard difficulty."""
        result = RollResult(
            roll=25, target=50, success_level=SuccessLevel.REGULAR,
            difficulty="hard", bonus_dice=0, penalty_dice=0,
            tens_rolls=[2], units_roll=5, skill_name="Test",
            is_base=False, is_custom=False
        )
        assert result.effective_target == 25

    def test_effective_target_extreme(self):
        """effective_target at extreme difficulty."""
        result = RollResult(
            roll=10, target=50, success_level=SuccessLevel.REGULAR,
            difficulty="extreme", bonus_dice=0, penalty_dice=0,
            tens_rolls=[1], units_roll=0, skill_name="Test",
            is_base=False, is_custom=False
        )
        assert result.effective_target == 10

    def test_is_success_for_successes(self):
        """is_success True for success levels."""
        for level in [SuccessLevel.CRITICAL, SuccessLevel.EXTREME,
                      SuccessLevel.HARD, SuccessLevel.REGULAR]:
            result = RollResult(
                roll=25, target=50, success_level=level,
                difficulty="regular", bonus_dice=0, penalty_dice=0,
                tens_rolls=[2], units_roll=5, skill_name="Test",
                is_base=False, is_custom=False
            )
            assert result.is_success is True

    def test_is_success_for_failures(self):
        """is_success False for failure levels."""
        for level in [SuccessLevel.FAILURE, SuccessLevel.FUMBLE]:
            result = RollResult(
                roll=75, target=50, success_level=level,
                difficulty="regular", bonus_dice=0, penalty_dice=0,
                tens_rolls=[7], units_roll=5, skill_name="Test",
                is_base=False, is_custom=False
            )
            assert result.is_success is False


class TestCharacteristicCheck:
    """Tests for characteristic check function."""

    def test_same_mechanics_as_skill(self):
        """Characteristic check uses same mechanics as skill."""
        result = characteristic_check("STR", 60, difficulty="hard", bonus_dice=1)
        assert result.skill_name == "STR"
        assert result.target == 60
        assert result.difficulty == "hard"
        assert result.bonus_dice == 1


class TestRollDice:
    """Tests for generic dice rolling."""

    def test_simple_roll(self):
        """Should roll simple dice notation."""
        result = roll_dice("1d6")
        assert result is not None
        assert 1 <= result['natural'] <= 6

    def test_multiple_dice(self):
        """Should roll multiple dice."""
        result = roll_dice("2d6")
        assert result is not None
        assert 2 <= result['natural'] <= 12

    def test_with_modifier(self):
        """Should handle modifiers."""
        result = roll_dice("1d6+2")
        assert result is not None
        # Modified should include the +2
        assert result['modified'] >= 3

    def test_invalid_notation(self):
        """Invalid notation should return None."""
        result = roll_dice("invalid")
        assert result is None


class TestFormatRollResult:
    """Tests for roll result formatting."""

    def test_basic_format(self):
        """Should format basic roll result."""
        result = RollResult(
            roll=25, target=50, success_level=SuccessLevel.HARD,
            difficulty="regular", bonus_dice=0, penalty_dice=0,
            tens_rolls=[2], units_roll=5, skill_name="Library Use",
            is_base=False, is_custom=False
        )
        formatted = format_roll_result(result)
        assert "Library Use" in formatted
        assert "50" in formatted
        assert "25" in formatted
        assert "Hard Success" in formatted

    def test_format_with_difficulty(self):
        """Should show difficulty in format."""
        result = RollResult(
            roll=10, target=50, success_level=SuccessLevel.EXTREME,
            difficulty="hard", bonus_dice=0, penalty_dice=0,
            tens_rolls=[1], units_roll=0, skill_name="Spot Hidden",
            is_base=False, is_custom=False
        )
        formatted = format_roll_result(result)
        assert "Hard" in formatted  # difficulty indicator
        assert "25" in formatted  # effective target

    def test_format_with_bonus_dice(self):
        """Should show bonus dice info."""
        result = RollResult(
            roll=15, target=50, success_level=SuccessLevel.HARD,
            difficulty="regular", bonus_dice=2, penalty_dice=0,
            tens_rolls=[1, 4, 6], units_roll=5, skill_name="Test",
            is_base=False, is_custom=False
        )
        formatted = format_roll_result(result)
        assert "Bonus" in formatted
        assert "2" in formatted

    def test_format_with_penalty_dice(self):
        """Should show penalty dice info."""
        result = RollResult(
            roll=65, target=50, success_level=SuccessLevel.FAILURE,
            difficulty="regular", bonus_dice=0, penalty_dice=1,
            tens_rolls=[3, 6], units_roll=5, skill_name="Test",
            is_base=False, is_custom=False
        )
        formatted = format_roll_result(result)
        assert "Penalty" in formatted

    def test_format_base_skill(self):
        """Should indicate base skill."""
        result = RollResult(
            roll=30, target=25, success_level=SuccessLevel.FAILURE,
            difficulty="regular", bonus_dice=0, penalty_dice=0,
            tens_rolls=[3], units_roll=0, skill_name="Spot Hidden",
            is_base=True, is_custom=False
        )
        formatted = format_roll_result(result)
        assert "base" in formatted.lower()

    def test_format_unset_custom(self):
        """Should indicate unset custom skill."""
        result = RollResult(
            roll=50, target=0, success_level=SuccessLevel.FAILURE,
            difficulty="regular", bonus_dice=0, penalty_dice=0,
            tens_rolls=[5], units_roll=0, skill_name="Wizardry",
            is_base=False, is_custom=True
        )
        formatted = format_roll_result(result)
        assert "unset" in formatted.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
