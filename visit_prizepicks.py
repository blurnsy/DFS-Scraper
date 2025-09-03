from seleniumbase import SB
import pyautogui
import time
import threading
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json
from datetime import datetime, timedelta
import re
from termcolor import cprint
import monitor

def show_mouse_coordinates():
    """Display mouse coordinates in real-time - redirects to utils"""
    import sys
    sys.path.append('utils')
    from mouse_coordinates import display_mouse_coordinates
    display_mouse_coordinates()

# Game time parsing moved to monitor.py

# Game time reading moved to monitor.py

# Upcoming games detection moved to monitor.py

def run_final_scraping_for_game(game_info, sheets_service):
    """Run final scraping session for a specific game"""
    cprint(f"🚀 Opening browser for FINAL scraping of {game_info['team']} vs {game_info['opponent']}...", "green", attrs=["bold"])
    
    with SB(uc=True, test=True, locale="en", ad_block=True) as sb:
        # Initialize the browser session
        initialize_browser_session(sb)
        
        # Run full scraping session for all stat types
        all_stat_types = get_all_stat_types()
        scrape_selected_stats(sb, sheets_service, all_stat_types)
        
        cprint(f"✅ Final scraping completed for {game_info['team']} vs {game_info['opponent']}", "green", attrs=["bold"])
        cprint(f"   This was the last scrape before the game starts!", "yellow")

# Next game info moved to monitor.py

# Game monitoring moved to monitor.py

def setup_google_sheets():
    """Setup Google Sheets API connection"""
    try:
        # You'll need to create a service account and download the JSON key file
        # Place it in your project directory and update the path below
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        SERVICE_ACCOUNT_FILE = 'service-account-key.json'
        
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        cprint(f"Error setting up Google Sheets: {e}", "red")
        cprint("Please ensure you have a service account key file named 'service-account-key.json'", "yellow")
        return None

def read_existing_sheet_data(service, spreadsheet_id, sheet_name):
    """Read existing data from the sheet to preserve Actual and Over/Under columns"""
    try:
        # Read all data from the sheet
        range_name = f"'{sheet_name}'!A:I"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return {}
        
        # Skip header row and build a lookup dictionary
        existing_data = {}
        for i, row in enumerate(values[1:], start=2):  # Start from row 2 (skip header)
            if len(row) >= 6:  # Ensure we have at least the basic columns
                # Create a unique key from player name, team, opponent, and game time
                player_key = f"{row[0]}|{row[2]}|{row[3]}|{row[4]}".lower().strip()
                existing_data[player_key] = {
                    'row_index': i,
                    'line': row[5] if len(row) > 5 else '',
                    'actual': row[7] if len(row) > 7 else '',
                    'over_under': row[8] if len(row) > 8 else '',
                    'payout_type': row[6] if len(row) > 6 else 'Standard'
                }
        
        return existing_data
    except Exception as e:
        cprint(f"Error reading existing sheet data: {e}", "red")
        return {}

def create_or_update_sheet(service, spreadsheet_id, sheet_name, data):
    """Create or update a worksheet with smart line updates only"""
    try:
        # Define the column headers based on your spreadsheet layout
        headers = [
            "Player Name",
            "Position", 
            "Team",
            "Opponent",
            "Game Time",
            "Line",
            "Payout Type",
            "Actual",
            "Over/Under"
        ]
        
        # Check if sheet exists, if not create it
        sheet_exists = True
        try:
            # Try to get the sheet
            sheet_metadata = service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                ranges=f"'{sheet_name}'!A1"
            ).execute()
        except:
            # Sheet doesn't exist, create it
            cprint(f"Creating new worksheet: {sheet_name}", "green", attrs=["bold"])
            request = {
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }
            
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [request]}
            ).execute()
            sheet_exists = False
        
        # Read existing data if sheet exists
        existing_data = {}
        if sheet_exists:
            existing_data = read_existing_sheet_data(service, spreadsheet_id, sheet_name)
        
        # Prepare data for update
        rows_to_update = []
        new_rows = []
        updated_count = 0
        unchanged_count = 0
        
        for player in data:
            # Create unique key for this player
            player_key = f"{player.get('name', '')}|{player.get('team', '')}|{player.get('opponent', '')}|{player.get('game_time', '')}".lower().strip()
            new_line_value = player.get('value', '')
            
            if player_key in existing_data:
                # Player exists, check if line has changed
                existing_line = existing_data[player_key]['line']
                if existing_line != new_line_value:
                    # Line has changed, update it
                    row_index = existing_data[player_key]['row_index']
                    rows_to_update.append({
                        'range': f"'{sheet_name}'!F{row_index}",
                        'values': [[new_line_value]]
                    })
                    updated_count += 1
                    cprint(f"  Updating {player.get('name', '')} line: {existing_line} → {new_line_value}", "yellow")
                else:
                    # Line unchanged, skip update
                    unchanged_count += 1
                    cprint(f"  Skipping {player.get('name', '')} (line unchanged: {new_line_value})", "cyan")
            else:
                # New player, add to new rows
                row = [
                    player.get('name', ''),           # Player Name
                    player.get('position', ''),       # Position
                    player.get('team', ''),           # Team
                    player.get('opponent', ''),       # Opponent
                    player.get('game_time', ''),      # Game Time
                    new_line_value,                   # Line (projection value)
                    player.get('payout_type', 'Standard'),  # Payout Type
                    '',                               # Actual (empty for new players)
                    ''                                # Over/Under (empty for new players)
                ]
                new_rows.append(row)
        
        # Perform updates
        if rows_to_update:
            # Update existing rows with changed lines
            body = {
                'valueInputOption': 'RAW',
                'data': rows_to_update
            }
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            cprint(f"  Updated {updated_count} existing players with new line values", "green")
        
        if new_rows:
            # Add new players to the sheet
            if not sheet_exists:
                # If it's a new sheet, add headers and all data
                all_rows = [headers] + new_rows
                range_name = f"'{sheet_name}'!A1"
                body = {'values': all_rows}
            else:
                # Append new rows to existing sheet
                range_name = f"'{sheet_name}'!A:I"
                body = {'values': new_rows}
            
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            cprint(f"  Added {len(new_rows)} new players", "green")
        
        cprint(f"Smart update completed for {sheet_name}:", "green", attrs=["bold"])
        cprint(f"  - Updated: {updated_count} players", "yellow")
        cprint(f"  - Unchanged: {unchanged_count} players", "cyan") 
        cprint(f"  - New: {len(new_rows)} players", "green")
        cprint(f"  - Total processed: {len(data)} players", "white")
        
        return True
        
    except Exception as e:
        cprint(f"Error updating sheet {sheet_name}: {e}", "red")
        return False

def is_live_betting_player(card):
    """Check if a player card indicates live betting (game has started)"""
    try:
        # Look for the "Starting" indicator div with specific classes
        starting_indicator = card.query_selector('div.body-xs.absolute.left-2.top-2.flex.items-center.gap-1.p-1')
        if starting_indicator:
            starting_text = starting_indicator.text.strip().lower()
            if 'starting' in starting_text:
                return True
        
        # Alternative selector patterns for "Starting" indicator
        starting_divs = card.query_selector_all('div[class*="absolute"][class*="left-2"][class*="top-2"]')
        for div in starting_divs:
            if 'starting' in div.text.strip().lower():
                return True
        
        # Look for any div containing "Starting" text (broader search)
        all_divs = card.query_selector_all('div')
        for div in all_divs:
            div_text = div.text.strip().lower()
            if div_text == 'starting' or 'starting' in div_text:
                # Make sure it's not just part of a longer word
                if div_text == 'starting' or div_text.startswith('starting ') or div_text.endswith(' starting'):
                    return True
        
        # Look for "Live" indicators as well
        live_indicators = card.query_selector_all('*')
        for element in live_indicators:
            element_text = element.text.strip().lower()
            if element_text == 'live' or 'live betting' in element_text:
                return True
                
        return False
    except Exception as e:
        # If there's an error checking, assume it's not live betting
        return False

def scrape_prop_type(sb, stat_name):
    """Scrape player projections for a specific prop type"""
    cprint(f"\n=== Scraping {stat_name} ===", "cyan", attrs=["bold"])
    
    # Click on the specific stat button
    try:
        sb.cdp.click(f'//button[contains(@class, "stat") and text()="{stat_name}"]')
        sb.cdp.sleep(2)
        cprint(f"{stat_name} button clicked successfully!", "green")
    except Exception as e:
        cprint(f"Error clicking {stat_name} button: {e}", "red")
        return []
    
    # Wait for projections to load and scrape player data
    cprint("Waiting for player projections to load...", "cyan")
    try:
        sb.cdp.wait_for_element_visible('ul[aria-label="Projections List"]', timeout=10)
        sb.cdp.sleep(2)
    except Exception as e:
        cprint(f"Error waiting for projections to load: {e}", "red")
        return []
    
    # Scrape player projections
    cprint("Scraping player projections...", "cyan")
    player_projections = []
    live_betting_skipped = 0
    
    # Get all player cards from the projections list
    player_cards = sb.cdp.select_all('ul[aria-label="Projections List"] li')
    
    for card in player_cards:
        try:
            # Check if this is a live betting player (game has started)
            if SKIP_LIVE_BETTING and is_live_betting_player(card):
                # Get player name for logging
                name_elem = card.query_selector('h3[id="test-player-name"]')
                if not name_elem:
                    name_elem = card.query_selector('h3[aria-label="name"]')
                player_name = name_elem.text.strip() if name_elem else "Unknown Player"
                cprint(f"🚫 Skipping {player_name} - Game has started (Live Betting)", "red")
                live_betting_skipped += 1
                continue
            
            # Check if this card has the "Money Mouth" image (skip these)
            money_mouth_img = card.query_selector('img[alt="Money Mouth"]')
            if money_mouth_img:
                cprint(f"Skipping player with Money Mouth indicator", "yellow")
                continue
            
            # Check if this card has a "Goblin" or "Demon" indicator
            goblin_img = card.query_selector('img[alt="Goblin"]')
            demon_img = card.query_selector('img[alt="Demon"]')
            payout_type = "Standard"  # Default to Standard
            
            if goblin_img or demon_img:
                indicator_type = "Goblin" if goblin_img else "Demon"
                cprint(f"Found {indicator_type} indicator", "magenta")
                
                # Check if there's a test-projection-swap button
                swap_button = card.query_selector('button#test-projection-swap')
                
                if swap_button:
                    print(f"  Found swap button, cycling through prop lines...")
                    
                    # Capture the player name BEFORE we start swapping (while card is still valid)
                    player_name_elem = card.query_selector('h3[id="test-player-name"]')
                    if not player_name_elem:
                        player_name_elem = card.query_selector('h3[aria-label="name"]')
                    
                    if not player_name_elem:
                        print(f"  Could not get player name, skipping this player")
                        continue
                    
                    player_name = player_name_elem.text.strip()
                    print(f"  Player name captured: {player_name}")
                    
                    # Store the original card state (first appearance on page)
                    original_goblin = goblin_img
                    original_demon = demon_img
                    original_indicator_type = indicator_type
                    
                    # Get the original projection value
                    original_value_elem = card.query_selector('span.duration-300.ease-in')
                    original_projection = original_value_elem.text.strip() if original_value_elem else ""
                    
                    # Track all seen lines for logging
                    all_seen_lines = []
                    all_seen_lines.append(f"{original_projection} {original_indicator_type}")
                    
                    # Click the test-projection-swap button until we find a Standard card or exhaust all swaps
                    max_attempts = 10  # Prevent infinite loops
                    attempts = 0
                    found_standard_card = False
                    seen_projections = set()  # Track unique projections to detect when we've cycled through all
                    
                    while attempts < max_attempts and not found_standard_card:
                        attempts += 1
                        print(f"  Attempt {attempts}: Clicking test-projection-swap...")
                        
                        # Click the swap button
                        swap_button = card.query_selector('button#test-projection-swap')
                        if swap_button:
                            swap_button.click()
                            sb.cdp.sleep(2)  # Wait for prop line to update and DOM to stabilize
                            
                            # Check if we now have a Standard card (no indicators)
                            current_goblin = card.query_selector('img[alt="Goblin"]')
                            current_demon = card.query_selector('img[alt="Demon"]')
                            
                            # Get the new projection value
                            new_value_elem = card.query_selector('span.duration-300.ease-in')
                            new_projection = new_value_elem.text.strip() if new_value_elem else ""
                            
                            # More robust check for Standard card - ensure no indicators are present
                            if not current_goblin and not current_demon:
                                # Double-check by looking for any indicator images
                                any_indicators = card.query_selector_all('img[alt="Goblin"], img[alt="Demon"]')
                                if not any_indicators:
                                    all_seen_lines.append(f"{new_projection} Standard")
                                    print(f"  Found Standard card after {attempts} attempts!")
                                    found_standard_card = True
                                    break  # Stop immediately when we find a Standard card
                                else:
                                    print(f"  False positive - indicators still present, continuing...")
                            else:
                                # Track this line
                                current_indicator = "Goblin" if current_goblin else "Demon"
                                all_seen_lines.append(f"{new_projection} {current_indicator}")
                                
                                # Check if we've seen this projection before (indicating we've cycled through all options)
                                if new_projection in seen_projections:
                                    print(f"  Cycled through all available swaps ({attempts} attempts)")
                                    break
                                
                                seen_projections.add(new_projection)
                                print(f"  Still {current_indicator} card, projection: {new_projection}, trying again...")
                        else:
                            print(f"  No swap button found, skipping this player")
                            break
                    
                    # Log all seen lines
                    lines_text = ", ".join(all_seen_lines)
                    print(f"  All lines seen: {lines_text}")
                    
                    if not found_standard_card:
                        if attempts >= max_attempts:
                            print(f"  Reached max attempts ({max_attempts})")
                        print(f"  No clean card option found - Grabbing {original_indicator_type}")
                        # Reset to original card state
                        payout_type = original_indicator_type
                        selected_line = f"{original_projection} {original_indicator_type}"
                    else:
                        # We found a Standard card, use the last line we saw
                        selected_line = all_seen_lines[-1]
                    
                    print(f"  Selected line: {selected_line}")
                    
                    # After finding clean prop, we need to re-find the card in the DOM
                    # The card reference is stale, so we need to get a fresh reference
                    print(f"  Re-finding card in DOM after swap...")
                    sb.cdp.sleep(1)  # Give DOM time to fully update
                    
                    # We already have the player name, so use it to find the fresh card
                    print(f"  Looking for updated card for: {player_name}")
                    
                    # Re-find the card by looking for the player name in the fresh DOM
                    fresh_cards = sb.cdp.select_all('ul[aria-label="Projections List"] li')
                    fresh_card = None
                    
                    # First try exact name match
                    for fresh_c in fresh_cards:
                        name_check = fresh_c.query_selector('h3[id="test-player-name"]')
                        if name_check and name_check.text.strip() == player_name:
                            # Accept the card regardless of indicators - we just need the updated projection
                            fresh_card = fresh_c
                            print(f"  Found fresh card for: {player_name}")
                            break
                    
                    # If exact match fails, try partial name match as fallback
                    if not fresh_card:
                        print(f"  Exact name match failed, trying partial match for: {player_name}")
                        for fresh_c in fresh_cards:
                            name_check = fresh_c.query_selector('h3[id="test-player-name"]')
                            if name_check:
                                name_text = name_check.text.strip()
                                # Check if the name contains the key parts (first and last name)
                                name_parts = player_name.split()
                                if len(name_parts) >= 2:
                                    first_name = name_parts[0]
                                    last_name = name_parts[-1]
                                    if first_name in name_text and last_name in name_text:
                                        fresh_card = fresh_c
                                        print(f"  Found fresh card via partial match: {name_text}")
                                        break
                    
                    if fresh_card:
                        card = fresh_card  # Update our reference to the fresh card
                        
                        # Determine final payout type based on the fresh card
                        if found_standard_card:
                            # We found a Standard card, use it
                            final_goblin = fresh_card.query_selector('img[alt="Goblin"]')
                            final_demon = fresh_card.query_selector('img[alt="Demon"]')
                            
                            if final_goblin:
                                payout_type = "Goblin"
                            elif final_demon:
                                payout_type = "Demon"
                            else:
                                payout_type = "Standard"
                        else:
                            # We didn't find a Standard card, use the original card type
                            payout_type = original_indicator_type
                            
                        print(f"  Final card type: {payout_type}")
                    else:
                        print(f"  Could not find fresh card for: {player_name}, skipping")
                        continue
                else:
                    print(f"  No swap button found, storing {indicator_type} indicator")
                    payout_type = indicator_type
            else:
                # No indicators found, this is a Standard card
                payout_type = "Standard"
            
            # Extract player name
            name_elem = card.query_selector('h3[id="test-player-name"]')
            if not name_elem:
                name_elem = card.query_selector('h3[aria-label="name"]')
            
            # Extract projection value (the number)
            value_elem = card.query_selector('span.duration-300.ease-in')
            
            # Extract stat type (e.g., "Pass Yards")
            stat_elem = card.query_selector('span.break-words')
            
            # Extract team and position
            team_pos_elem = card.query_selector('div#test-team-position')
            
            # Extract opponent and game time
            time_elem = card.query_selector('time[aria-label="Start Time"]')
            
            if name_elem and value_elem and stat_elem:
                name = name_elem.text.strip()
                value = value_elem.text.strip()
                stat_type = stat_elem.text.strip()
                
                # Extract team and position from the team-position element
                team = ""
                position = ""
                if team_pos_elem:
                    team_pos_text = team_pos_elem.text.strip()
                    if " - " in team_pos_text:
                        team, position = team_pos_text.split(" - ", 1)
                    else:
                        team = team_pos_text
                
                # Extract opponent and game time
                opponent = ""
                game_time = ""
                if time_elem:
                    # Get all span elements within the time element
                    spans = time_elem.query_selector_all('span')
                    if len(spans) >= 2:
                        opponent = spans[0].text.strip()  # First span contains opponent (e.g., "PHI")
                        game_time = spans[1].text.strip()  # Second span contains time (e.g., "Thu 7:20pm")
                    elif len(spans) == 1:
                        # Fallback: if only one span, it might contain both or just time
                        time_text = spans[0].text.strip()
                        if " " in time_text and any(day in time_text.lower() for day in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']):
                            game_time = time_text
                        else:
                            opponent = time_text
                
                # Combine into the format you want
                projection_text = f"{name} ({team} - {position}) vs {opponent} at {game_time} - {value} {stat_type}"
                
                # Add payout type to the display text if it's not Standard
                display_text = projection_text
                if payout_type != "Standard":
                    display_text += f" ({payout_type})"
                
                player_projections.append({
                    'name': name,
                    'team': team,
                    'position': position,
                    'opponent': opponent,
                    'game_time': game_time,
                    'value': value,
                    'stat_type': stat_type,
                    'payout_type': payout_type,
                    'full_text': projection_text
                })
                
                print(f"Scraped: {display_text}")
                
        except Exception as e:
            cprint(f"Error scraping player card: {e}", "red")
            continue
    
    # Print summary of live betting players skipped
    if SKIP_LIVE_BETTING and live_betting_skipped > 0:
        cprint(f"\n🚫 Skipped {live_betting_skipped} live betting player(s) - Games have started", "red")
    
    return player_projections

def get_all_stat_types():
    """Get all available stat types"""
    return [
        "Pass Yards",
        "Rush Yards", 
        "Pass TDs",
        "Receiving Yards",
        "FG Made",
        "Receptions",
        "Rush+Rec Yds",
        "Fantasy Score",
        "Pass Attempts",
        "Rec Targets",
        "Sacks",
        "Pass Completions",
        "INT",
        "Pass+Rush Yds",
        "Rush Attempts",
        "Kicking Points",
        "Tackles+Ast"
    ]

def display_menu():
    """Display CLI menu for stat type selection"""
    stat_types = get_all_stat_types()
    
    cprint("\n" + "="*50, "cyan")
    cprint("PRIZEPICKS SCRAPER - STAT TYPE SELECTION", "yellow", attrs=["bold"])
    cprint("="*50, "cyan")
    cprint("Select which prop type you want to scrape:", "white")
    print()
    
    for i, stat_type in enumerate(stat_types, 1):
        cprint(f"{i:2d}) {stat_type}", "white")
    
    cprint(f"{len(stat_types) + 1:2d}) All Stats", "green")
    print()
    
    return stat_types

def get_user_selection():
    """Get and validate user selection from menu"""
    stat_types = display_menu()
    
    while True:
        try:
            choice = input("Enter your choice (1-{}): ".format(len(stat_types) + 1)).strip()
            
            if not choice:
                cprint("Please enter a valid choice.", "red")
                continue
                
            choice_num = int(choice)
            
            if choice_num == len(stat_types) + 1:
                return stat_types  # All stats
            elif 1 <= choice_num <= len(stat_types):
                return [stat_types[choice_num - 1]]  # Single stat type
            else:
                cprint(f"Please enter a number between 1 and {len(stat_types) + 1}", "red")
                
        except ValueError:
            cprint("Please enter a valid number.", "red")
        except KeyboardInterrupt:
            cprint("\nExiting...", "yellow")
            exit(0)

def ask_continue():
    """Ask if user wants to scrape more stats"""
    while True:
        try:
            response = input("\nWould you like to scrape more stats? (y/n): ").strip().lower()
            
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                cprint("Please enter 'y' for yes or 'n' for no.", "red")
                
        except KeyboardInterrupt:
            cprint("\nExiting...", "yellow")
            exit(0)

# Configuration
SPREADSHEET_ID = "1H9HcjtjoG9AlRJ3lAvgZXpefYfuVcylwqc4D4B_Ai1g"  # Replace with your actual spreadsheet ID
SKIP_LIVE_BETTING = True  # Set to False if you want to track live betting lines

def initialize_browser_session(sb):
    """Initialize the browser session with PrizePicks setup"""
    # Setup Google Sheets
    sheets_service = setup_google_sheets()
    if not sheets_service:
        cprint("Google Sheets setup failed. Continuing with console output only.", "yellow")
    
    url = "https://app.prizepicks.com/"
    sb.activate_cdp_mode(url)
    
    # Click "Accept All" button if it appears (cookie consent)
    try:
        sb.cdp.click('button#ketch-banner-button-primary')
        sb.cdp.sleep(1)
        cprint("Accept All button clicked successfully!", "green")
    except Exception:
        cprint("No Accept All button found or already handled.", "cyan")
    
    # Click "Got it" button if it appears (welcome modal)
    try:
        sb.cdp.click('button[title="Got it"]')
        sb.cdp.sleep(1)
        cprint("Got it button clicked successfully!", "green")
    except Exception:
        cprint("No Got it button found or already handled.", "cyan")
    
    # Using exact coordinates for location clicks
    cprint("Using exact coordinates for location clicks...", "cyan")
    
    # Click the location icon at the top of the browser using pyautogui
    try:
        # First click: Location icon at (947, 91)
        cprint("Clicking first location at coordinates (947, 91)...", "cyan")
        pyautogui.click(947, 91)
        sb.cdp.sleep(2)
        cprint("First location clicked successfully!", "green")
        
        # Second click: Next location at (872, 219)
        cprint("Clicking second location at coordinates (872, 219)...", "cyan")
        pyautogui.click(872, 219)
        sb.cdp.sleep(2)
        cprint("Second location clicked successfully!", "green")
        
        # Refresh the page after location clicks
        cprint("Refreshing the page...", "cyan")
        sb.refresh()
        sb.cdp.sleep(3)  # Wait for page to reload
        cprint("Page refreshed successfully!", "green")
        
    except Exception as e:
        cprint(f"Error clicking locations: {e}", "red")
    
    # Close the welcome modal if it appears
    try:
        sb.cdp.click('button.close')
        sb.cdp.sleep(1)
        cprint("Welcome modal closed successfully!", "green")
    except Exception:
        cprint("No welcome modal found or already closed.", "cyan")
    
    # Click on the NFL tab - using XPath for exact text matching
    sb.cdp.click('//button[contains(@class, "league")]//span[text()="NFL" and not(contains(text(), "NFLSZN"))]')
    sb.cdp.sleep(2)
    
    cprint("NFL tab clicked successfully!", "green")
    cprint("Browser session ready!", "green", attrs=["bold"])
    
    return sheets_service

def scrape_selected_stats(sb, sheets_service, selected_stat_types):
    """Scrape the selected stat types"""
    # Use the stat types selected by the user
    stat_types = selected_stat_types
    
    if not stat_types:
        cprint("No stat types selected. Falling back to Pass Yards only.", "yellow")
        stat_types = ["Pass Yards"]
    
    # Scrape all prop types
    all_projections = {}
    
    for stat_type in stat_types:
        try:
            projections = scrape_prop_type(sb, stat_type)
            all_projections[stat_type] = projections
            cprint(f"Completed scraping {stat_type}: {len(projections)} players found", "green")
            
            # Update Google Sheets if service is available
            if sheets_service and SPREADSHEET_ID != "YOUR_SPREADSHEET_ID_HERE":
                sheet_name = stat_type.replace("+", " Plus ")  # Handle special characters for sheet names
                success = create_or_update_sheet(sheets_service, SPREADSHEET_ID, sheet_name, projections)
                if success:
                    cprint(f"✓ Data uploaded to Google Sheets: {sheet_name}", "green")
                else:
                    cprint(f"✗ Failed to upload data to Google Sheets: {sheet_name}", "red")
            else:
                cprint("Skipping Google Sheets upload (service not available or ID not configured)", "yellow")
            
            # Small delay between stat types to avoid overwhelming the page
            sb.cdp.sleep(1)
            
        except Exception as e:
            cprint(f"Error scraping {stat_type}: {e}", "red")
            all_projections[stat_type] = []
    
    # Display comprehensive results
    cprint(f"\n{'='*60}", "cyan")
    cprint("COMPREHENSIVE SCRAPING RESULTS", "yellow", attrs=["bold"])
    cprint(f"{'='*60}", "cyan")
    
    total_players = 0
    for stat_type, projections in all_projections.items():
        cprint(f"\n{stat_type.upper()} ({len(projections)} players):", "green", attrs=["bold"])
        cprint("-" * 40, "cyan")
        
        if projections:
            for player in projections:
                payout_status = ""
                if player.get('payout_type') == "Goblin":
                    payout_status = " [GOBLIN]"
                elif player.get('payout_type') == "Demon":
                    payout_status = " [DEMON]"
                
                cprint(f"• {player['name']} ({player['team']} - {player['position']}) vs {player['opponent']} at {player['game_time']}{payout_status}", "white")
                cprint(f"  Projection: {player['value']} {player['stat_type']}", "cyan")
                print()
        else:
            cprint("No players found for this stat type.", "yellow")
        
        total_players += len(projections)
    
    cprint(f"\n{'='*60}", "cyan")
    cprint(f"TOTAL PLAYERS SCRAPED ACROSS ALL STAT TYPES: {total_players}", "green", attrs=["bold"])
    cprint(f"{'='*60}", "cyan")
    
    if sheets_service and SPREADSHEET_ID != "YOUR_SPREADSHEET_ID_HERE":
        cprint(f"\n✓ Data has been uploaded to Google Sheets!", "green", attrs=["bold"])
        cprint(f"  Spreadsheet ID: {SPREADSHEET_ID}", "cyan")
        cprint(f"  Worksheets created/updated: {len(stat_types)}", "cyan")
    else:
        cprint(f"\n⚠ Google Sheets integration not configured", "yellow")
        cprint(f"  To enable, update SPREADSHEET_ID and ensure service-account-key.json is present", "yellow")

def run_scraping_session(selected_stat_types):
    """Run a single scraping session with the selected stat types"""
    cprint(f"\nSelected stat type(s): {', '.join(selected_stat_types)}", "green", attrs=["bold"])
    cprint("Starting browser session...", "cyan")
    
    with SB(uc=True, test=True, locale="en", ad_block=True) as sb:
        # Initialize the browser session
        sheets_service = initialize_browser_session(sb)
        
        # Scrape the selected stats
        scrape_selected_stats(sb, sheets_service, selected_stat_types)
        
        sb.cdp.sleep(2.5)

# Monitoring session moved to monitor.py

# Main execution loop
def main():
    """Main execution function with continuous scraping loop"""
    cprint("Welcome to PrizePicks Scraper!", "green", attrs=["bold"])
    cprint("This tool will help you scrape player projections from PrizePicks.", "cyan")
    
    if SKIP_LIVE_BETTING:
        cprint("🚫 Live betting filtering is ENABLED - Players with 'Starting' indicators will be skipped", "yellow")
    else:
        cprint("⚠️  Live betting filtering is DISABLED - All players will be tracked including live betting", "red")
    
    try:
        while True:
            # Get user selection
            selected_stat_types = get_user_selection()
            
            # Run regular scraping session
            run_scraping_session(selected_stat_types)
            
            # Ask if user wants to continue
            if not ask_continue():
                cprint("\nThank you for using PrizePicks Scraper!", "green", attrs=["bold"])
                break
                
    except KeyboardInterrupt:
        cprint("\n\nExiting...", "yellow")
    except Exception as e:
        cprint(f"\nAn error occurred: {e}", "red")

# Run the main function
if __name__ == "__main__":
    main()