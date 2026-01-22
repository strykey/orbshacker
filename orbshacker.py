#!/usr/bin/env python3
"""
Discord Orb Quest Faker

EDUCATIONAL PURPOSES ONLY - This tool is provided for educational and research
purposes only. The developers do not condone or encourage any misuse of this
software. Users are solely responsible for their actions and must comply with
all applicable laws and terms of service.

Automatically creates fake game processes for Discord Orb quests.
Developed by Strykey
"""

import os
import sys
import shutil
import requests
import subprocess
import time
from pathlib import Path


class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'


def print_color(text, color=Colors.WHITE, bold=False):
    """Print colored text"""
    style = Colors.BOLD if bold else ''
    print(f"{style}{color}{text}{Colors.RESET}")


def print_boxed_title(title, width=50, color=Colors.CYAN):
    """Print a boxed title with ASCII borders"""
    border = f"{Colors.BOLD}{color}{'+' + '-' * (width - 2) + '+'}{Colors.RESET}"
    title_padding = (width - len(title) - 4) // 2
    extra_space = (width - len(title) - 4) % 2
    title_line = f"{Colors.BOLD}{color}|{Colors.RESET}{' ' * title_padding}{Colors.BOLD}{title}{Colors.RESET}{' ' * (title_padding + extra_space)}{Colors.BOLD}{color}|{Colors.RESET}"
    print(f"\n{border}")
    print(title_line)
    print(f"{border}\n")


def print_banner():
    """Display ASCII banner"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
                                                                
 _____ _____ _____ _____    _____ _____ _____ _____ _____ _____ 
|     | __  | __  |   __|  |  |  |  _  |     |  |  |   __| __  |
|  |  |    -| __ -|__   |  |     |     |   --|    -|   __|    -|
|_____|__|__|_____|_____|  |__|__|__|__|_____|__|__|_____|__|__|
                                                                
{Colors.RESET}
    {Colors.GRAY}Developer: {Colors.CYAN}Strykey{Colors.RESET}
    {Colors.GRAY}Version: {Colors.WHITE}2.0.0{Colors.RESET}
    {Colors.GRAY}Database: {Colors.GREEN}Discord Official API + GitHub Archive{Colors.RESET}
"""
    print(banner)


def loading_animation(text, duration=1.5):
    """Display loading animation"""
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    i = 0
    
    while time.time() < end_time:
        sys.stdout.write(f"\r{Colors.CYAN}{frames[i % len(frames)]}{Colors.RESET} {text}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    
    sys.stdout.write("\r" + " " * (len(text) + 5) + "\r")
    sys.stdout.flush()


class DiscordGamesDB:
    DISCORD_API_URL = "https://discord.com/api/v9/applications/detectable"
    GITHUB_BACKUP_URL = "https://gist.githubusercontent.com/Cynosphere/c1e77f77f0e565ddaac2822977961e76/raw/gameslist.json"
    
    def __init__(self):
        self.games = []
        self.source = None
        self.load_games_list()
    
    def load_games_list(self):
        """Load games from Discord API or GitHub backup"""
        print_color("\n[*] Loading games database...", Colors.YELLOW)
        
        # Try Discord Official API first
        if self._load_from_discord_api():
            return
        
        # Fallback to GitHub
        print_color("[!] Discord API unavailable, using GitHub backup...", Colors.YELLOW)
        if self._load_from_github():
            return
        
        print_color("[ERROR] Failed to load any database!", Colors.RED, bold=True)
        sys.exit(1)
    
    def _load_from_discord_api(self):
        """Load from Discord's official API"""
        try:
            loading_animation("Connecting to Discord API", 1.0)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://discord.com/',
                'Origin': 'https://discord.com'
            }
            
            response = requests.get(self.DISCORD_API_URL, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.games = response.json()
                self.source = "Discord Official API"
                print_color(f"[OK] Loaded {len(self.games)} games from Discord API", Colors.GREEN, bold=True)
                print_color(f"[*] Using LIVE database (fresh from Discord's servers)", Colors.CYAN)
                return True
            else:
                return False
                
        except Exception as e:
            print_color(f"[!] Discord API error: {e}", Colors.YELLOW)
            return False
    
    def _load_from_github(self):
        """Load from GitHub backup"""
        try:
            loading_animation("Fetching GitHub backup", 1.0)
            
            response = requests.get(self.GITHUB_BACKUP_URL, timeout=15)
            response.raise_for_status()
            self.games = response.json()
            self.source = "GitHub Backup"
            print_color(f"[OK] Loaded {len(self.games)} games from GitHub", Colors.GREEN, bold=True)
            return True
            
        except Exception as e:
            print_color(f"[ERROR] GitHub backup failed: {e}", Colors.RED)
            return False
    
    def search_games(self, query):
        """Search for games by name or alias"""
        query_lower = query.lower()
        matches = []
        
        for game in self.games:
            name = game.get('name', '').lower()
            aliases = [a.lower() for a in game.get('aliases', [])]
            
            # Exact match priority
            if query_lower == name or query_lower in aliases:
                matches.insert(0, game)
            # Partial match
            elif query_lower in name or any(query_lower in alias for alias in aliases):
                matches.append(game)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_matches = []
        for game in matches:
            game_id = game.get('id')
            if game_id not in seen:
                seen.add(game_id)
                unique_matches.append(game)
        
        return unique_matches[:20]
    
    def get_win32_executable(self, game):
        """Extract primary Windows executable from game data (with full path)"""
        executables = game.get('executables', [])
        candidates = []
        
        for exe in executables:
            if exe.get('os') != 'win32':
                continue
            
            name = exe.get('name', '')
            
            if name.startswith('>'):
                name = name[1:]
            
            # Keep the full path, just clean up the separators
            name = name.replace('\\', '/')
            name_lower = name.lower()
            skip_patterns = ['_be.exe', '_eac.exe', 'launcher', 'unins', 'crash', 'report', 'update', 'setup', 'install']
            
            if any(skip in name_lower for skip in skip_patterns):
                continue
            
            candidates.append(name)
        
        return candidates[0] if candidates else None
    
    def get_all_executables(self, game):
        """Get all Windows executables for a game (with full paths)"""
        executables = game.get('executables', [])
        all_exes = []
        
        for exe in executables:
            if exe.get('os') != 'win32':
                continue
            
            name = exe.get('name', '')
            
            if name.startswith('>'):
                name = name[1:]
            
            # Keep the full path, just clean up the separators
            name = name.replace('\\', '/')
            
            if name and name not in all_exes:
                all_exes.append(name)
        
        return all_exes


class GameFaker:
    def __init__(self, exe_source="exe.exe"):
        self.exe_source = Path(exe_source)
        self.desktop_path = Path.home() / "Desktop"
        
        if not self.exe_source.exists():
            print_color(f"\n[ERROR] Source executable not found: {self.exe_source}", Colors.RED, bold=True)
            print_color(f"[!] Please place 'exe.exe' in: {Path.cwd()}", Colors.YELLOW)
            print_color("[*] We can't fake games without the base executable, you know", Colors.GRAY)
            sys.exit(1)
    
    def create_fake_game(self, exe_name):
        """Create fake game executable with full directory structure"""
        if not exe_name.lower().endswith('.exe'):
            exe_name += '.exe'
        
        # Parse the full path and create all directories
        # Convert backslashes to forward slashes for consistency
        exe_name = exe_name.replace('\\', '/')
        
        # Create the full path: Desktop/Win64/{full_game_path}
        target_path = self.desktop_path / "Win64" / exe_name
        target_dir = target_path.parent
        
        # Create all parent directories
        target_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Extract just the filename for display
            filename = exe_name.split('/')[-1]
            loading_animation(f"Creating {filename}", 0.8)
            shutil.copy2(self.exe_source, target_path)
            print_color(f"[OK] Created: {target_path}", Colors.GREEN, bold=True)
            return target_path
        except Exception as e:
            print_color(f"[ERROR] Failed to create executable: {e}", Colors.RED, bold=True)
            print_color("[!] Check file permissions or disk space", Colors.YELLOW)
            return None
    
    def launch_executable(self, exe_path):
        """Launch executable in background - Educational purposes only"""
        try:
            loading_animation("Launching process", 0.8)
            
            if sys.platform == 'win32':
                DETACHED_PROCESS = 0x00000008
                subprocess.Popen(
                    [str(exe_path)],
                    creationflags=DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )
            else:
                subprocess.Popen(
                    [str(exe_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            print_color("[OK] Process launched in background", Colors.GREEN, bold=True)
            print_color("[*] Discord should now detect the game (if Discord is running)", Colors.CYAN)
            print_color("[!] IMPORTANT: Discord MUST be running for the spoofing to work", Colors.YELLOW)
            print_color("[*] Wait a few seconds for Discord to scan processes", Colors.GRAY)
            print_color("[*] If it doesn't work, make sure Discord is actually open", Colors.GRAY)
            print_color(f"[*] TIP: You can run this tool multiple times to emulate multiple games!", Colors.MAGENTA)
            return True
        except Exception as e:
            print_color(f"[!] Failed to auto-launch: {e}", Colors.YELLOW)
            print_color(f"[*] You can manually run: {exe_path}", Colors.CYAN)
            print_color("[*] Or try running it as administrator", Colors.GRAY)
            return False


def print_menu():
    """Display main menu"""
    print_boxed_title("MAIN MENU", width=50, color=Colors.CYAN)
    
    print(f"  {Colors.BOLD}{Colors.GREEN}1.{Colors.RESET} Search Discord database (Official API)")
    print(f"  {Colors.BOLD}{Colors.GREEN}2.{Colors.RESET} Manual mode (custom executable)")
    print(f"  {Colors.BOLD}{Colors.GREEN}3.{Colors.RESET} Credits & Info")
    print(f"  {Colors.BOLD}{Colors.RED}4.{Colors.RESET} Exit\n")


def show_credits():
    """Display credits"""
    print_boxed_title("CREDITS", width=65, color=Colors.CYAN)
    credits = f"""
    {Colors.BOLD}Developer:{Colors.RESET} {Colors.CYAN}Strykey{Colors.RESET}
    {Colors.BOLD}Version:{Colors.RESET} {Colors.WHITE}2.0.0{Colors.RESET}
    
    {Colors.BOLD}Description:{Colors.RESET}
    This tool works as a game process spoofer. It tricks Discord into
    thinking you're running a game by creating fake processes with the
    exact names Discord expects.
    
    {Colors.BOLD}IMPORTANT:{Colors.RESET} {Colors.RED}Discord MUST be running for this to work!{Colors.RESET}
    
    {Colors.BOLD}How it works (Game Spoofing):{Colors.RESET}
    1. Connects to Discord's official API to get the latest game list
    2. Finds the exact process name Discord expects for each game
    3. Copies exe.exe to Desktop/Win64/ and renames it to match
    4. Launches the fake process in background
    5. Discord scans running processes and detects the fake process name
    6. Discord thinks you're playing the game (process name match)
    7. The fake process must stay running for Discord to keep detecting it
    
    {Colors.BOLD}How the spoofing works:{Colors.RESET}
    • Discord scans your running processes to detect games
    • It looks for specific executable names (e.g., TslGame.exe for PUBG)
    • This tool creates a fake process with that exact name
    • Discord sees the process and assumes you're playing the game
    • No actual game files needed - just the process name match
    
    {Colors.BOLD}Database Sources:{Colors.RESET}
    • Primary: Discord Official API (https://discord.com/api/v9/applications/detectable)
      → LIVE database with ALL detectable games
      → Always up-to-date with new games
    
    • Backup: GitHub Archive by Cynosphere
      → Used if Discord API is unavailable
      → Verified games list (snapshot)
    
    {Colors.BOLD}Features:{Colors.RESET}
    • Automatic detection of game executables
    • Manual mode for custom process names
    • Auto-launch in background
    • Beautiful colored interface (because black and white is boring)
    • Real-time loading animations (they're not just for show)
    • Works with Discord's official API (we're not making this up)
    
    {Colors.BOLD}Pro Tips:{Colors.RESET}
    • Search by game abbreviations (PUBG, LoL, CSGO, etc.)
    • Discord MUST be running - the tool won't work otherwise
    • The fake process must stay running for Discord to detect it
    • Close the fake exe after completing the quest
    • If Discord doesn't detect it, make sure Discord is actually running
    • You may need to wait a few seconds for Discord to scan processes
    • The spoofing works by matching process names, nothing more
    
    {Colors.BOLD}{Colors.GREEN}Multi-Game Emulation (Advanced):{Colors.RESET}
    • You can run this tool MULTIPLE TIMES to emulate multiple games at once!
    • Each fake process runs independently - Discord detects them all
    • Complete ALL orb quests simultaneously in just 15 minutes
    • Simply launch the tool again and select a different game
    • All processes will run in parallel - it's surprisingly effective
    
    {Colors.BOLD}{Colors.RED}WARNING - LEGAL NOTICE & DISCLAIMER{Colors.RESET}
    
    {Colors.RED}{Colors.BOLD}EDUCATIONAL PURPOSES ONLY{Colors.RESET}
    
    This tool is provided STRICTLY for educational and research purposes.
    It is intended to help users understand how Discord's game detection
    system works and to study process manipulation techniques.
    
    {Colors.YELLOW}IMPORTANT WARNINGS:{Colors.RESET}
    • The developers do NOT condone or encourage any misuse of this software
    • Users are SOLELY responsible for their actions and must comply with:
      - All applicable local, state, and federal laws
      - Discord's Terms of Service
      - Any other relevant terms of service or agreements
    • Misuse of this tool may violate Discord's Terms of Service
    • The developers are NOT responsible for any consequences resulting
      from the use or misuse of this software
    • Use at your own risk - no warranties or guarantees are provided
    
    {Colors.GRAY}Made by Strykey{Colors.RESET}
    {Colors.GRAY}Press Enter to return to menu...{Colors.RESET}
"""
    print(credits)
    input()


def manual_mode(faker):
    """Manual mode for custom executable names"""
    print_boxed_title("MANUAL MODE", width=50, color=Colors.CYAN)
    
    print_color("[*] Enter the exact process name Discord expects", Colors.CYAN)
    print_color("[*] Examples:", Colors.GRAY)
    print_color("    • TslGame.exe (PUBG)", Colors.GRAY)
    print_color("    • League of Legends.exe (LoL)", Colors.GRAY)
    print_color("    • Overwatch.exe", Colors.GRAY)
    print_color("[*] Make sure the name matches exactly (case-sensitive on some systems)", Colors.GRAY)
    print()
    
    exe_name = input(f"{Colors.BOLD}Executable name{Colors.RESET} (or 'back'): ").strip()
    
    if exe_name.lower() in ['back', 'b', '']:
        return
    
    if not exe_name:
        print_color("\n[ERROR] Invalid executable name", Colors.RED)
        print_color("[!] You need to enter something, you know", Colors.YELLOW)
        time.sleep(1.5)
        return
    
    print(f"\n{Colors.BOLD}Summary:{Colors.RESET}")
    print(f"  Executable: {Colors.CYAN}{exe_name}{Colors.RESET}")
    print(f"  Path: {Colors.GRAY}{faker.desktop_path / 'Win64' / exe_name}{Colors.RESET}")

    confirm = input(f"\n{Colors.BOLD}Create and launch?{Colors.RESET} [Y/n]: ").strip().lower()

    if confirm not in ['', 'y', 'yes']:
        print_color("\n[!] Operation cancelled", Colors.YELLOW)
        print_color("[*] No fake games were created (this time)", Colors.GRAY)
        time.sleep(1.5)
        return

    result = faker.create_fake_game(exe_name)
    
    if result:
        print()
        faker.launch_executable(result)
        print_color("\n[OK] Setup complete!", Colors.GREEN, bold=True)
        print_color("[!] IMPORTANT: Discord MUST be running for the spoofing to work", Colors.YELLOW)
        print_color("[*] Process is running in the background", Colors.GRAY)
        print_color("[*] Discord should detect it by scanning process names", Colors.GRAY)
    
    input(f"\n{Colors.GRAY}Press Enter to continue...{Colors.RESET}")


def database_mode(db, faker):
    """Database search mode"""
    print_boxed_title("DATABASE SEARCH", width=50, color=Colors.CYAN)
    
    print_color(f"[*] Database: {db.source}", Colors.CYAN)
    print_color(f"[*] Total games available: {len(db.games)}", Colors.GRAY)
    print_color("\n[*] Search by name or abbreviation", Colors.CYAN)
    print_color("[*] Examples: PUBG, Fortnite, League, Valorant, Minecraft", Colors.GRAY)
    print()
    
    query = input(f"{Colors.BOLD}Search{Colors.RESET} (or 'back'): ").strip()
    
    if query.lower() in ['back', 'b', '']:
        return
    
    loading_animation(f"Searching for '{query}'", 0.8)
    matches = db.search_games(query)

    if not matches:
        print_color(f"\n[ERROR] No games found for '{query}'", Colors.RED)
        print_color("[!] Try a different search term or abbreviation", Colors.YELLOW)
        print_color("[*] Pro tip: Try searching 'Minecraft' instead of 'minecraft.exe'", Colors.GRAY)
        time.sleep(2)
        return
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}Found {len(matches)} game(s):{Colors.RESET}\n")
    print(f"{Colors.GRAY}{'─' * 75}{Colors.RESET}")
    
    for idx, game in enumerate(matches, 1):
        name = game.get('name', 'Unknown')
        game_id = game.get('id', 'N/A')
        aliases = game.get('aliases', [])
        
        print(f"{Colors.BOLD}{Colors.CYAN}{idx:2d}.{Colors.RESET} {Colors.WHITE}{name}{Colors.RESET}")
        if aliases:
            alias_str = ', '.join(aliases[:3])
            if len(aliases) > 3:
                alias_str += f" (+{len(aliases)-3} more)"
            print(f"    {Colors.GRAY}Aliases: {alias_str}{Colors.RESET}")
        print(f"    {Colors.GRAY}ID: {game_id}{Colors.RESET}")
        
        if idx < len(matches):
            print(f"{Colors.GRAY}{'─' * 75}{Colors.RESET}")
    
    print()
    choice = input(f"{Colors.BOLD}Select [1-{len(matches)}]{Colors.RESET} (or 'back'): ").strip()
    
    if choice.lower() in ['back', 'b', '']:
        return
    
    try:
        choice = int(choice)
        if choice < 1 or choice > len(matches):
            print_color("\n[ERROR] Invalid selection", Colors.RED)
            time.sleep(1)
            return
    except ValueError:
        print_color("\n[ERROR] Enter a number", Colors.RED)
        time.sleep(1)
        return
    
    selected = matches[choice - 1]
    
    loading_animation("Analyzing game data", 0.8)
    exe_name = db.get_win32_executable(selected)
    all_exes = db.get_all_executables(selected)

    if not exe_name:
        print_color("\n[ERROR] No Windows executable found for this game", Colors.RED)
        print_color("[!] This game might not have a Windows version or executable data", Colors.YELLOW)
        manual = input(f"{Colors.YELLOW}Enter executable name manually?{Colors.RESET} [Y/n]: ").strip().lower()
        
        if manual in ['', 'y', 'yes']:
            exe_name = input(f"{Colors.BOLD}Executable name:{Colors.RESET} ").strip()
            if not exe_name:
                print_color("\n[!] Operation cancelled", Colors.YELLOW)
                time.sleep(1.5)
                return
        else:
            return
    
    print(f"\n{Colors.BOLD}Game Information:{Colors.RESET}")
    print(f"  Name: {Colors.CYAN}{selected.get('name')}{Colors.RESET}")
    print(f"  ID: {Colors.GRAY}{selected.get('id')}{Colors.RESET}")
    print(f"  Primary Executable: {Colors.GREEN}{exe_name}{Colors.RESET}")

    if len(all_exes) > 1:
        print(f"  {Colors.GRAY}Other executables: {', '.join(all_exes[1:3])}{Colors.RESET}")
        if len(all_exes) > 3:
            print(f"  {Colors.GRAY}(+{len(all_exes)-3} more executables available){Colors.RESET}")

    print(f"  Path: {Colors.GRAY}{faker.desktop_path / 'Win64' / exe_name}{Colors.RESET}")

    confirm = input(f"\n{Colors.BOLD}Create and launch?{Colors.RESET} [Y/n]: ").strip().lower()

    if confirm not in ['', 'y', 'yes']:
        print_color("\n[!] Operation cancelled", Colors.YELLOW)
        print_color("[*] Returning to main menu...", Colors.GRAY)
        time.sleep(1.5)
        return
    
    result = faker.create_fake_game(exe_name)
    
    if result:
        print()
        faker.launch_executable(result)
        print_color("\n[OK] Setup complete! Discord should detect the game.", Colors.GREEN, bold=True)
        print_color(f"[!] IMPORTANT: Discord MUST be running for the spoofing to work", Colors.YELLOW)
        print_color(f"[*] Keep the process running until quest is complete", Colors.CYAN)
        print_color("[*] Don't close this window or the process will stop", Colors.GRAY)
        print_color("[*] The game spoofer works by matching process names", Colors.GRAY)
        print_color(f"[*] TIP: Run this tool again to emulate another game simultaneously!", Colors.MAGENTA)
        print_color(f"[*] You can complete ALL orb quests at once in 15 minutes!", Colors.MAGENTA)
    
    input(f"\n{Colors.GRAY}Press Enter to continue...{Colors.RESET}")


def main():
    """Main application loop"""
    print_banner()
    
    print_color("Initializing Discord Orb Quest Faker...", Colors.CYAN)
    print_color("[*] Connecting to Discord API...", Colors.GRAY)
    db = DiscordGamesDB()
    faker = GameFaker()
    print_color("[OK] Ready to fake some games!", Colors.GREEN)
    time.sleep(0.5)
    
    while True:
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            print_banner()
            
            if db.source:
                print_color(f"   Active Database: {db.source} ({len(db.games)} games)", Colors.GRAY)
            
            print_menu()
            
            choice = input(f"{Colors.BOLD}Select option{Colors.RESET} [1-4]: ").strip()
            
            if choice == '1':
                database_mode(db, faker)
            elif choice == '2':
                manual_mode(faker)
            elif choice == '3':
                show_credits()
            elif choice == '4':
                print_color("\n[*] Thanks for using Orb Quest Faker!", Colors.CYAN, bold=True)
                print_color("[*] Developed by Strykey", Colors.GRAY)
                print_color("\n[*] May your orbs be plentiful!", Colors.MAGENTA)
                print_color("[*] Remember: With great power comes great responsibility\n", Colors.GRAY)
                break
            else:
                print_color("\n[ERROR] Invalid option - try 1, 2, 3, or 4", Colors.RED)
                time.sleep(1.5)
                
        except KeyboardInterrupt:
            print_color("\n\n[!] Interrupted by user", Colors.YELLOW)
            print_color("[*] Exiting gracefully...", Colors.GRAY)
            print_color("[*] Thanks for using Orb Quest Faker!\n", Colors.CYAN)
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_color("\n\n[!] Interrupted", Colors.YELLOW)
        sys.exit(0)
    except Exception as e:
        print_color(f"\n[ERROR] Fatal error: {e}", Colors.RED, bold=True)
        print_color("[!] This shouldn't happen. Please report this issue.", Colors.YELLOW)
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
