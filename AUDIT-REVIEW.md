# pk.shado Review

## Summary

pk.shado is a Discord bot providing gaming RNG (dice, cards), Call of Cthulhu 7e character management (AAS), astrology readings with natal chart generation, weather, and various fun commands. The project is well-architected with good separation of concerns, comprehensive documentation, and a solid test suite (159+ tests). Overall health is **good** with some security concerns around secrets management.

## Critical Issues

- **[.env:1-3] API keys stored in plaintext** - While `.env` is gitignored, the file contains actual Discord bot token, OpenAI API key, and Geonames credentials in plaintext. These appear to be real keys. If this repo is ever shared or the machine compromised, these secrets are exposed. The OpenAI key format (`sk-proj-...`) suggests an active project key. **Severity: HIGH** - recommend using a secrets manager or at minimum ensuring backup/sync tools exclude this file.

- **[cogs/Thirstyboi.py:337] Bare except clause** - `try/except:` without exception type catches everything including KeyboardInterrupt, SystemExit. This can mask serious errors and make debugging difficult.
  ```python
  try:
      users, allowed_chan = dat_import()
  except:  # Too broad
      users = dict()
  ```

- **[app.py:137-153] killbot command has no permissions check** - Anyone can run `!killbot` to shut down the bot. Missing `@commands.has_permissions()` or `@commands.is_owner()` decorator.

## Recommendations

### High Priority

1. **[Security] Implement secrets management** - Use environment-only secrets (never write to `.env`), or use a secrets manager like HashiCorp Vault, AWS Secrets Manager, or `pass`. At minimum, rotate the exposed OpenAI key.

2. **[Security] Add permission check to killbot** - Add `@commands.is_owner()` decorator to prevent unauthorized shutdowns:
   ```python
   @bot.command(pass_context=True)
   @commands.is_owner()
   async def killbot(ctx):
   ```

3. **[Code Quality] Replace bare except clauses** - In `cogs/Thirstyboi.py:337`, change to specific exception handling:
   ```python
   except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
       logger.error(f"Failed to load data: {e}")
   ```

4. **[Security] Validate/sanitize user inputs in `toss` command** - `cogs/Games.py:108-123` accepts comma-separated items without validation. While not directly exploitable, consider length limits.

### Medium Priority

5. **[Architecture] Add rate limiting** - As noted in ARCHITECTURE.md "Future Improvements", the bot lacks rate limiting. Heavy usage could exhaust API quotas (OpenAI, OpenWeather, Geonames).

6. **[Code Quality] Remove unused imports** - `cogs/app.py:3` imports `string` which is never used.

7. **[Code Quality] `from .Utils import *`** - Several cogs use wildcard imports (`cogs/Thirstyboi.py:8`, `cogs/Games.py:1`). This pollutes namespace and makes dependencies unclear. Use explicit imports.

8. **[Testing] Missing tests for Astrologer cog** - Only `test_kerykeion.py` covers astrology. The main Astrologer cog commands (`!astrology`, `!setbirthday`, `!chartimage`) have no tests. The AAS cog has excellent test coverage as a model.

9. **[Code Quality] Inconsistent command patterns** - Some cogs use `pass_context=True` (deprecated) while newer code doesn't. Standardize on modern discord.py patterns.

10. **[Documentation] Type hints incomplete** - AAS cog has good type hints (`cogs/aas/cog.py`), but other cogs like Thirstyboi, Games lack them.

### Low Priority

11. **[Style] Docstring inconsistency** - `UserData` class in Thirstyboi has single quotes for docstrings while most code uses triple double quotes.

12. **[Code Quality] Magic number 69** - `cogs/Thirstyboi.py:92` `self.interval = 69` (autosave interval). While intentionally humorous, consider naming it `AUTOSAVE_INTERVAL_SECONDS = 69`.

13. **[Dependencies] Pin all requirements versions** - `requirements.txt` only pins `kerykeion==4.26.3`. Other deps (`discord.py`, `openai`, etc.) should be pinned for reproducibility.

## Scores (1-10)

| Category | Score | Notes |
|----------|-------|-------|
| **Code Quality** | 7 | Clean code, good patterns, some bare excepts and wildcard imports |
| **Architecture** | 8 | Excellent modular design, good separation (AAS/Astrologer packages), clear responsibilities |
| **Completeness** | 7 | Feature-rich, good AAS test coverage, missing tests for Astrologer/Weather/Thirstyboi |
| **Standards** | 7 | Generally consistent, some deprecated patterns (`pass_context`), incomplete type hints |

## Notes

### Positive Patterns

- **Excellent documentation** - ARCHITECTURE.md is thorough and well-maintained. README covers all commands comprehensively.
- **AAS cog is exemplary** - Clear separation into `cog.py`, `data.py`, `roller.py`, `importer.py`. Well-tested with 143+ tests covering the module. Good use of dataclasses (`RollResult`).
- **JSON data storage** - Good security decision over pickle (explicitly mentioned in ARCHITECTURE.md).
- **HTTP session reuse** - `Utils.py` properly implements connection pooling for performance.
- **Caching** - Astrologer uses SHA-256 based caching for natal charts (deterministic results).
- **Good error handling** - Most API calls have proper try/except with logging.

### Concerns

- **OpenAI dependency for readings** - CipherOracle and Astrologer depend on OpenAI API. No graceful degradation if API is unavailable or quota exceeded.
- **No database** - All data in JSON files. Fine for current scale but noted as future improvement.
- **No slash commands** - Still using prefix commands. Discord is pushing toward slash commands.

### Technical Debt

- The `pk.shado/pk.shado/` subdirectory contains an old venv that should be cleaned up.
- `test_bot.py` at project root (4.1KB) seems redundant with `tests/` directory.

### File Statistics

- **Total lines**: ~7,340 (source + tests)
- **Test coverage focus**: AAS cog well-covered, other cogs minimally tested
- **Last significant update**: January 2026 (active development)
