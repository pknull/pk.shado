---
version: 1.0.0
lastUpdated: 2025-12-22
lifecycle: active
stakeholder: pknull
changeTrigger: session-completion
validatedBy: manual-review
dependencies: [projectbrief.md, techEnvironment.md]
---

# Active Context: pk.shado Discord Bot

## Current Status

**Phase**: Active Development
**Date**: 2025-12-22
**Focus**: AAS Character Management System (Phase 1 MVP complete)

## Recent Changes

- AAS Cog Implementation (2025-12-22):
  - Created `cogs/aas_data.py`: Skill defaults, characteristics, success level calculation
  - Created `cogs/aas_roller.py`: CoC d100 mechanics with bonus/penalty dice
  - Created `cogs/aas_importer.py`: Dhole's House JSON parser and exporter
  - Created `cogs/AAS.py`: Main cog with all commands (~500 lines)
  - Added "AAS" to cogs list in `app.py`
  - Created comprehensive test suite (143 tests passing):
    - `tests/test_aas_data.py` (40 tests)
    - `tests/test_aas_roller.py` (42 tests)
    - `tests/test_aas_importer.py` (35 tests)
    - `tests/test_aas_cog.py` (26 tests)
  - Created `pytest.ini` for pytest-asyncio configuration
  - Plan file: `/home/pknull/.claude/plans/shimmying-dancing-noodle.md`

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

AAS Character Management implementation session (2025-12-22):
- Implemented Phase 1 MVP for BURGE (CoC 7e variant) character management
- Key discoveries:
  - rpg-dice DiceThrower returns `{'natural': [list], 'modified': [list], 'total': str}` format
  - Discord.py command callbacks require `.callback(cog, ctx, ...)` invocation for testing
  - Dhole's House JSON uses `Skills.Skill` nested array with string values
- Created 143 tests covering all modules
- Phase 2/3 features documented in plan but not yet implemented (pushed rolls, sanity loss rolls, bout of madness)
