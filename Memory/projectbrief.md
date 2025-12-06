---
version: 1.0.0
lastUpdated: 2025-12-06
lifecycle: stable
stakeholder: pknull
changeTrigger: major-feature-addition
validatedBy: architecture-review
dependencies: []
---

# Project Brief: pk.shado Discord Bot

## Overview

pk.shado is a feature-rich Discord bot providing gaming utilities, astrology features, and community engagement tools. The bot is built in Python using discord.py and follows a modular cog-based architecture.

## Core Purpose

Provide Discord server members with:
- Gaming RNG tools (dice, cards, coin flips)
- Astrology readings and natal chart generation
- Utility commands (weather, reminders, message cleanup)
- Community engagement features (greetings, memes, hydration tracking)

## Technical Foundation

**Language**: Python 3.8+
**Framework**: discord.py with cog-based extension system
**Key Dependencies**:
- discord.py (bot framework)
- kerykeion 4.26.3 (astrology calculations)
- openai (AI-powered readings)
- aiohttp (HTTP session management)
- pillow, cairosvg (image generation)

## Architecture

**Entry Point**: `app.py` - initializes bot, loads cogs, configures logging
**Module System**: `/cogs` directory - self-contained feature modules
**Data Storage**: JSON files in `/data` (user birth data, hydration tracking, geocoding database)
**Configuration**: Environment variables via `.env` file

## Key Features

1. **Astrology System** (Astrologer.py + support modules)
   - Natal chart computation with caching
   - AI-powered readings via OpenAI
   - Birth data persistence
   - Geocoding with fallback to manual database

2. **Gaming Tools** (Games.py)
   - Dice rolling with D&D notation
   - Card dealing from various decks
   - Coin flips and custom list randomization

3. **Utility Commands**
   - Weather forecasts (Weather.py)
   - Reminders and timers (Reminders.py)
   - Message cleanup (Cleaner.py)
   - Hydration tracking (Thirstyboi.py)

4. **Community Features**
   - Greeting messages (Greetings.py)
   - Member management (Members.py)
   - Meme generation (Meme.py)
   - Anime images (Anime.py)

## Recent Optimizations (Phases 1-3)

- HTTP session pooling (30-50% performance improvement)
- Astrologer cog modularization (1426 lines → 800 + 3 support modules)
- Migration from pickle to JSON for security and maintainability
- Unified logging configuration
- Enhanced error handling and graceful shutdown

## Constraints

- Single Discord bot instance (no sharding currently)
- In-memory caching (natal charts, transits)
- JSON file-based persistence (suitable for small-medium servers)
- Requires external API keys: DISCORD_BOT_TOKEN, OPENWEATHER_API_KEY, OPENAI_API_KEY, GEONAMES_USERNAME

## Deployment

- Docker support via Dockerfile
- Build scripts: build.sh, build_local.sh
- Virtual environment via venv
- Environment variable configuration

## Documentation

- ARCHITECTURE.md - comprehensive system architecture
- TESTING.md - testing guide and checklist
- CHANGELOG.md - version history
- README.md - setup instructions

## Success Criteria

- Bot stays online with minimal downtime
- Commands respond within 1-2 seconds
- Data persistence without corruption
- Clean separation of concerns across cogs
- Maintainable codebase with clear logging
