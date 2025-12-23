"""
Test suite for AAS Discord cog.

Tests command functionality with mocked Discord context.
Uses temporary directories for character data isolation.
"""
import pytest
import asyncio
import json
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockUser:
    """Mock Discord user/member."""

    def __init__(self, user_id: int = 123456789, name: str = "TestUser"):
        self.id = user_id
        self.name = name
        self.display_name = name
        self.display_avatar = MagicMock()
        self.display_avatar.url = "https://example.com/avatar.png"


class MockChannel:
    """Mock Discord channel."""

    def __init__(self):
        self.send = AsyncMock()
        self.last_message = None


class MockMessage:
    """Mock Discord message."""

    def __init__(self, author: MockUser, channel: MockChannel):
        self.author = author
        self.channel = channel
        self.attachments = []


class MockContext:
    """Mock Discord command context."""

    def __init__(self, user_id: int = 123456789, user_name: str = "TestUser"):
        self.author = MockUser(user_id, user_name)
        self.channel = MockChannel()
        self.message = MockMessage(self.author, self.channel)
        self.send = AsyncMock()


class MockBot:
    """Mock Discord bot."""

    def __init__(self):
        self.user = MockUser(0, "Bot")


@pytest.fixture
def temp_char_dir():
    """Create temporary directory for character data."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def aas_cog(temp_char_dir):
    """Create AAS cog instance with temporary data directory."""
    import cogs.aas.cog as aas_module

    # Patch the CHARACTER_DIR directly on the module
    original_dir = aas_module.CHARACTER_DIR
    aas_module.CHARACTER_DIR = temp_char_dir

    bot = MockBot()
    cog = aas_module.AAS(bot)

    yield cog

    # Restore original
    aas_module.CHARACTER_DIR = original_dir


@pytest.fixture
def ctx():
    """Create mock context."""
    return MockContext()


@pytest.fixture
def ctx2():
    """Create second mock context for different user."""
    return MockContext(user_id=987654321, user_name="OtherUser")


# Helper to call cog subcommand callbacks
async def call_cmd(cog, method_name, ctx, *args, **kwargs):
    """Call a cog command's callback directly."""
    method = getattr(cog, method_name)
    return await method.callback(cog, ctx, *args, **kwargs)


class TestCharacterCreate:
    """Tests for character creation."""

    @pytest.mark.asyncio
    async def test_create_character_success(self, aas_cog, ctx):
        """Should create a new character."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Harvey Walters", "Professor")

        ctx.send.assert_called_once()
        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "Harvey Walters" in content
        assert "Professor" in content

    @pytest.mark.asyncio
    async def test_create_without_occupation(self, aas_cog, ctx):
        """Should create character without occupation."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Solo Investigator", "")

        ctx.send.assert_called_once()
        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "Solo Investigator" in content

    @pytest.mark.asyncio
    async def test_create_duplicate_rejected(self, aas_cog, ctx):
        """Should reject duplicate character creation."""
        await call_cmd(aas_cog, 'aas_create', ctx, "First Character", "")
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_create', ctx, "Second Character", "")

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "already have a character" in content.lower()


class TestCharacterStats:
    """Tests for setting characteristics."""

    @pytest.mark.asyncio
    async def test_set_all_stats(self, aas_cog, ctx):
        """Should set all 8 characteristics."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test Character", "")
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_stats', ctx, 40, 50, 45, 60, 65, 55, 80, 85)

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "40" in content  # STR
        assert "50" in content  # CON
        assert "Derived:" in content

    @pytest.mark.asyncio
    async def test_stats_without_character(self, aas_cog, ctx):
        """Should reject stats without character."""
        await call_cmd(aas_cog, 'aas_stats', ctx, 40, 50, 45, 60, 65, 55, 80, 85)

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "don't have a character" in content.lower()

    @pytest.mark.asyncio
    async def test_stats_calculates_derived(self, aas_cog, ctx, temp_char_dir):
        """Should calculate HP/MP from stats."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test Character", "")
        await call_cmd(aas_cog, 'aas_stats', ctx, 40, 50, 45, 60, 65, 55, 80, 85)

        # Load character and check derived values
        char_path = temp_char_dir / f"{ctx.author.id}.json"
        with open(char_path) as f:
            char = json.load(f)

        # HP = (CON + SIZ) // 10 = (50 + 60) // 10 = 11
        assert char["resources"]["hp"]["max"] == 11
        # MP = POW // 5 = 65 // 5 = 13
        assert char["resources"]["mp"]["max"] == 13


class TestCharacterSet:
    """Tests for !aas set command."""

    @pytest.mark.asyncio
    async def test_set_characteristic(self, aas_cog, ctx, temp_char_dir):
        """Should set individual characteristic."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        await call_cmd(aas_cog, 'aas_stats', ctx, 40, 50, 45, 60, 65, 55, 80, 85)
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_set', ctx, "STR", "55")

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "55" in content

        # Verify in file
        char_path = temp_char_dir / f"{ctx.author.id}.json"
        with open(char_path) as f:
            char = json.load(f)
        assert char["characteristics"]["STR"] == 55

    @pytest.mark.asyncio
    async def test_set_with_delta(self, aas_cog, ctx, temp_char_dir):
        """Should handle delta values."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        await call_cmd(aas_cog, 'aas_stats', ctx, 40, 50, 45, 60, 65, 55, 80, 85)
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_set', ctx, "hp", "-3")

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "8/11" in content  # 11 - 3 = 8

    @pytest.mark.asyncio
    async def test_set_hp_major_wound(self, aas_cog, ctx, temp_char_dir):
        """Should detect major wound when HP drops below threshold."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        # Use stats where HP max (11) > threshold (CON/2 = 10)
        # CON=20, SIZ=90 -> HP max = 11, threshold = 10
        await call_cmd(aas_cog, 'aas_stats', ctx, 40, 20, 45, 90, 65, 55, 80, 85)
        ctx.send.reset_mock()

        # HP starts at 11, threshold is 10
        # Drop HP from 11 to 5 (crossing threshold of 10)
        await call_cmd(aas_cog, 'aas_set', ctx, "hp", "-6")  # 11 - 6 = 5

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "Major Wound" in content

    @pytest.mark.asyncio
    async def test_set_xp(self, aas_cog, ctx, temp_char_dir):
        """Should set XP pool."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_set', ctx, "xp", "5")

        char_path = temp_char_dir / f"{ctx.author.id}.json"
        with open(char_path) as f:
            char = json.load(f)
        assert char["resources"]["xp"] == 5


class TestSkillCommands:
    """Tests for skill-related commands."""

    @pytest.mark.asyncio
    async def test_set_skill(self, aas_cog, ctx, temp_char_dir):
        """Should set skill value."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_skill', ctx, "Library Use", 75)

        char_path = temp_char_dir / f"{ctx.author.id}.json"
        with open(char_path) as f:
            char = json.load(f)
        assert char["skills"]["Library Use"]["value"] == 75

    @pytest.mark.asyncio
    async def test_set_custom_skill(self, aas_cog, ctx, temp_char_dir):
        """Should create custom skill with marker."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_skill', ctx, "Wizardry", 35)

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "*" in content  # Custom skill marker

        char_path = temp_char_dir / f"{ctx.author.id}.json"
        with open(char_path) as f:
            char = json.load(f)
        assert char["skills"]["Wizardry"]["custom"] is True

    @pytest.mark.asyncio
    async def test_skill_check_command(self, aas_cog, ctx, temp_char_dir):
        """Should roll skill check with embed."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        await call_cmd(aas_cog, 'aas_skill', ctx, "Library Use", 75)
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'cmd_skill', ctx, "Library Use", "regular", None)

        # Check embed was sent
        embed = ctx.send.call_args.kwargs.get("embed")
        assert embed is not None
        assert "Library Use" in embed.title

    @pytest.mark.asyncio
    async def test_skill_check_with_difficulty(self, aas_cog, ctx):
        """Should handle difficulty modifier with embed."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        await call_cmd(aas_cog, 'aas_skill', ctx, "Library Use", 80)
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'cmd_skill', ctx, "Library Use", "hard", None)

        # Check embed was sent with difficulty info
        embed = ctx.send.call_args.kwargs.get("embed")
        assert embed is not None
        # Check fields contain difficulty and target
        field_values = [f.value for f in embed.fields]
        assert any("Hard" in str(v) for v in field_values)


class TestResourceCommands:
    """Tests for HP/MP/San/Luck commands."""

    @pytest.mark.asyncio
    async def test_hp_view(self, aas_cog, ctx):
        """Should display HP."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        await call_cmd(aas_cog, 'aas_stats', ctx, 40, 50, 45, 60, 65, 55, 80, 85)
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'cmd_hp', ctx, None)

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "11/11" in content

    @pytest.mark.asyncio
    async def test_hp_damage(self, aas_cog, ctx):
        """Should apply damage to HP."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        await call_cmd(aas_cog, 'aas_stats', ctx, 40, 50, 45, 60, 65, 55, 80, 85)
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'cmd_hp', ctx, "-3")

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "8/11" in content
        assert "-3" in content

    @pytest.mark.asyncio
    async def test_san_with_dice(self, aas_cog, ctx):
        """Should roll dice for sanity loss."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        await call_cmd(aas_cog, 'aas_stats', ctx, 40, 50, 45, 60, 65, 55, 80, 85)
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'cmd_san', ctx, "-1d6")

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "Sanity" in content
        assert "rolled" in content.lower()


class TestAdvancement:
    """Tests for skill advancement system."""

    @pytest.mark.asyncio
    async def test_check_skill(self, aas_cog, ctx, temp_char_dir):
        """Should mark skill for advancement."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        await call_cmd(aas_cog, 'aas_skill', ctx, "Library Use", 75)
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_check', ctx, "Library Use")

        char_path = temp_char_dir / f"{ctx.author.id}.json"
        with open(char_path) as f:
            char = json.load(f)
        assert char["skills"]["Library Use"]["checked"] is True

    @pytest.mark.asyncio
    async def test_advance_rolls_for_checked(self, aas_cog, ctx, temp_char_dir):
        """Should roll advancement for checked skills."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        await call_cmd(aas_cog, 'aas_skill', ctx, "Library Use", 75)
        await call_cmd(aas_cog, 'aas_check', ctx, "Library Use")
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_advance', ctx)

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "Library Use" in content
        assert "rolled" in content.lower()

    @pytest.mark.asyncio
    async def test_spend_xp(self, aas_cog, ctx, temp_char_dir):
        """Should spend XP on eligible skill."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        await call_cmd(aas_cog, 'aas_skill', ctx, "TestSkill", 50)
        await call_cmd(aas_cog, 'aas_set', ctx, "xp", "5")

        # Manually set skill as eligible
        char_path = temp_char_dir / f"{ctx.author.id}.json"
        with open(char_path) as f:
            char = json.load(f)
        char["skills"]["TestSkill"]["eligible"] = True
        with open(char_path, 'w') as f:
            json.dump(char, f)

        ctx.send.reset_mock()
        await call_cmd(aas_cog, 'aas_spend', ctx, "TestSkill", 2)

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "52" in content  # 50 + 2


class TestSessionManagement:
    """Tests for session save and history."""

    @pytest.mark.asyncio
    async def test_save_session(self, aas_cog, ctx, temp_char_dir):
        """Should save pending changes to changelog."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        await call_cmd(aas_cog, 'aas_stats', ctx, 40, 50, 45, 60, 65, 55, 80, 85)
        await call_cmd(aas_cog, 'aas_set', ctx, "hp", "-3")
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_save', ctx, note="Session 1 - The Beginning")

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "saved" in content.lower()

        # Check changelog
        char_path = temp_char_dir / f"{ctx.author.id}.json"
        with open(char_path) as f:
            char = json.load(f)
        assert len(char["changelog"]) > 0
        assert char["changelog"][0]["note"] == "Session 1 - The Beginning"

    @pytest.mark.asyncio
    async def test_history(self, aas_cog, ctx, temp_char_dir):
        """Should display session history."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        await call_cmd(aas_cog, 'aas_set', ctx, "xp", "1")
        await call_cmd(aas_cog, 'aas_save', ctx, note="First Session")
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_history', ctx, 5)

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "First Session" in content


class TestConditions:
    """Tests for condition tracking."""

    @pytest.mark.asyncio
    async def test_wound_toggle(self, aas_cog, ctx, temp_char_dir):
        """Should toggle major wound status."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_wound', ctx, "on")

        char_path = temp_char_dir / f"{ctx.author.id}.json"
        with open(char_path) as f:
            char = json.load(f)
        assert char["conditions"]["major_wound"] is True

        await call_cmd(aas_cog, 'aas_wound', ctx, "off")

        with open(char_path) as f:
            char = json.load(f)
        assert char["conditions"]["major_wound"] is False


class TestCharacterDelete:
    """Tests for character deletion."""

    @pytest.mark.asyncio
    async def test_delete_requires_confirmation(self, aas_cog, ctx):
        """Should require confirmation to delete."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")
        ctx.send.reset_mock()

        await call_cmd(aas_cog, 'aas_delete', ctx, None)

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "confirm" in content.lower()

    @pytest.mark.asyncio
    async def test_delete_with_confirmation(self, aas_cog, ctx, temp_char_dir):
        """Should delete character when confirmed."""
        await call_cmd(aas_cog, 'aas_create', ctx, "Test", "")

        # First call to initiate delete
        await call_cmd(aas_cog, 'aas_delete', ctx, None)
        ctx.send.reset_mock()

        # Second call to confirm
        await call_cmd(aas_cog, 'aas_delete', ctx, "confirm")

        content = ctx.send.call_args.kwargs.get("content") or ctx.send.call_args.args[0]
        assert "deleted" in content.lower()

        # Verify file removed
        char_path = temp_char_dir / f"{ctx.author.id}.json"
        assert not char_path.exists()


class TestMultipleUsers:
    """Tests for multi-user isolation."""

    @pytest.mark.asyncio
    async def test_separate_characters(self, aas_cog, ctx, ctx2, temp_char_dir):
        """Different users should have separate characters."""
        await call_cmd(aas_cog, 'aas_create', ctx, "User1 Character", "")
        await call_cmd(aas_cog, 'aas_create', ctx2, "User2 Character", "")

        # Check both files exist
        char1_path = temp_char_dir / f"{ctx.author.id}.json"
        char2_path = temp_char_dir / f"{ctx2.author.id}.json"

        assert char1_path.exists()
        assert char2_path.exists()

        with open(char1_path) as f:
            char1 = json.load(f)
        with open(char2_path) as f:
            char2 = json.load(f)

        assert char1["name"] == "User1 Character"
        assert char2["name"] == "User2 Character"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
