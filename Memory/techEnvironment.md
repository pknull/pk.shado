---
version: 1.0.0
lastUpdated: 2025-12-06
lifecycle: active
stakeholder: pknull
changeTrigger: tool-addition
validatedBy: manual-testing
dependencies: [projectbrief.md]
---

# Technical Environment: pk.shado Discord Bot

## Project Structure

```
/home/pknull/Code/pk.shado/
├── app.py                    # Main bot entry point
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (not in git)
├── asha/                     # Asha framework submodule
├── Memory/                   # Memory Bank (this location)
├── data/                     # Configuration and user data
│   ├── timezone_regions.json
│   ├── manual_coordinates.json
│   ├── astrologer_birth_data.json
│   └── thirstyboi_data.json
├── cogs/                     # Discord bot cogs (modules)
│   ├── Astrologer.py
│   ├── astrologer_core.py
│   ├── astrologer_data.py
│   ├── astrologer_geocoding.py
│   ├── Games.py
│   ├── Weather.py
│   ├── Thirstyboi.py
│   ├── CipherOracle.py
│   ├── Cleaner.py
│   ├── Anime.py
│   ├── Greetings.py
│   ├── Members.py
│   ├── Meme.py
│   ├── Passel.py
│   ├── Pets.py
│   ├── Reminders.py
│   └── Utils.py              # Shared utilities
├── tests/                    # Test files
├── logs/                     # Log files
├── cache/                    # Cache directory
├── venv/                     # Python virtual environment
├── ARCHITECTURE.md           # Architecture documentation
├── TESTING.md                # Testing guide
├── CHANGELOG.md              # Version history
└── README.md                 # Setup instructions
```

## Python Environment

**Python Version**: 3.8+
**Virtual Environment**: `/home/pknull/Code/pk.shado/venv`

**Activation**:
```bash
source /home/pknull/Code/pk.shado/venv/bin/activate
```

**Key Dependencies**:
- discord.py - Discord bot framework
- kerykeion==4.26.3 - Astrology calculations
- openai - AI-powered readings
- aiohttp - HTTP session management
- pillow - Image processing
- cairosvg - SVG rendering
- timezonefinder - Timezone lookup
- dotenv - Environment variable loading
- pytest - Testing framework

**Custom Dependencies**:
- git+https://github.com/pknull/rpg-dice.git@master
- git+https://github.com/pknull/rpg-card.git@master
- git+https://github.com/pknull/rpg-flip.git@master

## Environment Variables

Required in `.env`:
- `DISCORD_BOT_TOKEN` - Discord bot authentication
- `OPENWEATHER_API_KEY` - Weather API access
- `OPENAI_API_KEY` - AI reading generation
- `GEONAMES_USERNAME` - Geocoding service

## Running the Bot

**Local Development**:
```bash
cd /home/pknull/Code/pk.shado
source venv/bin/activate
python app.py
```

**Docker**:
```bash
./build.sh          # Production build
./build_local.sh    # Local testing build
```

## Testing

**Import Validation**:
```bash
python test_bot.py
```

**Unit Tests**:
```bash
pytest tests/
```

**Manual Testing**: See TESTING.md for comprehensive checklist

## Logging

**Configuration**: Unified logging in `app.py`
**Level**: DEBUG (configurable)
**Output**: stdout (visible in console/Docker logs)
**Log Location**: `/home/pknull/Code/pk.shado/logs/`

**Logger Hierarchy**:
- debug - Bot lifecycle events
- utils - HTTP requests
- astrologer - Chart computations
- astrologer.geocoding - Location lookups
- astrologer.core - Calculations
- games - Game commands
- weather - Weather API
- thirstyboi - Hydration tracking
- cipher_oracle - Mystical readings

## Discord Bot Commands

**Prefix**: `!`

**Key Commands**:
- `!astrology` - Generate astrology reading
- `!setbirthday` - Set birth data for natal chart
- `!natalchart` - Display natal chart
- `!chartimage` - Generate natal chart SVG
- `!weather <city>` - Current weather
- `!forecast <city>` - 5-day forecast
- `!dice <notation>` - Roll dice (e.g., `!dice 2d6+3`)
- `!card <deck> <count>` - Deal cards
- `!coin <count>` - Flip coins
- `!killbot` - Graceful shutdown (admin only)

## Data Persistence

**Format**: JSON (not pickle - security improvement)
**Location**: `/home/pknull/Code/pk.shado/data/`

**Auto-save Intervals**:
- Astrologer birth data: Every 5 minutes
- Thirstyboi user data: Every 69 seconds

## Caching Strategy

**Natal Charts**: SHA-256 based deterministic caching (in-memory)
**Transit Calculations**: Time-bucketed caching (in-memory)
**HTTP Sessions**: Global singleton pattern (connection pooling)

## Development Conventions

**Code Style**:
- Minimal comments (prefer self-documenting code)
- Type hints for new functions
- Consistent logging levels (DEBUG/INFO/WARNING/ERROR)

**Cog Structure**:
```python
class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def mycommand(self, ctx):
        # Implementation
        pass

async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

**HTTP Requests**: Always use shared session via `Utils.get_http_session()`

## Git Workflow

**Current Branch**: `claude/code-optimization-review-011CUoLFDCwdDSpontgtvv3m`
**Remote**: origin

**Common Commands**:
```bash
git status
git add <files>
git commit -m "message"
git push origin <branch>
```

## Tools and Integrations

**No MCP integrations currently configured**
**No external agents currently configured**

## Platform

**OS**: Linux 6.8.0-88-generic
**Architecture**: x86_64
**Working Directory**: /home/pknull/Code/pk.shado

## Asha Framework

**Location**: `/home/pknull/Code/pk.shado/asha/` (git submodule)
**CLAUDE.md**: References `@asha/CORE.md`
**Memory Bank**: `/home/pknull/Code/pk.shado/Memory/`

## Future Tooling Considerations

- Redis for distributed caching
- PostgreSQL for user data persistence
- CI/CD pipeline (GitHub Actions)
- Bot sharding for large deployments
- Web dashboard
- Slash command migration
