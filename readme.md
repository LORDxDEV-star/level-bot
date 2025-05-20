# Lunar Developments Level Bot 🌙

A powerful Discord leveling system with custom rank cards and MongoDB integration.

## Features ✨

- XP and leveling system with customizable settings
- Beautiful rank cards with user avatars
- MongoDB integration for reliable data storage 
- Per-server configurable settings
- Admin commands for server management

## Setup 🚀

### Prerequisites

- Python 3.8+
- MongoDB Atlas Account
- Discord Bot Token
- Required packages:
```bash
pip install discord.py Pillow motor
```

### Quick Start

1. Clone and install:
```bash
git clone https://github.com/LORDxDEV-star/level-bot
cd level-bot
pip install -r requirements.txt
```

2. Configure `config.json`:
```json
{
    "token": "your-bot-token",
    "mongodb_uri": "your-mongodb-uri",
    "bot_status": "levels",
    "xp_per_message": 10,
    "max_level": 500
}
```

3. Add required assets:
- Create `assets` folder
- Add `background.png` (934x282px) for rank cards
- Add `font.ttf` for text rendering

4. Run the bot:
```bash
python main.py
```

## Commands 🛠️

| Command | Description | Permission |
|---------|-------------|------------|
| `!rank` | View your rank card | Everyone |
| `!setlevelchannel #channel` | Set level-up channel | Admin |

## Support 💜

Need help? Join our Discord server:
[discord.gg/lunardevs](https://discord.gg/lunardevs)

## Credits 🌟

Made with 💜 by [Lunar Developments](https://discord.gg/lunardevs)

## License 📝

MIT License - See [LICENSE](LICENSE) for details