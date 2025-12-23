# pk.shado

A Discord bot providing gaming RNG, character management, astrology, and fun commands.

> This project is partially managed by [Asha](https://github.com/pknull/asha), a Claude Code framework.

## Setup

1. Install Python 3.10 or newer.
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variables:
   - `DISCORD_BOT_TOKEN` (required) - Your Discord bot token
   - `OPENWEATHER_API_KEY` (optional) - For weather commands
   - `OPENAI_API_KEY` (optional) - For AI-powered readings
   - `GEONAMES_USERNAME` (optional) - For location geocoding
4. Run the bot:
   ```bash
   python app.py
   ```

The provided `Dockerfile` can also be used to build an image with the token
passed at build time using the `TOKEN` build argument.

## Commands

All commands use the `!` prefix.

### AAS (Character Management - Call of Cthulhu 7e)

| Command | Description |
|---------|-------------|
| `!aas create <name> [occupation]` | Create a new character |
| `!aas sheet [@user]` | View character sheet |
| `!aas stats <STR> <CON> <DEX> <SIZ> <POW> <APP> <INT> <EDU>` | Set characteristics |
| `!aas set <target> <value>` | Set a characteristic or resource |
| `!aas skill <name> <value>` | Set a skill value |
| `!aas skills [@user]` | List all skills |
| `!aas import` | Import from Dhole's House JSON (attach file) |
| `!aas export` | Export character to JSON |
| `!aas delete [confirm]` | Delete your character |
| `!aas check <skill>` | Mark skill for advancement check |
| `!aas advance` | Roll advancement for checked skills |
| `!aas spend <skill> [amount]` | Spend XP on a skill |
| `!aas wound [on/off]` | Toggle major wound status |
| `!aas save [note]` | Save a snapshot of your character |
| `!aas history [count]` | View character history |
| `!aas help [command]` | Show help for AAS commands |

**Quick Roll Commands:**
| Command | Description |
|---------|-------------|
| `!skill <name> [difficulty] [modifier]` | Roll a skill check |
| `!char <name> [difficulty] [modifier]` | Roll a characteristic check |
| `!hp [+/-amount]` | View or modify HP |
| `!mp [+/-amount]` | View or modify MP |
| `!san [+/-amount]` | View or modify Sanity |
| `!luck [+/-amount]` | View or modify Luck |

- **Difficulty**: `regular`, `hard`, or `extreme`
- **Modifier**: `+1`, `+2` (bonus dice) or `-1`, `-2` (penalty dice)

### Astrology

| Command | Description |
|---------|-------------|
| `!astrology [daily/weekly/love/career] [sign]` | Get an astrological reading |
| `!setbirthday <date time location>` | Set your birth info for charts |
| `!mybirthday` | View your stored birth info |
| `!removebirthday` | Remove your birth data |
| `!settimezone <tz_string>` | Set your timezone |
| `!listtimezones` | List common timezone strings |
| `!natalchart` | Get your detailed natal chart |
| `!chartimage` | Generate a visual SVG chart |
| `!zodiac` | Show astrology command info |

### Games & RNG

| Command | Description |
|---------|-------------|
| `!dice <notation>` | Roll dice (e.g., `2d6+3`, `4d6kh3`) |
| `!card <deck> [count]` | Draw cards (e.g., `standard 5`, `tarot`) |
| `!coin [count]` | Flip coins |
| `!eightball` | Ask the magic 8-ball |
| `!toss <items> [count] [unique]` | Pick from comma-separated list |

### Weather

| Command | Description |
|---------|-------------|
| `!weather <city>` | Get current weather |
| `!forecast <city>` | Get 5-day forecast |

Requires `OPENWEATHER_API_KEY` environment variable.

### Hydration (Thirstyboi)

| Command | Description |
|---------|-------------|
| `!sip [time]` | Log a drink |
| `!total` | View drink count |
| `!stop` | Stop reminders |
| `!dmme` | Get reminders via DM |
| `!allow_c` | Allow bot in this channel (admin) |

### Utility

| Command | Description |
|---------|-------------|
| `!clean [limit] [bulk]` | Delete messages (admin) |
| `!remind <time> <message>` | Set a reminder |
| `!timer <time>` | Start a countdown timer |
| `!sr [count]` | Pick random server member(s) |
| `!vr <count>` | Pick random voice channel member(s) |
| `!pins` | Show pinned message count |

### Fun

| Command | Description |
|---------|-------------|
| `!cipher` | Get a mystical AI-powered reading |
| `!meme <query>` | Search for a meme |
| `!dog` | Random dog image |
| `!headpat` | Headpat GIF |
| `!hello [@user]` | Friendly greeting |

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for technical documentation.

## Testing

```bash
pytest tests/
```

See [TESTING.md](TESTING.md) for the testing guide.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for
details.

