---
version: 1.0.0
lastUpdated: 2025-12-07
lifecycle: active
stakeholder: pknull
changeTrigger: session-completion
validatedBy: manual-review
dependencies: [projectbrief.md, techEnvironment.md]
---

# Active Context: pk.shado Discord Bot

## Current Status

**Phase**: Maintenance
**Date**: 2025-12-06
**Focus**: Stable, security-hardened

## Recent Changes

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

Panel-driven cleanup session. Removed 2858 lines dead code, fixed HIGH priority security issues, pushed to origin.
