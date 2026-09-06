"""
discord_db.py – DiscordGamesDB class and database search mode.
"""

import time
from typing import TypedDict

from . import config
from .errors import DatabaseLoadError, NetworkError
from .faker import GameFaker
from .net import fetch_json
from .path_utils import sanitize_relative_path
from .ui import (
    Colors,
    ask_confirm,
    loading_animation,
    print_boxed_title,
    print_color,
)


class ExecutableEntry(TypedDict, total=False):
    os: str
    name: str


class GameRecord(TypedDict, total=False):
    id: str
    name: str
    aliases: list[str]
    executables: list[ExecutableEntry]


class DiscordGamesDB:
    """Loads and searches the Discord-detectable games database."""

    def __init__(self):
        self.games: list[GameRecord] = []
        self.source: str | None = None
        self._load()

    def _load(self):
        """Load games from Discord API or GitHub backup."""
        print_color("\n[*] Loading games database...", Colors.YELLOW)
        if self._load_from_discord_api():
            return
        print_color(
            "[!] Discord API unavailable, using GitHub backup...", Colors.YELLOW
        )
        if self._load_from_github():
            return
        raise DatabaseLoadError("Could not load games database from any source.")

    def _load_from_discord_api(self) -> bool:
        try:
            loading_animation("Connecting to Discord API", 1.0)
            self.games = fetch_json(
                config.DISCORD_API_URL, headers=config.DISCORD_HEADERS
            )
            self.source = "Discord Official API"
            print_color(
                f"[OK] Loaded {len(self.games)} games from Discord API",
                Colors.GREEN,
                bold=True,
            )
            print_color(
                "[*] Using LIVE database (fresh from Discord's servers)", Colors.CYAN
            )
            return True
        except NetworkError as e:
            print_color(f"[!] Discord API error: {e}", Colors.YELLOW)
            return False

    def _load_from_github(self) -> bool:
        try:
            loading_animation("Fetching GitHub backup", 1.0)
            self.games = fetch_json(
                config.GITHUB_BACKUP_URL, timeout=config.REQUEST_TIMEOUT_LONG
            )
            self.source = "GitHub Backup"
            print_color(
                f"[OK] Loaded {len(self.games)} games from GitHub",
                Colors.GREEN,
                bold=True,
            )
            return True
        except NetworkError as e:
            print_color(f"[ERROR] GitHub backup failed: {e}", Colors.RED)
            return False

    def search_games(self, query: str) -> list[GameRecord]:
        """Search for games by name or alias, returning up to MAX_SEARCH_RESULTS matches."""
        query_lower = query.lower()
        exact: dict[str, GameRecord] = {}
        partial: dict[str, GameRecord] = {}
        for game in self.games:
            game_id = game.get("id", "")
            name = game.get("name", "").lower()
            aliases = [a.lower() for a in game.get("aliases", [])]
            if query_lower == name or query_lower in aliases:
                if game_id:
                    exact.setdefault(game_id, game)
            elif query_lower in name or any(query_lower in a for a in aliases):  # noqa: SIM102
                if game_id:
                    partial.setdefault(game_id, game)
        merged = list(exact.values()) + [
            g for g in partial.values() if g.get("id") not in exact
        ]
        return merged[: config.MAX_SEARCH_RESULTS]

    # ── executable helpers ────────────────────────────────────────────────────
    _SKIP_EXE_PATTERNS = [  # noqa: RUF012
        "_be.exe",
        "_eac.exe",
        "launcher",
        "unins",
        "crash",
        "report",
        "update",
        "setup",
        "install",
    ]

    def _filter_win32_exes(
        self, game: GameRecord, skip_patterns: bool = True
    ) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for exe in game.get("executables", []):
            if exe.get("os") != "win32":
                continue
            name = exe.get("name", "")
            name = name.removeprefix(">")
            name = sanitize_relative_path(name)
            if not name or name in seen:
                continue
            if skip_patterns and any(
                p in name.lower() for p in self._SKIP_EXE_PATTERNS
            ):
                continue
            seen.add(name)
            result.append(name)
        return result

    def get_win32_executable(self, game: GameRecord) -> str | None:
        candidates = self._filter_win32_exes(game, skip_patterns=True)
        return candidates[0] if candidates else None

    def get_all_executables(self, game: GameRecord) -> list[str]:
        return self._filter_win32_exes(game, skip_patterns=False)


# ── Interactive UI ────────────────────────────────────────────────────────────


def _pick_discord_game(db: DiscordGamesDB, query: str) -> GameRecord | None:
    """Search the Discord DB and let the user choose a game."""
    loading_animation(f"Searching for '{query}'", 0.8)
    matches = db.search_games(query)
    if not matches:
        print_color(f"\n[ERROR] No games found for '{query}'", Colors.RED)
        print_color("[!] Try a different search term or abbreviation", Colors.YELLOW)
        time.sleep(config.SLEEP_LONG)
        return None

    print(f"\n{Colors.BOLD}{Colors.GREEN}Found {len(matches)} game(s):{Colors.RESET}\n")
    print(f"{Colors.GRAY}{'─' * 75}{Colors.RESET}")
    for idx, game in enumerate(matches, 1):
        name = game.get("name", "Unknown")
        game_id = game.get("id", "N/A")
        aliases = game.get("aliases", [])
        print(
            f"{Colors.BOLD}{Colors.CYAN}{idx:2d}.{Colors.RESET} {Colors.WHITE}{name}{Colors.RESET}"
        )
        if aliases:
            alias_str = ", ".join(aliases[:3])
            if len(aliases) > 3:
                alias_str += f" (+{len(aliases) - 3} more)"
            print(f"    {Colors.GRAY}Aliases: {alias_str}{Colors.RESET}")
        print(f"    {Colors.GRAY}ID: {game_id}{Colors.RESET}")
        if idx < len(matches):
            print(f"{Colors.GRAY}{'─' * 75}{Colors.RESET}")
    print()

    raw = input(
        f"{Colors.BOLD}Select [1-{len(matches)}]{Colors.RESET} (or 'back'): "
    ).strip()
    if raw.lower() in ("back", "b", ""):
        return None
    try:
        idx = int(raw)
        if not 1 <= idx <= len(matches):
            raise ValueError
    except ValueError:
        print_color("\n[ERROR] Enter a valid number", Colors.RED)
        time.sleep(config.SLEEP_SHORT)
        return None
    return matches[idx - 1]


def _resolve_discord_exe(db: DiscordGamesDB, game: GameRecord) -> str | None:
    """Return the primary exe, prompting the user if none found."""
    exe_name = db.get_win32_executable(game)
    if exe_name:
        return exe_name
    print_color("\n[ERROR] No Windows executable found for this game", Colors.RED)
    print_color(
        "[!] This game might not have a Windows version or executable data",
        Colors.YELLOW,
    )
    if ask_confirm("Enter executable name manually?"):
        exe_name = input(f"{Colors.BOLD}Executable name:{Colors.RESET} ").strip()
        if not exe_name:
            print_color("\n[!] Operation cancelled", Colors.YELLOW)
            time.sleep(config.SLEEP_SHORT)
            return None
        return sanitize_relative_path(exe_name)
    return None


def database_mode(db: DiscordGamesDB, faker: GameFaker) -> None:
    """Database search mode."""
    print_boxed_title("DATABASE SEARCH", width=50, color=Colors.CYAN)
    print_color(f"[*] Database: {db.source}", Colors.CYAN)
    print_color(f"[*] Total games available: {len(db.games)}", Colors.GRAY)
    print_color("\n[*] Search by name or abbreviation", Colors.CYAN)
    print_color(
        "[*] Examples: PUBG, Fortnite, League, Valorant, Minecraft", Colors.GRAY
    )
    print()

    query = input(f"{Colors.BOLD}Search{Colors.RESET} (or 'back'): ").strip()
    if query.lower() in ("back", "b", ""):
        return

    selected = _pick_discord_game(db, query)
    if not selected:
        return

    loading_animation("Analysing game data", 0.8)
    exe_name = _resolve_discord_exe(db, selected)
    if not exe_name:
        return

    all_exes = db.get_all_executables(selected)

    print(f"\n{Colors.BOLD}Game Information:{Colors.RESET}")
    print(f"  Name:               {Colors.CYAN}{selected.get('name')}{Colors.RESET}")
    print(f"  ID:                 {Colors.GRAY}{selected.get('id')}{Colors.RESET}")
    print(f"  Primary Executable: {Colors.GREEN}{exe_name}{Colors.RESET}")
    if len(all_exes) > 1:
        print(
            f"  {Colors.GRAY}Other executables: {', '.join(all_exes[1:3])}{Colors.RESET}"
        )
        if len(all_exes) > 3:
            print(
                f"  {Colors.GRAY}(+{len(all_exes) - 3} more executables available){Colors.RESET}"
            )
    print(
        f"  Path: {Colors.GRAY}{faker.chosen_path / config.FAKE_EXE_DIR / exe_name}{Colors.RESET}"
    )

    if not ask_confirm():
        print_color("\n[!] Operation cancelled", Colors.YELLOW)
        time.sleep(config.SLEEP_SHORT)
        return

    result = faker.create_fake_game(exe_name)
    if result:
        print()
        faker.launch_executable(result, selected.get("name"))
        print_color(
            "\n[OK] Setup complete! Discord should detect the game.",
            Colors.GREEN,
            bold=True,
        )
        print_color(
            "[!] IMPORTANT: Discord MUST be running for the spoofing to work",
            Colors.YELLOW,
        )
        print_color("[*] Keep the process running until quest is complete", Colors.CYAN)
        print_color(
            "[*] TIP: Run this tool again to emulate another game simultaneously!",
            Colors.MAGENTA,
        )

    input(f"\n{Colors.GRAY}Press Enter to continue...{Colors.RESET}")
