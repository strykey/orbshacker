# Discord Orb Quest Faker

> **WARNING: EDUCATIONAL PURPOSES ONLY**
> 
> This tool is provided **STRICTLY for educational and research purposes**. It is intended to help users understand how Discord's game detection system works and to study process manipulation techniques.
> 
> **The developers do NOT condone or encourage any misuse of this software. Users are solely responsible for compliance with all applicable laws and terms of service. Use at your own risk.**

A professional tool that automatically creates fake game processes for Discord Orb quests without requiring actual game installations. Because who has time to install 500GB games just for some orbs?

<img width="485" height="426" alt="Capture d&#39;écran 2026-01-16 204625" src="https://github.com/user-attachments/assets/07cbdd26-b248-4bd0-8092-61a54c80d2ed" />
## Features


- **Automatic Game Detection**: Connects to Discord's official API to fetch the latest list of detectable games
- **Smart Search**: Search games by name or abbreviation (PUBG, LoL, CSGO, etc.)
- **Auto-Launch**: Automatically launches fake processes in the background
- **Multi-Game Support**: Run multiple instances to emulate multiple games simultaneously and complete all orb quests at once
- **Backup Database**: Falls back to GitHub archive if Discord API is unavailable
- **Beautiful Interface**: Colored terminal interface with loading animations (because black and white is boring)
- **Manual Mode**: Support for custom executable names
- **Fast & Efficient**: No bloat, just works

## Requirements

- Python 3.7 or higher
- **Windows ONLY** - This tool is designed exclusively for Windows. Linux/macOS are not supported.
- Internet connection (for database fetching)
- **Discord MUST be running**. The game spoofer only works when Discord is active and scanning processes

## Installation

1. Clone this repository:
```bash
git clone https://github.com/strykey/orbshacker.git
cd orbshacker
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Place `exe.exe` in the project root directory (this is the base executable that will be copied and renamed)

## Usage

Run the main script:
```bash
python orbshacker.py
```

### Menu Options

1. **Search Discord Database**: Search for games using Discord's official API
2. **Manual Mode**: Enter a custom executable name manually
3. **Credits & Info**: View project information and credits
4. **Exit**: Quit the application

### How It Works

This tool works as a **game process spoofer**. It tricks Discord into thinking you're running a game by creating fake processes with the exact names Discord expects.

**IMPORTANT: Discord MUST be running for this to work!**

1. The tool connects to Discord's official API (`/api/v9/applications/detectable`) to get the latest game list
2. It finds the exact process name Discord expects for each game
3. Copies `exe.exe` to `Desktop/Win64/` and renames it to match the game's executable name
4. Launches the fake process in the background
5. **Discord detects the running process** (because it scans for process names) and thinks you're playing the game
6. The fake process must stay running for Discord to continue detecting it

**How the spoofing works:**
- Discord scans your running processes to detect games
- It looks for specific executable names (e.g., `TslGame.exe` for PUBG)
- This tool creates a fake process with that exact name
- Discord sees the process name and assumes you're playing the game
- No actual game files are needed, just the process name match

**Multi-Game Emulation:**
- You can emulate multiple games simultaneously from a single window
- After launching a game, press Enter to return to the main menu
- Select another game and repeat as many times as needed
- Each fake process runs independently, so Discord detects all of them
- This allows you to complete **all orb quests at once in just 15 minutes**
- All fake processes will run in parallel and Discord will detect them all
- No need to open multiple windows, just use the menu repeatedly

### Database Sources

- **Primary**: Discord Official API. Live database with all detectable games, always up to date
- **Backup**: GitHub Archive by Cynosphere. Used if Discord API is unavailable

## Project Structure

```
orbshacker/
├── orbshacker.py      # Main application
├── exe.py             # GUI timer application
├── exe.exe            # Base executable (required)
├── requirements.txt   # Python dependencies
├── README.md          # This file
├── LICENSE            # MIT License
├── CONTRIBUTING.md    # Contribution guidelines
└── .gitignore         # Git ignore rules
```

## Technical Details

### Classes

- **`DiscordGamesDB`**: Handles game database loading from Discord API or GitHub backup
- **`GameFaker`**: Manages fake game executable creation and launching
- **`Colors`**: ANSI color codes for terminal output

### Key Functions

- `load_games_list()`: Loads games from Discord API or GitHub backup
- `search_games(query)`: Searches for games by name or alias
- `get_win32_executable(game)`: Extracts primary Windows executable from game data
- `create_fake_game(exe_name)`: Creates fake game executable
- `launch_executable(exe_path)`: Launches executable in background

## WARNING: Legal Notice & Disclaimer

**EDUCATIONAL PURPOSES ONLY - NO COMMERCIAL USE**

This tool is provided **STRICTLY for educational and research purposes**. It is intended to help users understand how Discord's game detection system works and to study process manipulation techniques.

**COMMERCIAL USE IS STRICTLY PROHIBITED. This software may not be used, distributed, or sold for commercial purposes under any circumstances.**

### Important Warnings

- **NO COMMERCIAL USE**: This software is for educational purposes only. Commercial use, distribution, or sale is strictly prohibited.
- **The developers do NOT condone or encourage any misuse of this software**
- **Users are SOLELY responsible for their actions** and must comply with:
  - All applicable local, state, and federal laws
  - Discord's Terms of Service
  - Any other relevant terms of service or agreements
- **Misuse of this tool may violate Discord's Terms of Service**
- **The developers are NOT responsible** for any consequences resulting from the use or misuse of this software
- **Use at your own risk**. No warranties or guarantees are provided

### Important Requirements

- **Discord MUST be running**. The tool won't work if Discord is closed
- The fake process must stay running for Discord to detect it
- Close the fake executable after completing the quest
- Discord needs to be able to scan processes (normal operation)
- This tool is for educational purposes only
- Use responsibly and at your own risk

### Multi-Game Strategy

**Complete all orb quests in 15 minutes:**
1. Launch the tool and select your first game
2. After the process is launched, press Enter to return to the main menu
3. Select another game from the menu
4. Repeat steps 2-3 for as many games as you want (no need to open multiple windows!)
5. All fake processes will run simultaneously in the background
6. Discord will detect all of them and complete all quests at once
7. Wait 15 minutes for all quests to complete
8. Close all fake processes when done

This works because each fake process has a unique name, so Discord treats them as separate games running simultaneously. You can emulate as many games as you want from a single window by simply pressing Enter after each launch to return to the menu.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See the [LICENSE](LICENSE) file for details.

**GPL v3 Key Points:**
- **Attribution Required**: You must credit the original author
- **Share Alike**: Any modified versions must also be GPL v3
- **Source Code**: You must provide source code when distributing
- **NO COMMERCIAL USE**: This software is provided for educational purposes only. Commercial use, distribution, or sale of this software or any derivative works is strictly prohibited.

## Author

**Strykey**

*"Because sometimes you just need those orbs without the commitment of a 100GB download."*



