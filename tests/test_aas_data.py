"""
Test suite for AAS data constants and utility functions.

Tests skill defaults, success level calculation, derived value formulas,
and skill normalization functions.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogs.aas.data import (
    CHARACTERISTICS,
    RESOURCES,
    STANDARD_SKILLS,
    SKILL_ALIASES,
    get_skill_base,
    is_standard_skill,
    normalize_skill_name,
    calc_hp_max,
    calc_mp_max,
    calc_sanity_max,
    calc_major_wound_threshold,
    get_success_level,
    SuccessLevel,
    SUCCESS_DISPLAY,
)


class TestCharacteristics:
    """Tests for characteristic constants."""

    def test_all_eight_characteristics(self):
        """Verify all 8 CoC characteristics are defined."""
        expected = {"STR", "CON", "DEX", "SIZ", "POW", "APP", "INT", "EDU"}
        assert CHARACTERISTICS == expected

    def test_characteristics_is_set(self):
        """Characteristics should be a set for O(1) lookup."""
        assert isinstance(CHARACTERISTICS, set)


class TestResources:
    """Tests for resource pool constants."""

    def test_all_resources_defined(self):
        """Verify all resource types are defined."""
        expected = {"hp", "mp", "san", "luck", "xp"}
        assert RESOURCES == expected


class TestStandardSkills:
    """Tests for standard skill list."""

    def test_has_combat_skills(self):
        """Combat skills should be present."""
        assert "Dodge" in STANDARD_SKILLS
        assert "Fighting (Brawl)" in STANDARD_SKILLS
        assert "Firearms (Handgun)" in STANDARD_SKILLS

    def test_has_investigation_skills(self):
        """Investigation skills should be present."""
        assert "Library Use" in STANDARD_SKILLS
        assert "Spot Hidden" in STANDARD_SKILLS
        assert "Listen" in STANDARD_SKILLS

    def test_has_social_skills(self):
        """Social skills should be present."""
        assert "Charm" in STANDARD_SKILLS
        assert "Persuade" in STANDARD_SKILLS
        assert "Intimidate" in STANDARD_SKILLS

    def test_cthulhu_mythos_base_zero(self):
        """Cthulhu Mythos must have base 0."""
        assert STANDARD_SKILLS["Cthulhu Mythos"] == 0

    def test_dodge_base_zero_for_derived(self):
        """Dodge has 0 base because it's derived from DEX."""
        assert STANDARD_SKILLS["Dodge"] == 0

    def test_language_own_base_zero_for_derived(self):
        """Language (Own) has 0 base because it's derived from EDU."""
        assert STANDARD_SKILLS["Language (Own)"] == 0

    def test_library_use_base_20(self):
        """Library Use should have base 20."""
        assert STANDARD_SKILLS["Library Use"] == 20

    def test_first_aid_base_30(self):
        """First Aid should have base 30."""
        assert STANDARD_SKILLS["First Aid"] == 30


class TestSkillAliases:
    """Tests for skill name aliases."""

    def test_common_aliases(self):
        """Common abbreviations should map correctly."""
        assert SKILL_ALIASES["spot"] == "Spot Hidden"
        assert SKILL_ALIASES["library"] == "Library Use"
        assert SKILL_ALIASES["brawl"] == "Fighting (Brawl)"

    def test_firearm_aliases(self):
        """Firearm aliases should work."""
        assert SKILL_ALIASES["handgun"] == "Firearms (Handgun)"
        assert SKILL_ALIASES["pistol"] == "Firearms (Handgun)"
        assert SKILL_ALIASES["rifle"] == "Firearms (Rifle/Shotgun)"


class TestGetSkillBase:
    """Tests for get_skill_base function."""

    def test_standard_skill_returns_base(self):
        """Standard skills return their base value."""
        assert get_skill_base("Library Use") == 20
        assert get_skill_base("First Aid") == 30
        assert get_skill_base("Spot Hidden") == 25

    def test_unknown_skill_returns_zero(self):
        """Unknown/custom skills return 0."""
        assert get_skill_base("Wizardry") == 0
        assert get_skill_base("Made Up Skill") == 0

    def test_dodge_with_characteristics(self):
        """Dodge should be DEX/2 when characteristics provided."""
        chars = {"DEX": 60, "EDU": 80}
        assert get_skill_base("Dodge", chars) == 30

    def test_dodge_without_characteristics(self):
        """Dodge returns 0 when no characteristics provided."""
        assert get_skill_base("Dodge") == 0

    def test_language_own_with_characteristics(self):
        """Language (Own) should be EDU when characteristics provided."""
        chars = {"DEX": 60, "EDU": 80}
        assert get_skill_base("Language (Own)", chars) == 80

    def test_alias_resolution(self):
        """Aliases should resolve to correct skill."""
        assert get_skill_base("spot") == 25  # Spot Hidden
        assert get_skill_base("library") == 20  # Library Use


class TestIsStandardSkill:
    """Tests for is_standard_skill function."""

    def test_standard_skills_return_true(self):
        """Known skills return True."""
        assert is_standard_skill("Library Use") is True
        assert is_standard_skill("Spot Hidden") is True
        assert is_standard_skill("Cthulhu Mythos") is True

    def test_custom_skills_return_false(self):
        """Unknown skills return False."""
        assert is_standard_skill("Wizardry") is False
        assert is_standard_skill("Dreaming") is False

    def test_aliases_return_true(self):
        """Aliased names should return True."""
        assert is_standard_skill("spot") is True
        assert is_standard_skill("brawl") is True

    def test_partial_match_parameterized(self):
        """Parameterized skills should partial match."""
        assert is_standard_skill("Art/Craft") is True
        assert is_standard_skill("Science") is True


class TestNormalizeSkillName:
    """Tests for normalize_skill_name function."""

    def test_alias_normalized(self):
        """Aliases should normalize to full name."""
        assert normalize_skill_name("spot") == "Spot Hidden"
        assert normalize_skill_name("library") == "Library Use"

    def test_non_alias_unchanged(self):
        """Non-aliased names pass through."""
        assert normalize_skill_name("Library Use") == "Library Use"
        assert normalize_skill_name("Wizardry") == "Wizardry"


class TestDerivedValueFormulas:
    """Tests for HP, MP, Sanity max calculations."""

    def test_hp_max_calculation(self):
        """HP max = (CON + SIZ) // 10"""
        assert calc_hp_max(50, 60) == 11
        assert calc_hp_max(40, 40) == 8
        assert calc_hp_max(99, 99) == 19
        assert calc_hp_max(10, 10) == 2

    def test_mp_max_calculation(self):
        """MP max = POW // 5"""
        assert calc_mp_max(65) == 13
        assert calc_mp_max(50) == 10
        assert calc_mp_max(99) == 19
        assert calc_mp_max(10) == 2

    def test_sanity_max_calculation(self):
        """Sanity max = 99 - Cthulhu Mythos"""
        assert calc_sanity_max(0) == 99
        assert calc_sanity_max(10) == 89
        assert calc_sanity_max(50) == 49
        assert calc_sanity_max(99) == 0

    def test_major_wound_threshold(self):
        """Major wound threshold = CON // 2"""
        assert calc_major_wound_threshold(50) == 25
        assert calc_major_wound_threshold(60) == 30
        assert calc_major_wound_threshold(99) == 49
        assert calc_major_wound_threshold(10) == 5


class TestSuccessLevelCalculation:
    """Tests for get_success_level function."""

    def test_critical_success(self):
        """Roll of 01 is always critical."""
        assert get_success_level(1, 50) == SuccessLevel.CRITICAL
        assert get_success_level(1, 10) == SuccessLevel.CRITICAL
        assert get_success_level(1, 99) == SuccessLevel.CRITICAL

    def test_fumble_on_100(self):
        """Roll of 100 is always fumble."""
        assert get_success_level(100, 50) == SuccessLevel.FUMBLE
        assert get_success_level(100, 99) == SuccessLevel.FUMBLE

    def test_fumble_96_99_low_skill(self):
        """Rolls 96-99 fumble when skill < 50."""
        assert get_success_level(96, 49) == SuccessLevel.FUMBLE
        assert get_success_level(97, 30) == SuccessLevel.FUMBLE
        assert get_success_level(98, 10) == SuccessLevel.FUMBLE
        assert get_success_level(99, 45) == SuccessLevel.FUMBLE

    def test_no_fumble_96_99_high_skill(self):
        """Rolls 96-99 don't fumble when skill >= 50."""
        assert get_success_level(96, 50) == SuccessLevel.FAILURE
        assert get_success_level(97, 60) == SuccessLevel.FAILURE
        assert get_success_level(99, 99) == SuccessLevel.REGULAR  # 99 <= 99

    def test_extreme_success(self):
        """Roll <= skill/5 is extreme success."""
        # skill 50: extreme threshold is 10
        assert get_success_level(5, 50) == SuccessLevel.EXTREME
        assert get_success_level(10, 50) == SuccessLevel.EXTREME
        # skill 80: extreme threshold is 16
        assert get_success_level(16, 80) == SuccessLevel.EXTREME

    def test_hard_success(self):
        """Roll <= skill/2 (but > skill/5) is hard success."""
        # skill 50: hard threshold 25, extreme threshold 10
        assert get_success_level(15, 50) == SuccessLevel.HARD
        assert get_success_level(25, 50) == SuccessLevel.HARD

    def test_regular_success(self):
        """Roll <= skill (but > skill/2) is regular success."""
        # skill 50: regular <= 50, hard <= 25
        assert get_success_level(30, 50) == SuccessLevel.REGULAR
        assert get_success_level(50, 50) == SuccessLevel.REGULAR

    def test_failure(self):
        """Roll > skill is failure."""
        assert get_success_level(51, 50) == SuccessLevel.FAILURE
        assert get_success_level(75, 50) == SuccessLevel.FAILURE
        assert get_success_level(95, 50) == SuccessLevel.FAILURE

    def test_minimum_thresholds(self):
        """Thresholds should be at least 1."""
        # skill 3: extreme would be 0, but minimum is 1
        assert get_success_level(1, 3) == SuccessLevel.CRITICAL  # 01 always critical
        # skill 5: extreme = 1, hard = 2
        assert get_success_level(2, 5) == SuccessLevel.HARD


class TestSuccessDisplay:
    """Tests for success level display strings."""

    def test_all_levels_have_display(self):
        """All success levels should have display text."""
        for level in [SuccessLevel.CRITICAL, SuccessLevel.EXTREME,
                      SuccessLevel.HARD, SuccessLevel.REGULAR,
                      SuccessLevel.FAILURE, SuccessLevel.FUMBLE]:
            assert level in SUCCESS_DISPLAY
            assert len(SUCCESS_DISPLAY[level]) > 0

    def test_display_text_format(self):
        """Display text should be human-readable."""
        assert SUCCESS_DISPLAY[SuccessLevel.CRITICAL] == "Critical Success!"
        assert SUCCESS_DISPLAY[SuccessLevel.FUMBLE] == "Fumble!"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
