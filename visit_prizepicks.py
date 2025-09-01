from seleniumbase import SB
import pyautogui
import time
import threading
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json

def show_mouse_coordinates():
    """Display mouse coordinates in real-time"""
    while True:
        try:
            x, y = pyautogui.position()
            print(f"\rMouse position: ({x}, {y})", end="", flush=True)
            time.sleep(0.1)
        except KeyboardInterrupt:
            break
    print()  # New line after stopping

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
        print(f"Error setting up Google Sheets: {e}")
        print("Please ensure you have a service account key file named 'service-account-key.json'")
        return None

def create_or_update_sheet(service, spreadsheet_id, sheet_name, data):
    """Create or update a worksheet with the scraped data"""
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
        
        # Prepare data rows
        rows = [headers]  # First row is headers
        
        for player in data:
            # Extract the line value (projection) from the player data
            line_value = player.get('value', '')
            
            # Create row matching your column structure
            row = [
                player.get('name', ''),           # Player Name
                player.get('position', ''),       # Position
                player.get('team', ''),           # Team
                player.get('opponent', ''),       # Opponent
                player.get('game_time', ''),      # Game Time
                line_value,                       # Line (projection value)
                player.get('payout_type', 'Standard'),  # Payout Type
                '',                               # Actual (empty for now)
                ''                                # Over/Under (empty for now)
            ]
            rows.append(row)
        
        # Check if sheet exists, if not create it
        try:
            # Try to get the sheet
            sheet_metadata = service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                ranges=f"'{sheet_name}'!A1"
            ).execute()
        except:
            # Sheet doesn't exist, create it
            print(f"Creating new worksheet: {sheet_name}")
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
        
        # Update the sheet with data
        range_name = f"'{sheet_name}'!A1"
        body = {
            'values': rows
        }
        
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"Updated {sheet_name} with {len(data)} players")
        return True
        
    except Exception as e:
        print(f"Error updating sheet {sheet_name}: {e}")
        return False

def scrape_prop_type(sb, stat_name):
    """Scrape player projections for a specific prop type"""
    print(f"\n=== Scraping {stat_name} ===")
    
    # Click on the specific stat button
    try:
        sb.cdp.click(f'//button[contains(@class, "stat") and text()="{stat_name}"]')
        sb.cdp.sleep(2)
        print(f"{stat_name} button clicked successfully!")
    except Exception as e:
        print(f"Error clicking {stat_name} button: {e}")
        return []
    
    # Wait for projections to load and scrape player data
    print("Waiting for player projections to load...")
    try:
        sb.cdp.wait_for_element_visible('ul[aria-label="Projections List"]', timeout=10)
        sb.cdp.sleep(2)
    except Exception as e:
        print(f"Error waiting for projections to load: {e}")
        return []
    
    # Scrape player projections
    print("Scraping player projections...")
    player_projections = []
    
    # Get all player cards from the projections list
    player_cards = sb.cdp.select_all('ul[aria-label="Projections List"] li')
    
    for card in player_cards:
        try:
            # Check if this card has the "Money Mouth" image (skip these)
            money_mouth_img = card.query_selector('img[alt="Money Mouth"]')
            if money_mouth_img:
                print(f"Skipping player with Money Mouth indicator")
                continue
            
            # Check if this card has a "Goblin" or "Demon" indicator
            goblin_img = card.query_selector('img[alt="Goblin"]')
            demon_img = card.query_selector('img[alt="Demon"]')
            payout_type = "Standard"
            
            if goblin_img or demon_img:
                indicator_type = "Goblin" if goblin_img else "Demon"
                print(f"Found {indicator_type} indicator")
                
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
                    
                    # Click the test-projection-swap button until we find a clean prop line
                    max_attempts = 10  # Prevent infinite loops
                    attempts = 0
                    found_clean_prop = False
                    
                    while attempts < max_attempts and not found_clean_prop:
                        attempts += 1
                        print(f"  Attempt {attempts}: Clicking test-projection-swap...")
                        
                        # Click the swap button
                        swap_button = card.query_selector('button#test-projection-swap')
                        if swap_button:
                            swap_button.click()
                            sb.cdp.sleep(1)  # Wait for prop line to update
                            
                            # Check if indicator is still present
                            current_goblin = card.query_selector('img[alt="Goblin"]')
                            current_demon = card.query_selector('img[alt="Demon"]')
                            if not current_goblin and not current_demon:
                                print(f"  Found clean prop line after {attempts} attempts!")
                                found_clean_prop = True
                            else:
                                print(f"  {indicator_type} still present, trying again...")
                        else:
                            print(f"  No swap button found, skipping this player")
                            break
                    
                    if not found_clean_prop:
                        print(f"  Could not find clean prop line after {max_attempts} attempts, skipping player")
                        continue
                    
                    # After finding clean prop, we need to re-find the card in the DOM
                    # The card reference is stale, so we need to get a fresh reference
                    print(f"  Re-finding card in DOM after swap...")
                    
                    # We already have the player name, so use it to find the fresh card
                    print(f"  Looking for updated card for: {player_name}")
                    
                    # Re-find the card by looking for the player name in the fresh DOM
                    fresh_cards = sb.cdp.select_all('ul[aria-label="Projections List"] li')
                    fresh_card = None
                    
                    for fresh_c in fresh_cards:
                        name_check = fresh_c.query_selector('h3[id="test-player-name"]')
                        if name_check and name_check.text.strip() == player_name:
                            # Check if this fresh card has no indicators
                            goblin_check = fresh_c.query_selector('img[alt="Goblin"]')
                            demon_check = fresh_c.query_selector('img[alt="Demon"]')
                            if not goblin_check and not demon_check:
                                fresh_card = fresh_c
                                print(f"  Found fresh card without indicators for: {player_name}")
                                break
                    
                    if fresh_card:
                        card = fresh_card  # Update our reference to the fresh card
                    else:
                        print(f"  Could not find fresh card for: {player_name}, skipping")
                        continue
                else:
                    print(f"  No swap button found, storing {indicator_type} indicator")
                    payout_type = indicator_type
            
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
                
                print(f"Scraped: {projection_text}")
                
        except Exception as e:
            print(f"Error scraping player card: {e}")
            continue
    
    return player_projections

def get_all_stat_types(sb):
    """Get specific stat types to scrape"""
    # Predefined list of stat types to scrape
    stat_types = [
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
    
    print(f"Will scrape {len(stat_types)} specific stat types: {stat_types}")
    return stat_types

# Configuration
SPREADSHEET_ID = "1H9HcjtjoG9AlRJ3lAvgZXpefYfuVcylwqc4D4B_Ai1g"  # Replace with your actual spreadsheet ID

with SB(uc=True, test=True, locale="en", ad_block=True) as sb:
    # Setup Google Sheets
    sheets_service = setup_google_sheets()
    if not sheets_service:
        print("Google Sheets setup failed. Continuing with console output only.")
    
    url = "https://app.prizepicks.com/"
    sb.activate_cdp_mode(url)
    # Click "Accept All" button if it appears (cookie consent)
    try:
        sb.cdp.click('button#ketch-banner-button-primary')
        sb.cdp.sleep(1)
        print("Accept All button clicked successfully!")
    except Exception:
        print("No Accept All button found or already handled.")
    
    # Click "Got it" button if it appears (welcome modal)
    try:
        sb.cdp.click('button[title="Got it"]')
        sb.cdp.sleep(1)
        print("Got it button clicked successfully!")
    except Exception:
        print("No Got it button found or already handled.")
    
    # Using exact coordinates for location clicks
    print("Using exact coordinates for location clicks...")
    
    # Click the location icon at the top of the browser using pyautogui
    try:
        # First click: Location icon at (947, 91)
        print("Clicking first location at coordinates (947, 91)...")
        pyautogui.click(947, 91)
        sb.cdp.sleep(2)
        print("First location clicked successfully!")
        
        # Second click: Next location at (872, 219)
        print("Clicking second location at coordinates (872, 219)...")
        pyautogui.click(872, 219)
        sb.cdp.sleep(2)
        print("Second location clicked successfully!")
        
        # Refresh the page after location clicks
        print("Refreshing the page...")
        sb.refresh()
        sb.cdp.sleep(3)  # Wait for page to reload
        print("Page refreshed successfully!")
        
    except Exception as e:
        print(f"Error clicking locations: {e}")
    
    # Close the welcome modal if it appears
    try:
        sb.cdp.click('button.close')
        sb.cdp.sleep(1)
        print("Welcome modal closed successfully!")
    except Exception:
        print("No welcome modal found or already closed.")
    
    # Click on the NFL tab - using XPath for exact text matching
    sb.cdp.click('//button[contains(@class, "league")]//span[text()="NFL" and not(contains(text(), "NFLSZN"))]')
    sb.cdp.sleep(2)
    
    print("NFL tab clicked successfully!")
    
    # Get all available stat types
    stat_types = get_all_stat_types(sb)
    
    if not stat_types:
        print("No stat types found. Falling back to Pass Yards only.")
        stat_types = ["Pass Yards"]
    
    # Scrape all prop types
    all_projections = {}
    
    for stat_type in stat_types:
        try:
            projections = scrape_prop_type(sb, stat_type)
            all_projections[stat_type] = projections
            print(f"Completed scraping {stat_type}: {len(projections)} players found")
            
            # Update Google Sheets if service is available
            if sheets_service and SPREADSHEET_ID != "YOUR_SPREADSHEET_ID_HERE":
                sheet_name = stat_type.replace("+", " Plus ")  # Handle special characters for sheet names
                success = create_or_update_sheet(sheets_service, SPREADSHEET_ID, sheet_name, projections)
                if success:
                    print(f"✓ Data uploaded to Google Sheets: {sheet_name}")
                else:
                    print(f"✗ Failed to upload data to Google Sheets: {sheet_name}")
            else:
                print("Skipping Google Sheets upload (service not available or ID not configured)")
            
            # Small delay between stat types to avoid overwhelming the page
            sb.cdp.sleep(1)
            
        except Exception as e:
            print(f"Error scraping {stat_type}: {e}")
            all_projections[stat_type] = []
    
    # Display comprehensive results
    print(f"\n{'='*60}")
    print("COMPREHENSIVE SCRAPING RESULTS")
    print(f"{'='*60}")
    
    total_players = 0
    for stat_type, projections in all_projections.items():
        print(f"\n{stat_type.upper()} ({len(projections)} players):")
        print("-" * 40)
        
        if projections:
            for player in projections:
                payout_status = ""
                if player.get('payout_type') == "Goblin":
                    payout_status = " [GOBLIN]"
                elif player.get('payout_type') == "Demon":
                    payout_status = " [DEMON]"
                
                print(f"• {player['name']} ({player['team']} - {player['position']}) vs {player['opponent']} at {player['game_time']}{payout_status}")
                print(f"  Projection: {player['value']} {player['stat_type']}")
                print()
        else:
            print("No players found for this stat type.")
        
        total_players += len(projections)
    
    print(f"\n{'='*60}")
    print(f"TOTAL PLAYERS SCRAPED ACROSS ALL STAT TYPES: {total_players}")
    print(f"{'='*60}")
    
    if sheets_service and SPREADSHEET_ID != "YOUR_SPREADSHEET_ID_HERE":
        print(f"\n✓ Data has been uploaded to Google Sheets!")
        print(f"  Spreadsheet ID: {SPREADSHEET_ID}")
        print(f"  Worksheets created/updated: {len(stat_types)}")
    else:
        print(f"\n⚠ Google Sheets integration not configured")
        print(f"  To enable, update SPREADSHEET_ID and ensure service-account-key.json is present")
    
    sb.cdp.sleep(2.5)