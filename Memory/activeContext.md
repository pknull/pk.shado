---
version: 1.4.0
lastUpdated: 2026-01-17
lifecycle: active
stakeholder: pknull
changeTrigger: session-completion
validatedBy: manual-review
dependencies: [projectbrief.md, techEnvironment.md]
---

# Active Context: pk.shado Discord Bot

## Current Status

**Phase**: Active Development
**Date**: 2026-01-17
**Focus**: Code audit remediation (security and code quality fixes)

## Recent Changes

- Code Audit Remediation (2026-01-17):
  - Security: Added `@commands.is_owner()` to `killbot` command (app.py:137)
  - Code quality: Removed bare `except:` clause in Thirstyboi.py setup() function
  - Code quality: Removed unused `import string` from app.py
  - Code quality: Replaced wildcard imports with explicit imports
    - Games.py: `from .Utils import *` → `from .Utils import make_embed`
    - Thirstyboi.py: Removed unused `from .Utils import *` entirely
  - Code quality: Removed deprecated `pass_context=True` from 10 command decorators
  - Code quality: Added input validation to `!toss` command (max 100 items, 200 char limit)
  - Code quality: Extracted magic number to `AUTOSAVE_INTERVAL_SECONDS` constant
  - 161 tests passing
  - AUDIT-REVIEW.md documents remaining lower-priority items

- GitHub Issues #16, #17 + Style Refactor (2026-01-12):
  - Issue #16: Enable rolling luck/san as characteristics
    - Added `ROLLABLE_STATS` constant to `data.py`
    - Modified `!char` command to accept luck/san
    - Added `!luck roll [modifier]` and `!san roll [modifier]` syntax
    - Added `_roll_resource()` helper method
  - Issue #17: Add XP management command
    - Added `!xp [delta]` command for viewing/modifying XP
    - Added comprehensive test `test_xp_pool_shared_across_commands`
    - Verified XP shared correctly between `!xp`, `!aas set xp`, `!aas spend`
  - Style refactoring (from local code review):
    - Added `RESOURCE_KEY_MAP` constant to centralize resource key mapping
    - Added `_get_resource_value()` helper to eliminate duplicate lookups
    - Made control flow consistent (early return pattern in cmd_luck)
  - Both GitHub issues closed via `gh issue close`
  - 151 tests passing

- Cog Restructure & Bug Fixes (2025-12-23):
  - Reorganized cogs into package subdirectories:
    - `cogs/AAS.py` → `cogs/aas/cog.py` (with data.py, roller.py, importer.py)
    - `cogs/Astrologer.py` → `cogs/astrologer/cog.py` (with core.py, geocoding.py, data.py)
    - Added `__init__.py` files for proper package imports
  - Fixed GitHub issues #13, #14, #15:
    - #13: Custom skills from Dhole's House "Misc" container now import as just the skill name
    - #14: Skill lookups now case-insensitive via `find_skill_in_dict()`
    - #15: Dice rolls now use Discord embeds with color-coded results
  - Data management improvements:
    - Migrated astrologer birth data from pickle to JSON
    - Moved static config files to cog packages
    - Simplified `.gitignore` to ignore entire `data/` directory
  - 159 tests passing (up from 143)

- AAS Cog Implementation (2025-12-22):
  - Created `cogs/aas/` package: data.py, roller.py, importer.py, cog.py
  - CoC 7e percentile mechanics with bonus/penalty dice
  - Dhole's House JSON import/export
  - Comprehensive test suite across all modules

- rpg-dice upgrade (2025-12-07):
  - dice_roller 0.1 → 0.2 (commit 5bbfc9d)
  - New: total check syntax (t>=N), total modifier syntax (=+N)
  - New: DiceProbability analyzer with exact combinatorics (sympy)
  - Dependencies: sympy 1.14.0, pyparsing 3.2.5

- Security hardening commit (722e340):
  - Removed debug_token fallback, fail fast on missing token
  - Replaced /tmp/ paths with secure tempfile module
  - Added try/finally for guaranteed temp file cleanup

- Repository cleanup commit (6cdcf4f):
  - Added tests/ directory with Kerykeion deterministic tests
  - Added AGENTS.md, GEMINI.md for multi-AI workflow transparency
  - Removed deprecated backup files (pickle security)
  - Updated .gitignore: cache/, *.code-workspace

- Asha framework onboarding complete

## Current Branch

`master` (synced with origin)

## Remaining Improvements (Optional)

| Priority | Task | Location |
|----------|------|----------|
| LOW | Unify HTTP clients | astrologer_geocoding.py (requests → aiohttp) |
| LOW | Rate limiting | Expensive commands (!astrology, !chartimage) |
| LOW | File permissions | JSON data files (chmod 600) |

## Known Issues

None critical. API key absence warnings retained for operator visibility.

## Open Questions

None.

## Session Notes

Code audit remediation (2026-01-17):
- Implemented fixes from AUDIT-REVIEW.md findings
- Critical: killbot command now requires bot owner permission
- High: Removed bare except that masked SystemExit/KeyboardInterrupt
- Medium: Cleaned up wildcard imports, deprecated parameters, magic numbers
- Key learnings:
  - `dat_import()` in Thirstyboi.py already handles all exceptions internally; outer try/except was redundant
  - Thirstyboi.py never actually used any Utils functions (wildcard import was dead code)
  - `pass_context=True` deprecated since discord.py 1.0; context always passed automatically
- Not addressed (requires infrastructure decisions): secrets management, rate limiting, requirements pinning
- 161 tests passing

GitHub issues + refactoring (2026-01-12):
- Closed GitHub issues #16 (luck/san rolling) and #17 (XP command)
- Local code review identified style issues; refactored for consistency
- Key learnings:
  - Resource key mapping (`san` → `sanity`) belongs in a constant, not inline dicts
  - Helper methods reduce duplication and improve testability
  - Early return pattern more readable than if/else for guard clauses
- 151 tests passing (down from 159 due to test consolidation in prior session)

Documentation update (2025-12-23, session 2):
- Updated README.md with comprehensive command reference (50+ commands)
- Updated ARCHITECTURE.md with new cog package structure
- Updated CHANGELOG.md with v0.21.0, v0.22.0, v0.23.0 entries
- Verified no open PRs or issues on GitHub

Cog restructure and GitHub issue fixes (2025-12-23, session 1):
- Reorganized cogs with supporting files into package subdirectories
- Fixed all 3 open GitHub issues for AAS cog
- Key learnings:
  - Python packages need `__init__.py` with proper exports for cog loading
  - Case-insensitive dict lookups need alias resolution first, then case folding
  - Discord embeds provide better UX for dice roll results (color-coded by success level)
- Verified git history clean of PII
- 159 tests passing
