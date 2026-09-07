<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0a0a,60:0d1f0d,100:1a4a1a&height=200&section=header&text=orbshacker&fontSize=70&fontColor=4ade80&fontAlignY=55&animation=fadeIn" width="100%"/>

<br/>

[![Python](https://img.shields.io/badge/Python-3.7+-3572A5?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20Only-555555?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/DanielPires2000/orbshacker)
[![Discord](https://img.shields.io/badge/Discord-Game%20Spoofer-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com)
[![License](https://img.shields.io/badge/License-GPL%20v3-c0392b?style=for-the-badge&logo=opensourceinitiative&logoColor=white)](./LICENSE)
[![Version](https://img.shields.io/github/v/release/DanielPires2000/orbshacker?style=for-the-badge&logo=semanticrelease&color=4ade80&logoColor=white)](https://github.com/DanielPires2000/orbshacker/releases)

<br/>

*Because who has time to install 500GB of games just for some orbs.*

<br/>

[Get Started](#installation) &nbsp;·&nbsp; [How it works](#how-it-works) &nbsp;·&nbsp; [Steam Mode](#steam-quest-mode) &nbsp;·&nbsp; [Usage](#usage) &nbsp;·&nbsp; [Structure](#project-structure) &nbsp;·&nbsp; [Legal](#legal-notice)

</div>

<br/>

<div align="center">
<img width="340" alt="image" src="https://github.com/user-attachments/assets/1db237b0-2f57-428f-a004-d707f98a416e" style="border-radius: 16px"/>
</div>

## What is this

orbshacker is a Windows tool that creates fake game processes for Discord Orb quests without installing the actual games. It reads Discord's own public API to get the exact process names Discord expects, copies a base executable, renames it, and launches it in the background. Discord scans your process list, sees what it's looking for, and marks the quest as active.

No client modification. No code injection. No suspicious network traffic. Just a process name sitting in your task list, which is all Discord ever checks.

> **Educational purposes only.** This tool is provided to study how Discord's game detection system works and to explore process manipulation techniques. Use at your own risk and in compliance with all applicable terms of service.

<br/>

## 🚨 Steam Quest Mode

Some games use a more advanced detection method. Discord doesn't just check the process name it also verifies that Steam has registered the game as downloading. Standard spoofing doesn't work for those. Steam Quest Mode does.

### How it works

You search for the game by name directly inside the tool. The tool fetches the game's metadata from the SteamCMD public API install directory, executable path, depot info and retrieves your Steam ID automatically from the Windows registry. It generates a fake `appmanifest_<appid>.acf` file in your `steamapps/` folder, the exact file Steam creates when a download is in progress, with realistic values (`StateFlags 1026`, `LastOwner`, `StagedDepots`, etc.). The fake executable goes directly into `steamapps/common/<game>/`. Discord scans the folder, finds the manifest, sees the process running, and validates the quest. Cleans up after itself when you're done.

**Supported:**
`Any game requiring a Steam manifest` &nbsp; `Fully automatic, no manual AppID lookup` &nbsp; `Uses your real Steam ID` &nbsp; `Searches demos and full games separately` &nbsp; `Auto-cleanup on exit`

> **Tip:** If a quest targets a demo, search for `"Toxic Commando Demo"` instead of `"Toxic Commando"`. They have different AppIDs and the wrong one won't trigger the quest.

<br/>

## Features

**Automatic Game Detection** pulls the latest detectable game list from Discord's official API. Smart search lets you find games by name or abbreviation PUBG, LoL, CSGO. Auto-launch handles everything in the background.

**Self-Executing Timer & Embedded Config** builds faked game processes (renamed copies of the spoofer executable) that directly run the countdown timer when double-clicked by the user, with custom durations and auto-delete settings embedded directly inside the binary. No console windows are allocated for the faked processes.

**Automatic Self-Destruction (`AUTO_DELETE`)** cleans up all faked executables, parent folders, and generated Steam manifests in the background once the countdown timer finishes.

**Multi-Game Support** lets you run multiple fake processes simultaneously, completing all orb quests at once. Launch a game, press Enter, pick another, repeat. Each process runs independently and Discord sees all of them.

**Backup Database** falls back to a GitHub archive if Discord's API is unavailable, so the tool keeps working even when the primary source is down.

**Manual Mode** supports custom executable names if you need to spoof something not in the database.

**Beautiful Interface** is a colored terminal UI with loading animations, because plain text is boring.

<br/>

## Why this method works

Discord's game detection reads your Windows process list. It sees `TslGame.exe` and assumes you're playing PUBG. There is no technical mechanism in place to verify whether that process is the actual game or a renamed executable. The name is all it checks.

To detect this method, Discord would need kernel-level anti-cheat software comparable to Valorant's Vanguard deep system access, raised privacy concerns, a broken promise of being a lightweight chat app. That is not happening for cosmetic orb quests.

**What this is not:** This tool does not inject code into Discord's console, modify client files, or send fake API requests. Those methods leave traces. Discord can detect when their JavaScript has been tampered with. Our approach leaves Discord's client completely untouched. The tool uses Discord's own public API to fetch the game list. No client modification. No integrity violations.

<br/>

## Requirements

Windows only. Internet connection for database fetching. Discord must be running the spoofer only works when Discord is active and scanning processes.

## Installation

### Option 1: Download the executable

If you just want to use Orbshacker without setting up Python, you can download the latest executable from the [Releases](https://github.com/DanielPires2000/orbshacker/releases) page.

Download `orbshacker.exe` and run it directly. No Python installation or additional setup is required.

### Option 2: Run from source

Clone the repository, or download and extract the ZIP.

If you've cloned the repository, run `cd orbshacker` to enter the project folder.

If you've downloaded the ZIP, open a terminal in the folder containing `README.md`.

Make sure you have Python 3.7+ installed and available in your PATH.

Then install the required dependencies and run the tool:

```bash
pip install -r requirements.txt
python -m orbshacker
```

<br/>

## Usage

```bash
python orbshacker.py
```

Or via the package entry point:

```bash
python -m orbshacker
```

### Menu options

`1` Search Discord database by name or abbreviation

`2` Manual mode, enter a custom executable name

`3` Steam special quest mode

`4` Credits and project info

`5` Exit

### Completing all quests in 15 minutes

Launch the tool. Select your first game. After the process is launched, press Enter to return to the main menu. Select another game. Repeat as many times as needed no need to open multiple windows. Every fake process runs in parallel. Discord detects all of them simultaneously. Wait 15 minutes. Close everything when done.

<br/>

## How it works

The tool connects to Discord's official API (`/api/v9/applications/detectable`) to get the live game list. It extracts the exact process name Discord expects for each game. It copies the spoofer executable (or base Python interpreter in source mode) to the configured folder (defaults to `Desktop/Win64/`), renames it to match the game's executable name, and bakes the active configuration directly inside it.

When the faked game executable runs, it acts as a standalone countdown timer with its settings embedded. When the countdown completes, it automatically triggers a background self-destruction script (if `AUTO_DELETE` is enabled) to delete the faked files and empty parent directories.

Steam Quest Mode adds a layer: it generates a fake `appmanifest_<appid>.acf` in `steamapps/` and places the executable in `steamapps/common/<game>/`, satisfying Discord's additional manifest check for games like Marathon or Toxic Commando.

<br/>

## Project Structure

```
orbshacker/
├── orbshacker.py          Main entry point
├── orbshacker/
│   ├── __init__.py        Version and author metadata
│   ├── __main__.py        Package entry point, --timer-mode support
│   ├── config.py          Centralized configuration with settings.py overrides
│   ├── faker.py           Fake executable creation and launch logic
│   ├── discord_db.py      Game database loading, search, and selection
│   ├── steam.py           Steam registry helpers and manifest generation
│   ├── updater.py         Auto-update from GitHub releases
│   ├── net.py             HTTP helpers
│   ├── ui.py              Terminal colors, animations, prompts
│   └── errors.py          Custom exception hierarchy
├── tests/                 pytest coverage for pure helpers
├── settings.py            User-editable configuration
├── requirements.txt
└── .github/
    └── workflows/
        └── release.yml    PyInstaller build and GitHub Release automation
```

<br/>

## Configuration

User-editable values live in `settings.py` at the project root. The file is loaded at startup and overrides any default from `orbshacker/config.py`. Runtime preferences and API timeouts go there. The application version comes from the git tag used for the build and is not user-configurable; changing it manually would break update detection.

<br/>

## Auto-updater

When a new version tag is pushed, GitHub Actions builds a standalone Windows executable using PyInstaller and publishes it as a GitHub Release. The tool checks for updates on launch, downloads the new binary, swaps it in place, and restarts automatically. No Python installation needed to run the distributed executable.

<br/>

## Legal Notice

**Educational purposes only. No commercial use.**

This tool is provided strictly for educational and research purposes to study how Discord's game detection system works and to explore process manipulation techniques. Commercial use, distribution, or sale is strictly prohibited.

Users are solely responsible for compliance with all applicable laws, Discord's Terms of Service, and any other relevant agreements. The developers do not condone misuse and are not responsible for any consequences resulting from use of this software. No warranties or guarantees are provided. Use at your own risk.

Misuse of this tool may violate Discord's Terms of Service.

<br/>

## License

GPL v3. Attribution required. Modified versions must also be GPL v3. Source code must be provided with any distribution. Commercial use is strictly prohibited. See [LICENSE](./LICENSE) for full terms.

<br/>

<div align="center">

made with questionable life choices by **Strykey**

<br/>

[![GitHub stars](https://img.shields.io/github/stars/DanielPires2000/orbshacker?style=for-the-badge&color=4ade80&labelColor=1a1a1a)](https://github.com/DanielPires2000/orbshacker/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/DanielPires2000/orbshacker?style=for-the-badge&color=4ade80&labelColor=1a1a1a)](https://github.com/DanielPires2000/orbshacker/network)

<br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:4ade80,40:0d1f0d,100:0a0a0a&height=120&section=footer" width="100%"/>

</div>
