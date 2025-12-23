---
version: 1.2.0
lastUpdated: 2025-12-23
lifecycle: active
stakeholder: pknull
changeTrigger: session-completion
validatedBy: manual-review
dependencies: [projectbrief.md, techEnvironment.md]
---

# Active Context: pk.shado Discord Bot

## Current Status

**Phase**: Active Development
**Date**: 2025-12-23
**Focus**: AAS Character Management System (Phase 1 complete, all issues resolved)

## Recent Changes

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
