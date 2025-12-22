"""
Test suite for AAS character importer/exporter.

Tests Dhole's House JSON parsing, field mapping, and round-trip export.
Uses actual Dhole's House v0.5.0 format as reference.
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogs.aas_importer import (
    parse_dholes_house_json,
    export_to_dholes_house,
    ImportError,
    _safe_int,
)


# Fixture: Minimal valid Dhole's House character
MINIMAL_DHOLES_JSON = json.dumps({
    "Investigator": {
        "PersonalDetails": {
            "Name": "Harvey Walters",
            "Occupation": "Professor"
        },
        "Characteristics": {
            "STR": "40",
            "CON": "50",
            "DEX": "45",
            "SIZ": "60",
            "POW": "65",
            "APP": "55",
            "INT": "80",
            "EDU": "85",
            "HitPts": "11",
            "HitPtsMax": "11",
            "MagicPts": "13",
            "MagicPtsMax": "13",
            "Luck": "65",
            "Sanity": "65",
            "SanityMax": "99"
        },
        "Skills": {
            "Skill": [
                {"name": "Library Use", "value": "75", "half": "37", "fifth": "15"},
                {"name": "History", "value": "60", "half": "30", "fifth": "12"},
                {"name": "Occult", "value": "45", "half": "22", "fifth": "9"},
                {"name": "Spot Hidden", "value": "50", "half": "25", "fifth": "10"},
                {"name": "Fighting", "subskill": "Brawl", "value": "35", "half": "17", "fifth": "7"},
                {"name": "Firearms", "subskill": "Handgun", "value": "30", "half": "15", "fifth": "6"}
            ]
        }
    }
})

# Fixture: Character with Cthulhu Mythos (affects sanity max)
MYTHOS_SCHOLAR_JSON = json.dumps({
    "Investigator": {
        "PersonalDetails": {
            "Name": "Mythos Scholar",
            "Occupation": "Antiquarian"
        },
        "Characteristics": {
            "STR": "30",
            "CON": "40",
            "DEX": "50",
            "SIZ": "50",
            "POW": "70",
            "APP": "45",
            "INT": "85",
            "EDU": "90",
            "HitPts": "9",
            "HitPtsMax": "9",
            "MagicPts": "14",
            "MagicPtsMax": "14",
            "Luck": "50",
            "Sanity": "55",
            "SanityMax": "87"
        },
        "Skills": {
            "Skill": [
                {"name": "Cthulhu Mythos", "value": "12", "half": "6", "fifth": "2"},
                {"name": "Occult", "value": "65", "half": "32", "fifth": "13"},
                {"name": "Library Use", "value": "80", "half": "40", "fifth": "16"}
            ]
        }
    }
})


class TestSafeInt:
    """Tests for _safe_int helper function."""

    def test_string_to_int(self):
        """Convert string numbers to int."""
        assert _safe_int("50") == 50
        assert _safe_int("0") == 0
        assert _safe_int("99") == 99

    def test_int_passthrough(self):
        """Int values pass through unchanged."""
        assert _safe_int(50) == 50
        assert _safe_int(0) == 0

    def test_none_returns_default(self):
        """None returns default value."""
        assert _safe_int(None) == 0
        assert _safe_int(None, 10) == 10

    def test_invalid_string_returns_default(self):
        """Invalid strings return default."""
        assert _safe_int("abc") == 0
        assert _safe_int("") == 0
        assert _safe_int("12.5") == 0  # Float string

    def test_float_truncates(self):
        """Float values truncate to int."""
        assert _safe_int(12.9) == 12
        assert _safe_int(12.1) == 12


class TestParseCharacter:
    """Tests for parse_dholes_house_json function."""

    def test_parses_name_and_occupation(self):
        """Should extract name and occupation."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        assert character["name"] == "Harvey Walters"
        assert character["occupation"] == "Professor"

    def test_parses_characteristics(self):
        """Should parse all 8 characteristics."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        chars = character["characteristics"]

        assert chars["STR"] == 40
        assert chars["CON"] == 50
        assert chars["DEX"] == 45
        assert chars["SIZ"] == 60
        assert chars["POW"] == 65
        assert chars["APP"] == 55
        assert chars["INT"] == 80
        assert chars["EDU"] == 85

    def test_parses_resources(self):
        """Should parse HP, MP, Luck, Sanity."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        res = character["resources"]

        assert res["hp"]["current"] == 11
        assert res["hp"]["max"] == 11
        assert res["mp"]["current"] == 13
        assert res["mp"]["max"] == 13
        assert res["luck"]["current"] == 65
        assert res["luck"]["starting"] == 65
        assert res["sanity"]["current"] == 65
        assert res["sanity"]["max"] == 99

    def test_parses_skills(self):
        """Should parse skills with correct values."""
        character, skill_count = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        skills = character["skills"]

        assert skill_count == 6
        assert "Library Use" in skills
        assert skills["Library Use"]["value"] == 75
        assert "History" in skills
        assert skills["History"]["value"] == 60

    def test_parses_subskills(self):
        """Should combine skill name with subskill."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        skills = character["skills"]

        assert "Fighting (Brawl)" in skills
        assert skills["Fighting (Brawl)"]["value"] == 35
        assert "Firearms (Handgun)" in skills
        assert skills["Firearms (Handgun)"]["value"] == 30

    def test_mythos_affects_sanity_max(self):
        """Cthulhu Mythos should be tracked for sanity calculation."""
        character, _ = parse_dholes_house_json(MYTHOS_SCHOLAR_JSON)

        assert character["resources"]["sanity"]["mythos"] == 12
        # Sanity max should be min of file value (87) and 99 - mythos (87)
        assert character["resources"]["sanity"]["max"] == 87

    def test_initializes_metadata(self):
        """Should initialize version, timestamps, etc."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)

        assert character["version"] == 1
        assert "created_at" in character
        assert "last_updated" in character
        assert character["pending"] == []
        assert character["changelog"] == []
        assert character["conditions"]["major_wound"] is False

    def test_skills_have_flags(self):
        """Skills should have checked, eligible, custom flags."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        skill = character["skills"]["Library Use"]

        assert skill["checked"] is False
        assert skill["eligible"] is False
        assert "custom" in skill

    def test_returns_skill_count(self):
        """Should return count of imported skills."""
        _, count = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        assert count == 6

    def test_xp_starts_at_zero(self):
        """XP should start at 0."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        assert character["resources"]["xp"] == 0


class TestParseErrors:
    """Tests for error handling in parse_dholes_house_json."""

    def test_invalid_json_raises_error(self):
        """Invalid JSON should raise ImportError."""
        with pytest.raises(ImportError) as exc:
            parse_dholes_house_json("not valid json {{{")
        assert "Could not parse JSON" in str(exc.value)

    def test_missing_investigator_raises_error(self):
        """Missing Investigator key should raise ImportError."""
        with pytest.raises(ImportError) as exc:
            parse_dholes_house_json('{"SomeOtherKey": {}}')
        assert "missing Investigator" in str(exc.value)

    def test_empty_json_raises_error(self):
        """Empty JSON object should raise ImportError."""
        with pytest.raises(ImportError) as exc:
            parse_dholes_house_json('{}')
        assert "missing Investigator" in str(exc.value)


class TestParseEdgeCases:
    """Tests for edge cases in parsing."""

    def test_missing_name_uses_default(self):
        """Missing name should use default."""
        json_data = json.dumps({
            "Investigator": {
                "PersonalDetails": {},
                "Characteristics": {},
                "Skills": {"Skill": []}
            }
        })
        character, _ = parse_dholes_house_json(json_data)
        assert character["name"] == "Unknown Investigator"

    def test_missing_occupation_empty(self):
        """Missing occupation should be empty string."""
        json_data = json.dumps({
            "Investigator": {
                "PersonalDetails": {"Name": "Test"},
                "Characteristics": {},
                "Skills": {"Skill": []}
            }
        })
        character, _ = parse_dholes_house_json(json_data)
        assert character["occupation"] == ""

    def test_zero_characteristics_allowed(self):
        """Zero characteristics should be allowed."""
        json_data = json.dumps({
            "Investigator": {
                "PersonalDetails": {"Name": "Blank"},
                "Characteristics": {
                    "STR": "0", "CON": "0", "DEX": "0", "SIZ": "0",
                    "POW": "0", "APP": "0", "INT": "0", "EDU": "0"
                },
                "Skills": {"Skill": []}
            }
        })
        character, _ = parse_dholes_house_json(json_data)
        assert all(v == 0 for v in character["characteristics"].values())

    def test_zero_value_skills_excluded(self):
        """Skills with value 0 should not be imported."""
        json_data = json.dumps({
            "Investigator": {
                "PersonalDetails": {"Name": "Test"},
                "Characteristics": {},
                "Skills": {
                    "Skill": [
                        {"name": "ZeroSkill", "value": "0"},
                        {"name": "NonZeroSkill", "value": "50"}
                    ]
                }
            }
        })
        character, count = parse_dholes_house_json(json_data)
        assert "ZeroSkill" not in character["skills"]
        assert "NonZeroSkill" in character["skills"]
        assert count == 1

    def test_null_subskill_handled(self):
        """Null subskill should be handled like None."""
        json_data = json.dumps({
            "Investigator": {
                "PersonalDetails": {"Name": "Test"},
                "Characteristics": {},
                "Skills": {
                    "Skill": [
                        {"name": "Accounting", "subskill": None, "value": "50"}
                    ]
                }
            }
        })
        character, _ = parse_dholes_house_json(json_data)
        assert "Accounting" in character["skills"]

    def test_calculates_hp_if_missing(self):
        """HP max should be calculated if not in file."""
        json_data = json.dumps({
            "Investigator": {
                "PersonalDetails": {"Name": "Test"},
                "Characteristics": {
                    "CON": "50", "SIZ": "60"
                },
                "Skills": {"Skill": []}
            }
        })
        character, _ = parse_dholes_house_json(json_data)
        # HP max = (50 + 60) // 10 = 11
        assert character["resources"]["hp"]["max"] == 11
        assert character["resources"]["hp"]["current"] == 11


class TestExport:
    """Tests for export_to_dholes_house function."""

    def test_exports_valid_json(self):
        """Export should produce valid JSON."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        exported = export_to_dholes_house(character)

        # Should be valid JSON
        data = json.loads(exported)
        assert "Investigator" in data

    def test_exports_name_and_occupation(self):
        """Export should include name and occupation."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        exported = export_to_dholes_house(character)
        data = json.loads(exported)

        personal = data["Investigator"]["PersonalDetails"]
        assert personal["Name"] == "Harvey Walters"
        assert personal["Occupation"] == "Professor"

    def test_exports_characteristics_as_strings(self):
        """Characteristics should be exported as strings."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        exported = export_to_dholes_house(character)
        data = json.loads(exported)

        chars = data["Investigator"]["Characteristics"]
        assert chars["STR"] == "40"
        assert chars["CON"] == "50"
        assert isinstance(chars["STR"], str)

    def test_exports_resources(self):
        """Resources should be exported."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        exported = export_to_dholes_house(character)
        data = json.loads(exported)

        chars = data["Investigator"]["Characteristics"]
        assert chars["HitPts"] == "11"
        assert chars["HitPtsMax"] == "11"
        assert chars["Luck"] == "65"

    def test_exports_skills_in_skill_array(self):
        """Skills should be in Skills.Skill array."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        exported = export_to_dholes_house(character)
        data = json.loads(exported)

        skills = data["Investigator"]["Skills"]["Skill"]
        assert isinstance(skills, list)
        assert len(skills) > 0

    def test_exports_skill_half_and_fifth(self):
        """Skills should include half and fifth values."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        exported = export_to_dholes_house(character)
        data = json.loads(exported)

        skills = data["Investigator"]["Skills"]["Skill"]
        lib_use = next(s for s in skills if s["name"] == "Library Use")
        assert lib_use["value"] == "75"
        assert lib_use["half"] == "37"
        assert lib_use["fifth"] == "15"

    def test_exports_subskills(self):
        """Subskills should be split back out."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        exported = export_to_dholes_house(character)
        data = json.loads(exported)

        skills = data["Investigator"]["Skills"]["Skill"]
        fighting = next((s for s in skills if s["name"] == "Fighting"), None)
        assert fighting is not None
        assert fighting["subskill"] == "Brawl"

    def test_includes_header(self):
        """Export should include header metadata."""
        character, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        exported = export_to_dholes_house(character)
        data = json.loads(exported)

        header = data["Investigator"]["Header"]
        assert header["GameVersion"] == "7th Edition"
        assert header["Version"] == "0.5.0"


class TestRoundTrip:
    """Tests for import -> export -> import round-trip."""

    def test_roundtrip_preserves_name(self):
        """Name should survive round-trip."""
        char1, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        exported = export_to_dholes_house(char1)
        char2, _ = parse_dholes_house_json(exported)

        assert char2["name"] == char1["name"]

    def test_roundtrip_preserves_characteristics(self):
        """Characteristics should survive round-trip."""
        char1, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        exported = export_to_dholes_house(char1)
        char2, _ = parse_dholes_house_json(exported)

        for stat in ["STR", "CON", "DEX", "SIZ", "POW", "APP", "INT", "EDU"]:
            assert char2["characteristics"][stat] == char1["characteristics"][stat]

    def test_roundtrip_preserves_skill_values(self):
        """Skill values should survive round-trip."""
        char1, _ = parse_dholes_house_json(MINIMAL_DHOLES_JSON)
        exported = export_to_dholes_house(char1)
        char2, _ = parse_dholes_house_json(exported)

        for skill_name, skill_data in char1["skills"].items():
            assert skill_name in char2["skills"]
            assert char2["skills"][skill_name]["value"] == skill_data["value"]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
