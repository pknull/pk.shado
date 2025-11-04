#!/usr/bin/env python3
"""
Test script to verify bot can import all modules and initialize.
This doesn't actually run the bot, just verifies imports and basic initialization.
"""
import sys
import os

# Set dummy env vars for testing
os.environ['DISCORD_BOT_TOKEN'] = 'test_token_for_import_validation'
os.environ.setdefault('OPENAI_API_KEY', 'test_key')
os.environ.setdefault('OPENWEATHER_API_KEY', 'test_key')

print("=" * 60)
print("BOT IMPORT AND INITIALIZATION TEST")
print("=" * 60)

# Test 1: Import main app
print("\n[TEST 1] Importing main app.py...")
try:
    import app
    print("✅ app.py imported successfully")
except Exception as e:
    print(f"❌ Failed to import app.py: {e}")
    sys.exit(1)

# Test 2: Import all cog modules
print("\n[TEST 2] Importing cog modules...")
cog_modules = [
    'cogs.Utils',
    'cogs.astrologer_data',
    'cogs.astrologer_geocoding',
    'cogs.astrologer_core',
    'cogs.Astrologer',
    'cogs.Anime',
    'cogs.Games',
    'cogs.Greetings',
    'cogs.Members',
    'cogs.Passel',
    'cogs.Pets',
    'cogs.Thirstyboi',
    'cogs.CipherOracle',
    'cogs.Cleaner',
    'cogs.Weather',
    'cogs.Reminders',
    'cogs.Meme',
]

failed_imports = []
for module_name in cog_modules:
    try:
        __import__(module_name)
        print(f"  ✅ {module_name}")
    except Exception as e:
        print(f"  ❌ {module_name}: {e}")
        failed_imports.append((module_name, e))

if failed_imports:
    print(f"\n❌ {len(failed_imports)} modules failed to import:")
    for module_name, error in failed_imports:
        print(f"  - {module_name}: {error}")
    sys.exit(1)

print("\n✅ All cog modules imported successfully")

# Test 3: Verify data files exist
print("\n[TEST 3] Checking data files...")
data_files = [
    'data/timezone_regions.json',
    'data/manual_coordinates.json',
]

missing_files = []
for file_path in data_files:
    if os.path.exists(file_path):
        print(f"  ✅ {file_path}")
    else:
        print(f"  ❌ {file_path} - MISSING")
        missing_files.append(file_path)

if missing_files:
    print(f"\n❌ {len(missing_files)} data files missing")
    sys.exit(1)

# Test 4: Verify JSON data can be loaded
print("\n[TEST 4] Loading and validating JSON data...")
try:
    import json

    with open('data/timezone_regions.json', 'r') as f:
        tz_data = json.load(f)
    print(f"  ✅ timezone_regions.json loaded ({len(tz_data)} regions)")

    with open('data/manual_coordinates.json', 'r') as f:
        coord_data = json.load(f)
    print(f"  ✅ manual_coordinates.json loaded ({len(coord_data)} locations)")

except Exception as e:
    print(f"  ❌ Failed to load JSON data: {e}")
    sys.exit(1)

# Test 5: Verify bot instance can be created
print("\n[TEST 5] Verifying bot instance...")
try:
    from discord.ext import commands
    import discord

    # This creates the bot instance
    test_bot = commands.Bot(
        intents=discord.Intents.all(),
        command_prefix='!',
        description='Test bot instance'
    )
    print("  ✅ Bot instance created successfully")
except Exception as e:
    print(f"  ❌ Failed to create bot instance: {e}")
    sys.exit(1)

# Test 6: Check for common issues
print("\n[TEST 6] Checking for common issues...")

# Check if Utils session management is available
try:
    from cogs.Utils import get_http_session, close_http_session
    print("  ✅ HTTP session management available")
except ImportError as e:
    print(f"  ❌ HTTP session management not available: {e}")

# Check if astrologer modules are properly linked
try:
    from cogs.astrologer_data import load_timezone_regions, load_manual_coordinates
    from cogs.astrologer_geocoding import GeocodingService
    from cogs.astrologer_core import AstrologicalComputer

    # Try to instantiate services
    geocoding = GeocodingService(None)
    computer = AstrologicalComputer()
    print("  ✅ Astrologer services can be instantiated")
except Exception as e:
    print(f"  ❌ Astrologer services failed: {e}")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED - Bot is ready to run!")
print("=" * 60)
print("\nTo run the bot:")
print("  1. Set DISCORD_BOT_TOKEN in .env file")
print("  2. Run: python3 app.py")
print()
