"""
AAS Character Management Cog

BURGE (Call of Cthulhu 7e variant) character management for the Academy of
Anomalous Studies campaign. One character per Discord user, persisted as JSON.

Commands:
    !aas create/sheet/stats/set/skill/skills/import/export/delete/help
    !aas check/advance/spend (skill advancement)
    !aas save/history (session management)
    !aas wound (conditions)
    !skill, !char, !hp, !mp, !san, !luck (quick access)
"""

import os
import json
import re
import logging
import discord
from discord.ext import commands
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from .Utils import make_embed
from .aas_data import (
    CHARACTERISTICS,
    RESOURCES,
    STANDARD_SKILLS,
    get_skill_base,
    is_standard_skill,
    normalize_skill_name,
    calc_hp_max,
    calc_mp_max,
    calc_sanity_max,
    calc_major_wound_threshold,
    SuccessLevel,
)
from .aas_roller import (
    skill_check,
    characteristic_check,
    roll_dice,
    parse_modifier,
    format_roll_result,
)
from .aas_importer import (
    parse_dholes_house_json,
    export_to_dholes_house,
    ImportError,
)

logger = logging.getLogger('aas')

# Default character directory
DEFAULT_DIR = Path("data/characters")
CHARACTER_DIR = Path(os.getenv("AAS_CHARACTER_DIR", DEFAULT_DIR))


class AAS(commands.Cog):
    """Academy of Anomalous Studies character management."""

    def __init__(self, bot):
        self.bot = bot
        self._ensure_data_dir()
        self._pending_deletes: Dict[int, datetime] = {}

    def _ensure_data_dir(self):
        """Create character data directory if it doesn't exist."""
        CHARACTER_DIR.mkdir(parents=True, exist_ok=True)

    def _get_character_path(self, user_id: int) -> Path:
        """Get path to a user's character file."""
        return CHARACTER_DIR / f"{user_id}.json"

    def _load_character(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Load a character from disk."""
        path = self._get_character_path(user_id)
        if not path.exists():
            return None
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load character {user_id}: {e}")
            return None

    def _save_character(self, user_id: int, character: Dict[str, Any]):
        """Save a character to disk."""
        path = self._get_character_path(user_id)
        character["last_updated"] = datetime.now(timezone.utc).isoformat()
        try:
            with open(path, 'w') as f:
                json.dump(character, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save character {user_id}: {e}")
            raise

    def _add_pending_change(self, character: Dict[str, Any], change: str):
        """Add a change to pending list for session changelog."""
        if "pending" not in character:
            character["pending"] = []
        character["pending"].append(change)

    def _recalc_derived(self, character: Dict[str, Any]):
        """Recalculate derived values from characteristics."""
        chars = character.get("characteristics", {})
        resources = character.get("resources", {})
        skills = character.get("skills", {})

        con = chars.get("CON", 0)
        siz = chars.get("SIZ", 0)
        pow_stat = chars.get("POW", 0)

        # HP max
        new_hp_max = calc_hp_max(con, siz)
        if "hp" not in resources:
            resources["hp"] = {"current": new_hp_max, "max": new_hp_max}
        else:
            resources["hp"]["max"] = new_hp_max

        # MP max
        new_mp_max = calc_mp_max(pow_stat)
        if "mp" not in resources:
            resources["mp"] = {"current": new_mp_max, "max": new_mp_max}
        else:
            resources["mp"]["max"] = new_mp_max

        # Sanity max (99 - Cthulhu Mythos)
        mythos = skills.get("Cthulhu Mythos", {}).get("value", 0)
        new_san_max = calc_sanity_max(mythos)
        if "sanity" not in resources:
            resources["sanity"] = {"current": pow_stat, "max": new_san_max, "mythos": mythos}
        else:
            resources["sanity"]["max"] = new_san_max
            resources["sanity"]["mythos"] = mythos

        character["resources"] = resources

    # ========== Group 1: Character Management ==========

    @commands.group(invoke_without_command=True)
    async def aas(self, ctx):
        """AAS character management. Use !aas help for commands."""
        await ctx.send("Use `!aas help` for available commands.")

    @aas.command(name="create")
    async def aas_create(self, ctx, name: str, occupation: str = ""):
        """
        Create a new character.

        Usage: !aas create <name> [occupation]
        Examples:
            !aas create "Harvey Walters"
            !aas create "Harvey Walters" "Professor"
        """
        user_id = ctx.author.id

        if self._load_character(user_id):
            await ctx.send("You already have a character. Use `!aas delete` first.")
            return

        now = datetime.now(timezone.utc).isoformat()
        character = {
            "name": name,
            "occupation": occupation,
            "created_at": now,
            "last_updated": now,
            "version": 1,
            "characteristics": {c: 0 for c in CHARACTERISTICS},
            "resources": {
                "hp": {"current": 0, "max": 0},
                "mp": {"current": 0, "max": 0},
                "luck": {"current": 0, "starting": 0},
                "sanity": {"current": 0, "max": 99, "mythos": 0},
                "xp": 0,
            },
            "skills": {},
            "conditions": {"major_wound": False},
            "pending": [],
            "changelog": [],
        }

        self._save_character(user_id, character)

        msg = f"**Character Created:** {name}\n"
        if occupation:
            msg += f"**Occupation:** {occupation}\n"
        msg += "Use `!aas stats` to set characteristics."
        await ctx.send(msg)

    @aas.command(name="sheet")
    async def aas_sheet(self, ctx, user: discord.Member = None):
        """
        Display character sheet.

        Usage: !aas sheet [@user]
        """
        target = user or ctx.author
        character = self._load_character(target.id)

        if not character:
            if target == ctx.author:
                await ctx.send("You don't have a character. Use `!aas create` first.")
            else:
                await ctx.send(f"{target.display_name} doesn't have a character.")
            return

        embed = self._build_sheet_embed(character, target)
        await ctx.send(embed=embed)

    def _build_sheet_embed(self, character: Dict[str, Any], user: discord.Member) -> discord.Embed:
        """Build an embed for character sheet display."""
        name = character.get("name", "Unknown")
        occupation = character.get("occupation", "")
        chars = character.get("characteristics", {})
        resources = character.get("resources", {})
        skills = character.get("skills", {})
        conditions = character.get("conditions", {})

        title = name
        if occupation:
            title += f" - {occupation}"

        embed = discord.Embed(title=title, color=discord.Color.dark_purple())
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

        # Characteristics
        char_lines = []
        char_lines.append(f"STR {chars.get('STR', 0):2} | CON {chars.get('CON', 0):2} | DEX {chars.get('DEX', 0):2} | SIZ {chars.get('SIZ', 0):2}")
        char_lines.append(f"POW {chars.get('POW', 0):2} | APP {chars.get('APP', 0):2} | INT {chars.get('INT', 0):2} | EDU {chars.get('EDU', 0):2}")
        embed.add_field(name="Characteristics", value="```" + "\n".join(char_lines) + "```", inline=False)

        # Resources
        hp = resources.get("hp", {})
        mp = resources.get("mp", {})
        san = resources.get("sanity", {})
        luck = resources.get("luck", {})
        xp = resources.get("xp", 0)

        res_line = f"HP {hp.get('current', 0)}/{hp.get('max', 0)} | MP {mp.get('current', 0)}/{mp.get('max', 0)} | SAN {san.get('current', 0)}/{san.get('max', 99)} | Luck {luck.get('current', 0)}"
        if xp > 0:
            res_line += f" | XP {xp}"
        embed.add_field(name="Resources", value=f"`{res_line}`", inline=False)

        # Conditions
        cond_parts = []
        if conditions.get("major_wound"):
            cond_parts.append("Major Wound")
        if cond_parts:
            embed.add_field(name="Conditions", value=", ".join(cond_parts), inline=False)

        # Top skills
        sorted_skills = sorted(skills.items(), key=lambda x: x[1].get("value", 0), reverse=True)[:10]
        if sorted_skills:
            skill_lines = []
            for skill_name, skill_data in sorted_skills:
                value = skill_data.get("value", 0)
                markers = ""
                if skill_data.get("custom"):
                    markers += "*"
                if skill_data.get("checked"):
                    markers += "✓"
                if skill_data.get("eligible"):
                    markers += "↑"
                skill_lines.append(f"{skill_name}{markers}: {value}")
            embed.add_field(name="Skills", value="\n".join(skill_lines), inline=False)

        return embed

    @aas.command(name="stats")
    async def aas_stats(self, ctx, str_val: int, con_val: int, dex_val: int,
                        siz_val: int, pow_val: int, app_val: int, int_val: int, edu_val: int):
        """
        Set all 8 characteristics at once.

        Usage: !aas stats <STR> <CON> <DEX> <SIZ> <POW> <APP> <INT> <EDU>
        Example: !aas stats 40 50 45 60 65 55 80 85
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        # Validate ranges
        values = [str_val, con_val, dex_val, siz_val, pow_val, app_val, int_val, edu_val]
        if any(v < 1 or v > 99 for v in values):
            await ctx.send("All characteristics must be between 1 and 99.")
            return

        character["characteristics"] = {
            "STR": str_val, "CON": con_val, "DEX": dex_val, "SIZ": siz_val,
            "POW": pow_val, "APP": app_val, "INT": int_val, "EDU": edu_val,
        }

        # Recalculate derived values and set to max
        self._recalc_derived(character)
        resources = character["resources"]
        resources["hp"]["current"] = resources["hp"]["max"]
        resources["mp"]["current"] = resources["mp"]["max"]
        resources["sanity"]["current"] = character["characteristics"]["POW"]
        resources["luck"]["current"] = 0
        resources["luck"]["starting"] = 0

        self._save_character(ctx.author.id, character)

        hp = resources["hp"]
        mp = resources["mp"]
        san = resources["sanity"]

        msg = f"**Characteristics set:**\n"
        msg += f"STR {str_val} | CON {con_val} | DEX {dex_val} | SIZ {siz_val}\n"
        msg += f"POW {pow_val} | APP {app_val} | INT {int_val} | EDU {edu_val}\n"
        msg += f"Derived: HP {hp['max']}/{hp['max']}, MP {mp['max']}/{mp['max']}, SAN {san['current']}/{san['max']}"
        await ctx.send(msg)

    @aas.command(name="set")
    async def aas_set(self, ctx, target: str, value: str):
        """
        Set a characteristic or resource.

        Usage: !aas set <target> <value>
        Targets: STR, CON, DEX, SIZ, POW, APP, INT, EDU, hp, mp, san, luck, xp
        Value: absolute number or +N/-N for delta

        Examples:
            !aas set STR 55
            !aas set hp -3
            !aas set luck +5
            !aas set xp 2
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        target_upper = target.upper()
        target_lower = target.lower()

        # Parse value (absolute or delta)
        is_delta = value.startswith('+') or value.startswith('-')
        try:
            num_value = int(value)
        except ValueError:
            if value.lower() == "max":
                num_value = None  # Special case for max
                is_delta = False
            else:
                await ctx.send(f"Invalid value: {value}")
                return

        # Characteristic
        if target_upper in CHARACTERISTICS:
            old_val = character["characteristics"].get(target_upper, 0)
            if is_delta:
                new_val = old_val + num_value
            else:
                new_val = num_value

            new_val = max(1, min(99, new_val))
            character["characteristics"][target_upper] = new_val
            self._recalc_derived(character)
            self._add_pending_change(character, f"{target_upper}: {old_val}→{new_val}")
            self._save_character(ctx.author.id, character)
            await ctx.send(f"**{target_upper}:** {old_val} → {new_val}")
            return

        # Resource
        if target_lower in RESOURCES:
            resources = character.get("resources", {})

            if target_lower == "xp":
                old_val = resources.get("xp", 0)
                if is_delta:
                    new_val = old_val + num_value
                else:
                    new_val = num_value
                new_val = max(0, new_val)
                resources["xp"] = new_val
                self._add_pending_change(character, f"xp: {old_val}→{new_val}")
                self._save_character(ctx.author.id, character)
                await ctx.send(f"**XP:** {old_val} → {new_val}")
                return

            # hp, mp, san, luck have current/max structure
            res_key = {"hp": "hp", "mp": "mp", "san": "sanity", "luck": "luck"}[target_lower]
            res = resources.get(res_key, {"current": 0, "max": 0})

            old_val = res.get("current", 0)
            max_val = res.get("max", 99)

            if num_value is None:  # "max" keyword
                new_val = max_val
            elif is_delta:
                new_val = old_val + num_value
            else:
                new_val = num_value

            # Clamp (allow negative for HP death tracking)
            if target_lower != "hp":
                new_val = max(0, min(max_val, new_val))
            else:
                new_val = min(max_val, new_val)

            res["current"] = new_val
            resources[res_key] = res
            character["resources"] = resources

            # Track change
            delta_str = f"{num_value:+d}" if is_delta and num_value else ""
            self._add_pending_change(character, f"{target_lower}: {old_val}→{new_val} ({delta_str})" if delta_str else f"{target_lower}: {old_val}→{new_val}")
            self._save_character(ctx.author.id, character)

            # Special messages
            msg = f"**{target_upper}:** {new_val}/{max_val}"
            if delta_str:
                msg += f" ({delta_str})"

            if target_lower == "hp":
                con = character["characteristics"].get("CON", 0)
                threshold = calc_major_wound_threshold(con)
                if new_val <= threshold and old_val > threshold:
                    msg += "\n**Major Wound!** Penalty die to all actions."
                    character["conditions"]["major_wound"] = True
                    self._save_character(ctx.author.id, character)
                if new_val <= 0:
                    msg += "\n**Unconscious!**"
                if new_val < -con:
                    msg += "\n**Dead.**"

            await ctx.send(msg)
            return

        await ctx.send(f"Unknown target: {target}. Use a characteristic (STR, CON...) or resource (hp, mp, san, luck, xp).")

    @aas.command(name="skill")
    async def aas_skill(self, ctx, skill_name: str, value: int):
        """
        Set a skill value.

        Usage: !aas skill <skill_name> <value>
        Examples:
            !aas skill "Library Use" 75
            !aas skill Occult 45
            !aas skill Wizardry 35  (creates custom skill*)
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        value = max(0, min(99, value))
        normalized = normalize_skill_name(skill_name)
        is_custom = not is_standard_skill(normalized)

        skills = character.get("skills", {})
        old_data = skills.get(normalized, {})
        old_val = old_data.get("value", 0)

        skills[normalized] = {
            "value": value,
            "checked": old_data.get("checked", False),
            "eligible": old_data.get("eligible", False),
            "custom": is_custom,
        }
        character["skills"] = skills

        # Recalc sanity max if Cthulhu Mythos changed
        if normalized == "Cthulhu Mythos":
            self._recalc_derived(character)

        self._add_pending_change(character, f"{normalized}: {old_val}→{value}")
        self._save_character(ctx.author.id, character)

        marker = "*" if is_custom else ""
        await ctx.send(f"**{normalized}{marker}** set to {value}")

    @aas.command(name="skills")
    async def aas_skills(self, ctx, user: discord.Member = None):
        """
        List all trained skills.

        Usage: !aas skills [@user]
        """
        target = user or ctx.author
        character = self._load_character(target.id)

        if not character:
            if target == ctx.author:
                await ctx.send("You don't have a character. Use `!aas create` first.")
            else:
                await ctx.send(f"{target.display_name} doesn't have a character.")
            return

        skills = character.get("skills", {})
        if not skills:
            await ctx.send("No trained skills.")
            return

        sorted_skills = sorted(skills.items(), key=lambda x: x[1].get("value", 0), reverse=True)

        lines = []
        for skill_name, skill_data in sorted_skills:
            value = skill_data.get("value", 0)
            markers = ""
            if skill_data.get("custom"):
                markers += "*"
            if skill_data.get("checked"):
                markers += "✓"
            if skill_data.get("eligible"):
                markers += "↑"
            lines.append(f"{skill_name}{markers}: {value}")

        embed = discord.Embed(
            title=f"Skills - {character.get('name', 'Unknown')}",
            description="\n".join(lines),
            color=discord.Color.dark_purple()
        )
        await ctx.send(embed=embed)

    @aas.command(name="import")
    async def aas_import(self, ctx):
        """
        Import character from Dhole's House JSON.

        Usage: Attach a .json file and type !aas import
        """
        if self._load_character(ctx.author.id):
            await ctx.send("You already have a character. Use `!aas delete` first.")
            return

        if not ctx.message.attachments:
            await ctx.send("Attach a .json file from Dhole's House.")
            return

        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith('.json'):
            await ctx.send("Please attach a .json file.")
            return

        try:
            json_data = await attachment.read()
            json_str = json_data.decode('utf-8')
            character, skill_count = parse_dholes_house_json(json_str)
        except ImportError as e:
            await ctx.send(str(e))
            return
        except Exception as e:
            logger.error(f"Import error: {e}")
            await ctx.send("Could not parse JSON file.")
            return

        self._save_character(ctx.author.id, character)

        chars = character["characteristics"]
        resources = character["resources"]
        hp = resources["hp"]
        mp = resources["mp"]
        san = resources["sanity"]
        luck = resources["luck"]

        msg = f"**Imported:** {character['name']}"
        if character['occupation']:
            msg += f" ({character['occupation']})"
        msg += f"\nSTR {chars['STR']} | CON {chars['CON']} | DEX {chars['DEX']} | SIZ {chars['SIZ']}"
        msg += f"\nPOW {chars['POW']} | APP {chars['APP']} | INT {chars['INT']} | EDU {chars['EDU']}"
        msg += f"\nHP {hp['current']}/{hp['max']} | MP {mp['current']}/{mp['max']} | SAN {san['current']}/{san['max']} | Luck {luck['current']}"
        msg += f"\n{skill_count} skills imported."
        await ctx.send(msg)

    @aas.command(name="export")
    async def aas_export(self, ctx):
        """
        Export character as JSON file.

        Usage: !aas export
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        json_str = export_to_dholes_house(character)
        filename = f"{character.get('name', 'character').replace(' ', '_')}.json"

        await ctx.send(
            f"Character export for {character.get('name', 'Unknown')}:",
            file=discord.File(
                fp=__import__('io').BytesIO(json_str.encode('utf-8')),
                filename=filename
            )
        )

    @aas.command(name="delete")
    async def aas_delete(self, ctx, confirm: str = None):
        """
        Delete your character.

        Usage: !aas delete
        Confirmation: !aas delete confirm (within 30 seconds)
        """
        user_id = ctx.author.id
        character = self._load_character(user_id)

        if not character:
            await ctx.send("You don't have a character.")
            return

        if confirm and confirm.lower() == "confirm":
            # Check if we have a pending delete
            pending_time = self._pending_deletes.get(user_id)
            if pending_time:
                elapsed = (datetime.now(timezone.utc) - pending_time).total_seconds()
                if elapsed <= 30:
                    # Delete the character
                    path = self._get_character_path(user_id)
                    try:
                        path.unlink()
                        del self._pending_deletes[user_id]
                        await ctx.send(f"**{character.get('name', 'Character')}** has been deleted.")
                        return
                    except IOError as e:
                        logger.error(f"Failed to delete character {user_id}: {e}")
                        await ctx.send("Failed to delete character.")
                        return

            await ctx.send("No pending delete. Use `!aas delete` first.")
            return

        # Start pending delete
        self._pending_deletes[user_id] = datetime.now(timezone.utc)
        await ctx.send(
            f"Are you sure you want to delete **{character.get('name', 'your character')}**?\n"
            f"Type `!aas delete confirm` within 30 seconds to confirm."
        )

    @aas.command(name="help")
    async def aas_help(self, ctx, command: str = None):
        """
        Show command reference.

        Usage: !aas help [command]
        """
        if command:
            await self._show_command_help(ctx, command)
        else:
            await self._show_main_help(ctx)

    async def _show_main_help(self, ctx):
        """Display main help."""
        help_text = """**AAS Character Management**

**Character:**
`!aas create <name> [occupation]` - Create character
`!aas sheet [@user]` - View character sheet
`!aas stats <STR CON DEX SIZ POW APP INT EDU>` - Set all characteristics
`!aas set <stat> <value>` - Set stat/resource (+N/-N for delta)
`!aas skill <name> <value>` - Set skill value
`!aas skills` - List all skills
`!aas import` - Import from Dhole's House (attach .json)
`!aas export` - Export to JSON
`!aas delete` - Delete character

**Rolls:**
`!skill <name> [difficulty] [modifier]` - Skill check
`!char <STAT> [difficulty] [modifier]` - Characteristic check
Difficulty: regular, hard, extreme
Modifier: +N bonus dice, -N penalty dice

**Resources:**
`!hp [delta]` - View/modify HP
`!mp [delta]` - View/modify MP
`!san [delta]` - View/modify Sanity
`!luck [delta]` - View/modify Luck

**Advancement:**
`!aas check <skill>` - Mark skill for advancement
`!aas advance` - Roll advancement eligibility
`!aas spend <skill> [amount]` - Spend XP on eligible skill

**Session:**
`!aas save [note]` - Save session to changelog
`!aas history [count]` - View past sessions
`!aas wound [on|off]` - Toggle major wound

Type `!aas help <command>` for details."""
        await ctx.send(help_text)

    async def _show_command_help(self, ctx, command: str):
        """Display help for specific command."""
        help_texts = {
            "create": """**!aas create** - Create a new character

Syntax: `!aas create <name> [occupation]`

Arguments:
  name - Character name (quotes if spaces)
  occupation - Optional occupation

Examples:
```
!aas create "Harvey Walters"
!aas create "Harvey Walters" "Professor"
!aas create Harvey
```""",
            "set": """**!aas set** - Set characteristic or resource

Syntax: `!aas set <target> <value>`

Targets:
  Characteristics: STR, CON, DEX, SIZ, POW, APP, INT, EDU
  Resources: hp, mp, san, luck, xp

Values:
  Absolute: `55` sets to 55
  Delta: `+5` adds 5, `-3` subtracts 3
  Max: `max` restores to maximum (resources only)

Examples:
```
!aas set STR 55
!aas set hp -3
!aas set luck +5
!aas set san max
!aas set xp 2
```""",
            "skill": """**!aas skill** - Set skill value

Syntax: `!aas skill <name> <value>`

Creates custom skill (*) if not in standard list.

Examples:
```
!aas skill "Library Use" 75
!aas skill Occult 45
!aas skill "Cthulhu Mythos" 12
!aas skill Wizardry 35
```""",
            "advance": """**!aas advance** - Roll for skill improvement

Syntax: `!aas advance`

At end of session, rolls d100 for each checked skill.
If roll > skill value, skill becomes ELIGIBLE.
Spend XP on eligible skills with `!aas spend`.

BURGE variant rules:
- Roll must EXCEED skill value
- Extreme success checkmarks get penalty die
- 1 XP = +1 to eligible skill

See also: `!aas check`, `!aas spend`""",
            "spend": """**!aas spend** - Spend XP on eligible skill

Syntax: `!aas spend <skill> [amount]`

Only works on skills that passed advancement roll.
Default amount is 1 XP.

Examples:
```
!aas spend "Library Use"
!aas spend "Library Use" 2
```""",
        }

        cmd_lower = command.lower()
        if cmd_lower in help_texts:
            await ctx.send(help_texts[cmd_lower])
        else:
            await ctx.send(f"No help available for `{command}`. Try `!aas help`.")

    # ========== Group 2: Dice Rolling ==========

    @commands.command(name="skill", aliases=["sk"])
    async def cmd_skill(self, ctx, skill_name: str, difficulty: str = "regular", modifier: str = None):
        """
        Roll a skill check.

        Usage: !skill <skill_name> [difficulty] [modifier]
        Difficulty: regular, hard, extreme
        Modifier: +N bonus dice, -N penalty dice

        Examples:
            !skill "Spot Hidden"
            !skill "Spot Hidden" hard
            !skill "Spot Hidden" hard +1
            !skill Listen +2
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        # Handle case where difficulty is actually a modifier
        if difficulty.startswith('+') or difficulty.startswith('-'):
            modifier = difficulty
            difficulty = "regular"

        if difficulty not in ("regular", "hard", "extreme"):
            await ctx.send("Difficulty must be: regular, hard, or extreme")
            return

        normalized = normalize_skill_name(skill_name)
        skills = character.get("skills", {})
        skill_data = skills.get(normalized, {})

        # Get skill value
        if normalized in skills:
            skill_value = skill_data.get("value", 0)
            is_base = False
            is_custom = skill_data.get("custom", False)
        elif is_standard_skill(normalized):
            # Standard skill with base value
            skill_value = get_skill_base(normalized, character.get("characteristics", {}))
            is_base = True
            is_custom = False
        else:
            # Custom skill not set
            skill_value = 0
            is_base = False
            is_custom = True

        # Parse modifiers
        bonus, penalty = parse_modifier(modifier) if modifier else (0, 0)

        # Apply major wound penalty
        if character.get("conditions", {}).get("major_wound"):
            penalty += 1

        result = skill_check(
            skill_name=normalized,
            skill_value=skill_value,
            difficulty=difficulty,
            bonus_dice=bonus,
            penalty_dice=penalty,
            is_base=is_base,
            is_custom=is_custom,
        )

        # Auto-check on success
        if result.is_success and not is_base:
            if normalized not in skills:
                skills[normalized] = {"value": skill_value, "checked": False, "eligible": False, "custom": is_custom}
            skills[normalized]["checked"] = True
            if result.success_level == SuccessLevel.EXTREME:
                skills[normalized]["extreme"] = True
            character["skills"] = skills
            self._save_character(ctx.author.id, character)

        msg = format_roll_result(result)
        if character.get("conditions", {}).get("major_wound"):
            msg += "\n(Major wound: +1 penalty die)"
        if result.is_success:
            msg += "\n✓ Skill checked for advancement"

        await ctx.send(msg)

    @commands.command(name="char", aliases=["ch"])
    async def cmd_char(self, ctx, char_name: str, difficulty: str = "regular", modifier: str = None):
        """
        Roll a characteristic check.

        Usage: !char <CHAR> [difficulty] [modifier]
        Examples:
            !char STR hard
            !char POW +1
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        char_upper = char_name.upper()
        if char_upper not in CHARACTERISTICS:
            await ctx.send(f"Invalid characteristic. Use: {', '.join(CHARACTERISTICS)}")
            return

        # Handle case where difficulty is actually a modifier
        if difficulty.startswith('+') or difficulty.startswith('-'):
            modifier = difficulty
            difficulty = "regular"

        if difficulty not in ("regular", "hard", "extreme"):
            await ctx.send("Difficulty must be: regular, hard, or extreme")
            return

        char_value = character.get("characteristics", {}).get(char_upper, 0)
        bonus, penalty = parse_modifier(modifier) if modifier else (0, 0)

        # Apply major wound penalty
        if character.get("conditions", {}).get("major_wound"):
            penalty += 1

        result = characteristic_check(
            char_name=char_upper,
            char_value=char_value,
            difficulty=difficulty,
            bonus_dice=bonus,
            penalty_dice=penalty,
        )

        msg = format_roll_result(result)
        if character.get("conditions", {}).get("major_wound"):
            msg += "\n(Major wound: +1 penalty die)"

        await ctx.send(msg)

    # ========== Group 3: Resource Tracking ==========

    @commands.command(name="hp")
    async def cmd_hp(self, ctx, delta: str = None):
        """
        View or modify HP.

        Usage: !hp [delta]
        Examples: !hp, !hp -3, !hp +2, !hp max
        """
        await self._resource_command(ctx, "hp", delta)

    @commands.command(name="mp")
    async def cmd_mp(self, ctx, delta: str = None):
        """
        View or modify MP.

        Usage: !mp [delta]
        Examples: !mp, !mp -5, !mp +3, !mp max
        """
        await self._resource_command(ctx, "mp", delta)

    @commands.command(name="san")
    async def cmd_san(self, ctx, delta: str = None):
        """
        View or modify Sanity.

        Usage: !san [delta]
        Supports dice: !san -1d6
        Examples: !san, !san -3, !san -1d6, !san +1d3
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        san = character.get("resources", {}).get("sanity", {"current": 0, "max": 99})

        if delta is None:
            await ctx.send(f"**Sanity:** {san['current']}/{san['max']}")
            return

        # Check for dice notation
        if 'd' in delta.lower():
            # Parse dice (e.g., -1d6, +1d3)
            sign = -1 if delta.startswith('-') else 1
            dice_str = delta.lstrip('+-')
            result = roll_dice(dice_str)
            if result is None:
                await ctx.send(f"Invalid dice notation: {delta}")
                return
            change = sign * result['natural']
            dice_info = f" (rolled {dice_str}={result['natural']})"
        else:
            try:
                change = int(delta)
                dice_info = ""
            except ValueError:
                if delta.lower() == "max":
                    change = san['max'] - san['current']
                    dice_info = ""
                else:
                    await ctx.send(f"Invalid value: {delta}")
                    return

        old_val = san['current']
        new_val = max(0, min(san['max'], old_val + change))
        san['current'] = new_val
        character["resources"]["sanity"] = san

        self._add_pending_change(character, f"san: {old_val}→{new_val}{dice_info}")
        self._save_character(ctx.author.id, character)

        msg = f"**Sanity:** {new_val}/{san['max']} ({change:+d}{dice_info})"
        await ctx.send(msg)

    @commands.command(name="luck")
    async def cmd_luck(self, ctx, delta: str = None):
        """
        View or modify Luck.

        Usage: !luck [delta]
        Examples: !luck, !luck -10, !luck +5
        """
        await self._resource_command(ctx, "luck", delta)

    async def _resource_command(self, ctx, resource: str, delta: str):
        """Generic resource view/modify handler."""
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        res_key = {"hp": "hp", "mp": "mp", "luck": "luck"}[resource]
        res = character.get("resources", {}).get(res_key, {"current": 0, "max": 0})

        if delta is None:
            await ctx.send(f"**{resource.upper()}:** {res['current']}/{res['max']}")
            return

        try:
            change = int(delta)
        except ValueError:
            if delta.lower() == "max":
                change = res['max'] - res['current']
            else:
                await ctx.send(f"Invalid value: {delta}")
                return

        old_val = res['current']
        new_val = old_val + change

        # Clamp
        if resource != "hp":
            new_val = max(0, min(res['max'], new_val))
        else:
            new_val = min(res['max'], new_val)

        res['current'] = new_val
        character["resources"][res_key] = res

        self._add_pending_change(character, f"{resource}: {old_val}→{new_val} ({change:+d})")
        self._save_character(ctx.author.id, character)

        msg = f"**{resource.upper()}:** {new_val}/{res['max']} ({change:+d})"

        # HP special messages
        if resource == "hp":
            con = character["characteristics"].get("CON", 0)
            threshold = calc_major_wound_threshold(con)
            if new_val <= threshold and old_val > threshold:
                msg += "\n**Major Wound!** Penalty die to all actions."
                character["conditions"]["major_wound"] = True
                self._save_character(ctx.author.id, character)
            if new_val <= 0:
                msg += "\n**Unconscious!**"
            if new_val < -con:
                msg += "\n**Dead.**"

        await ctx.send(msg)

    # ========== Group 4: Skill Advancement ==========

    @aas.command(name="check")
    async def aas_check(self, ctx, skill_name: str):
        """
        Mark a skill for advancement.

        Usage: !aas check <skill_name>
        Note: Skills are auto-checked on successful rolls.
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        normalized = normalize_skill_name(skill_name)
        skills = character.get("skills", {})

        if normalized not in skills:
            # Add the skill if it doesn't exist
            is_custom = not is_standard_skill(normalized)
            base_val = get_skill_base(normalized, character.get("characteristics", {})) if not is_custom else 0
            skills[normalized] = {"value": base_val, "checked": True, "eligible": False, "custom": is_custom}
        else:
            skills[normalized]["checked"] = True

        character["skills"] = skills
        self._save_character(ctx.author.id, character)
        await ctx.send(f"**{normalized}** checked for advancement.")

    @aas.command(name="advance")
    async def aas_advance(self, ctx):
        """
        Roll for skill improvement eligibility.

        Usage: !aas advance

        Rolls d100 for each checked skill.
        Roll > skill value = eligible for improvement.
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        skills = character.get("skills", {})
        checked_skills = [(name, data) for name, data in skills.items() if data.get("checked")]

        if not checked_skills:
            await ctx.send("No skills checked for advancement.")
            return

        xp = character.get("resources", {}).get("xp", 0)
        results = []
        eligible_count = 0

        for skill_name, skill_data in checked_skills:
            skill_value = skill_data.get("value", 0)
            extreme = skill_data.get("extreme", False)

            # Roll d100 (extreme success gets penalty die = easier to pass)
            if extreme:
                roll_result = roll_dice("2d100kh1")  # Keep highest = more likely to exceed
            else:
                roll_result = roll_dice("1d100")

            roll = roll_result['natural'] if roll_result else 50

            if roll > skill_value:
                results.append(f"  {skill_name} ({skill_value}): rolled {roll} → **ELIGIBLE**")
                skills[skill_name]["eligible"] = True
                eligible_count += 1
            else:
                results.append(f"  {skill_name} ({skill_value}): rolled {roll} → failed")

            # Clear check marks
            skills[skill_name]["checked"] = False
            skills[skill_name]["extreme"] = False

        character["skills"] = skills
        self._save_character(ctx.author.id, character)

        msg = f"**Advancement Rolls** (XP: {xp})\n\n"
        msg += "\n".join(results)
        if eligible_count > 0:
            msg += f"\n\n{eligible_count} skill(s) eligible. Spend XP with: `!aas spend <skill>`"
        await ctx.send(msg)

    @aas.command(name="spend")
    async def aas_spend(self, ctx, skill_name: str, amount: int = 1):
        """
        Spend XP to improve an eligible skill.

        Usage: !aas spend <skill_name> [amount]
        Default: 1 XP = +1 to skill
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        normalized = normalize_skill_name(skill_name)
        skills = character.get("skills", {})
        resources = character.get("resources", {})
        xp = resources.get("xp", 0)

        if normalized not in skills:
            await ctx.send(f"Skill not found: {normalized}")
            return

        skill_data = skills[normalized]
        if not skill_data.get("eligible"):
            await ctx.send(f"**{normalized}** did not pass advancement roll.")
            return

        if xp < amount:
            await ctx.send(f"Not enough XP. Have {xp}, need {amount}.")
            return

        old_val = skill_data.get("value", 0)
        new_val = min(99, old_val + amount)
        actual_gain = new_val - old_val

        skills[normalized]["value"] = new_val
        skills[normalized]["eligible"] = False
        resources["xp"] = xp - actual_gain

        character["skills"] = skills
        character["resources"] = resources
        self._add_pending_change(character, f"{normalized}: {old_val}→{new_val} (advanced)")
        self._save_character(ctx.author.id, character)

        await ctx.send(f"**{normalized}:** {old_val} → {new_val} ({actual_gain} XP spent, {resources['xp']} remaining)")

    # ========== Group 5: Session Management ==========

    @aas.command(name="save")
    async def aas_save(self, ctx, *, note: str = ""):
        """
        Save session to changelog.

        Usage: !aas save [note]
        Example: !aas save Session 12 - The Lighthouse
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        pending = character.get("pending", [])
        if not pending:
            await ctx.send("No pending changes to save.")
            return

        # Increment version
        version = character.get("version", 0) + 1
        character["version"] = version

        # Create changelog entry
        entry = {
            "v": version,
            "ts": datetime.now(timezone.utc).isoformat(),
            "note": note or f"Session {version}",
            "changes": pending.copy(),
        }

        changelog = character.get("changelog", [])
        changelog.insert(0, entry)  # Most recent first
        character["changelog"] = changelog
        character["pending"] = []

        self._save_character(ctx.author.id, character)

        msg = f"**Session saved** (v{version}): \"{entry['note']}\"\n"
        msg += f"  {len(pending)} changes recorded:\n"
        for change in pending[:5]:
            msg += f"  - {change}\n"
        if len(pending) > 5:
            msg += f"  ... and {len(pending) - 5} more"

        await ctx.send(msg)

    @aas.command(name="history")
    async def aas_history(self, ctx, count: int = 5):
        """
        View session changelog.

        Usage: !aas history [count]
        Default: last 5 sessions
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        changelog = character.get("changelog", [])
        if not changelog:
            await ctx.send("No session history.")
            return

        name = character.get("name", "Unknown")
        lines = [f"**{name} - Session History**\n"]

        for entry in changelog[:count]:
            ts = entry.get("ts", "")[:10]  # Just the date
            note = entry.get("note", "")
            changes = entry.get("changes", [])
            v = entry.get("v", "?")

            lines.append(f"**v{v}** ({ts}) \"{note}\"")
            changes_str = ", ".join(changes[:3])
            if len(changes) > 3:
                changes_str += f", +{len(changes) - 3} more"
            lines.append(f"  {changes_str}\n")

        await ctx.send("\n".join(lines))

    # ========== Group 6: Conditions ==========

    @aas.command(name="wound")
    async def aas_wound(self, ctx, state: str = None):
        """
        Toggle or set major wound status.

        Usage: !aas wound [on|off]
        """
        character = self._load_character(ctx.author.id)
        if not character:
            await ctx.send("You don't have a character. Use `!aas create` first.")
            return

        conditions = character.get("conditions", {})
        current = conditions.get("major_wound", False)

        if state is None:
            new_state = not current
        elif state.lower() == "on":
            new_state = True
        elif state.lower() == "off":
            new_state = False
        else:
            await ctx.send("Use: `!aas wound`, `!aas wound on`, or `!aas wound off`")
            return

        conditions["major_wound"] = new_state
        character["conditions"] = conditions
        self._save_character(ctx.author.id, character)

        if new_state:
            await ctx.send("**Major Wound** active. Penalty die to all actions.")
        else:
            await ctx.send("Major wound cleared.")


async def setup(bot):
    await bot.add_cog(AAS(bot))
