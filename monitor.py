#!/usr/bin/env python3

from datetime import datetime, timedelta
import re
import time
from typing import Dict, List, Optional, Any
from termcolor import cprint

def parse_game_time(game_time_str):
    """Parse game time string from PrizePicks and return datetime object"""
    if not game_time_str:
        return None
    
    try:
        # Handle formats like "Thu 7:20pm", "Fri 8:15pm", "Sun 1:00pm"
        # Extract day and time
        match = re.match(r'(\w{3})\s+(\d{1,2}):(\d{2})([ap]m)', game_time_str.strip())
        if not match:
            return None
        
        day_abbr, hour, minute, ampm = match.groups()
        
        # Convert to 24-hour format
        hour = int(hour)
        minute = int(minute)
        if ampm.lower() == 'pm' and hour != 12:
            hour += 12
        elif ampm.lower() == 'am' and hour == 12:
            hour = 0
        
        # Map day abbreviations to numbers (0=Monday, 6=Sunday)
        day_map = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
        day_num = day_map.get(day_abbr.lower())
        if day_num is None:
            return None
        
        # Get current date and find the next occurrence of this day
        today = datetime.now()
        days_ahead = (day_num - today.weekday()) % 7
        if days_ahead == 0 and (hour < today.hour or (hour == today.hour and minute <= today.minute)):
            days_ahead = 7  # Next week
        
        game_date = today + timedelta(days=days_ahead)
        game_datetime = game_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return game_datetime
        
    except Exception as e:
        cprint(f"Error parsing game time '{game_time_str}': {e}", "red")
        return None

def read_game_times_from_sheets(service, spreadsheet_id):
    """Read existing game time data from all sheets in the spreadsheet"""
    try:
        # Get all sheet names
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_names = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
        
        all_games = []
        
        for sheet_name in sheet_names:
            try:
                # Read data from each sheet (columns A through E: Player Name, Position, Team, Opponent, Game Time)
                range_name = f"'{sheet_name}'!A:E"
                result = service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute()
                
                values = result.get('values', [])
                if len(values) <= 1:  # Skip if no data or only headers
                    continue
                
                # Skip header row and process data
                for row in values[1:]:
                    if len(row) >= 5:  # Ensure we have all required columns
                        player_name = row[0].strip()
                        position = row[1].strip()
                        team = row[2].strip()
                        opponent = row[3].strip()
                        game_time = row[4].strip()
                        
                        if player_name and team and opponent and game_time:
                            all_games.append({
                                'player_name': player_name,
                                'position': position,
                                'team': team,
                                'opponent': opponent,
                                'game_time': game_time,
                                'sheet_name': sheet_name
                            })
                            
            except Exception as e:
                cprint(f"Error reading sheet {sheet_name}: {e}", "red")
                continue
        
        return all_games
        
    except Exception as e:
        cprint(f"Error reading game times from sheets: {e}", "red")
        return []

def get_upcoming_games_from_sheets(service, spreadsheet_id, minutes_ahead=60):
    """Get games starting within the specified time window from Google Sheets data"""
    all_games = read_game_times_from_sheets(service, spreadsheet_id)
    
    upcoming_games = []
    current_time = datetime.now()
    target_time = current_time + timedelta(minutes=minutes_ahead)
    
    for game in all_games:
        game_time = parse_game_time(game.get('game_time', ''))
        if game_time and current_time <= game_time <= target_time:
            upcoming_games.append({
                'game_time': game_time,
                'game_time_str': game.get('game_time', ''),
                'team': game.get('team', ''),
                'opponent': game.get('opponent', ''),
                'player_name': game.get('player_name', ''),
                'position': game.get('position', ''),
                'sheet_name': game.get('sheet_name', '')
            })
    
    # Group by game to avoid duplicates
    games_dict = {}
    for game in upcoming_games:
        game_key = f"{game['team']} vs {game['opponent']} at {game['game_time_str']}"
        if game_key not in games_dict:
            games_dict[game_key] = {
                'game_time': game['game_time'],
                'game_time_str': game['game_time_str'],
                'team': game['team'],
                'opponent': game['opponent'],
                'players': [game]
            }
        else:
            games_dict[game_key]['players'].append(game)
    
    return list(games_dict.values())

def get_next_game_info(sheets_service, spreadsheet_id, trigger_window=60):
    """Get information about the next upcoming game"""
    try:
        # Read all games from sheets
        all_games = read_game_times_from_sheets(sheets_service, spreadsheet_id)
        
        if not all_games:
            return None
        
        current_time = datetime.now()
        future_games = []
        
        # Find all future games
        for game in all_games:
            game_time = parse_game_time(game.get('game_time', ''))
            if game_time and game_time > current_time:
                future_games.append({
                    'game_time': game_time,
                    'game_time_str': game.get('game_time', ''),
                    'team': game.get('team', ''),
                    'opponent': game.get('opponent', ''),
                    'player_name': game.get('player_name', ''),
                    'position': game.get('position', ''),
                    'sheet_name': game.get('sheet_name', '')
                })
        
        if not future_games:
            return None
        
        # Sort by game time and get the next one
        future_games.sort(key=lambda x: x['game_time'])
        next_game = future_games[0]
        
        # Group by game to get player count
        game_key = f"{next_game['team']} vs {next_game['opponent']} at {next_game['game_time_str']}"
        players_in_game = [g for g in future_games if f"{g['team']} vs {g['opponent']} at {g['game_time_str']}" == game_key]
        
        return {
            'game_time': next_game['game_time'],
            'game_time_str': next_game['game_time_str'],
            'team': next_game['team'],
            'opponent': next_game['opponent'],
            'player_count': len(players_in_game),
            'stat_types': len(set(p['sheet_name'] for p in players_in_game)),
            'trigger_time': next_game['game_time'] - timedelta(minutes=trigger_window)
        }
        
    except Exception as e:
        cprint(f"Error getting next game info: {e}", "red")
        return None

def monitor_games(sheets_service, spreadsheet_id, check_interval=120, trigger_window=60, scraping_callback=None):
    """Monitor for upcoming games using Google Sheets data (no browser until needed)"""
    cprint(f"\n🎯 Starting game monitoring using Google Sheets data...", "green", attrs=["bold"])
    cprint(f"   Check interval: {check_interval} seconds", "cyan")
    cprint(f"   Trigger window: {trigger_window} minutes before game start", "cyan")
    cprint(f"   Browser will only open when games are detected within {trigger_window} minutes", "cyan")
    cprint(f"   Press Ctrl+C to stop monitoring\n", "yellow")
    
    if not sheets_service:
        cprint("❌ Google Sheets service not available. Cannot monitor games.", "red")
        return
    
    last_triggered_games = set()
    
    # Get initial next game info
    next_game_info = get_next_game_info(sheets_service, spreadsheet_id, trigger_window)
    if next_game_info:
        time_until_trigger = next_game_info['trigger_time'] - datetime.now()
        minutes_until_trigger = int(time_until_trigger.total_seconds() / 60)
        hours_until_trigger = minutes_until_trigger // 60
        remaining_minutes = minutes_until_trigger % 60
        
        if minutes_until_trigger > 0:
            time_str = f"{hours_until_trigger}h {remaining_minutes}m" if hours_until_trigger > 0 else f"{remaining_minutes}m"
            cprint(f"📅 Next game: {next_game_info['team']} vs {next_game_info['opponent']} at {next_game_info['game_time_str']}", "cyan")
            cprint(f"🎯 Final scrape will begin in {time_str} ({next_game_info['player_count']} players across {next_game_info['stat_types']} stat types)", "yellow")
        else:
            cprint(f"📅 Next game: {next_game_info['team']} vs {next_game_info['opponent']} at {next_game_info['game_time_str']}", "cyan")
            cprint(f"🎯 Final scrape should begin soon! ({next_game_info['player_count']} players across {next_game_info['stat_types']} stat types)", "yellow")
    else:
        cprint("📅 No upcoming games found in Google Sheets", "yellow")
    
    print()
    
    try:
        while True:
            cprint(f"⏰ Checking for upcoming games from Google Sheets... ({datetime.now().strftime('%H:%M:%S')})", "cyan")
            
            try:
                # Read game times from existing Google Sheets data
                upcoming_games = get_upcoming_games_from_sheets(sheets_service, spreadsheet_id, trigger_window)
                
                if upcoming_games:
                    cprint(f"🎮 Found {len(upcoming_games)} upcoming game(s):", "green", attrs=["bold"])
                    for game in upcoming_games:
                        game_key = f"{game['team']} vs {game['opponent']} at {game['game_time_str']}"
                        time_until = game['game_time'] - datetime.now()
                        minutes_until = int(time_until.total_seconds() / 60)
                        
                        cprint(f"   • {game_key} (in {minutes_until} minutes)", "white")
                        cprint(f"     Players: {len(game['players'])} across {len(set(p['sheet_name'] for p in game['players']))} stat types", "cyan")
                        
                        # Trigger final scraping if we haven't already for this game
                        if game_key not in last_triggered_games:
                            cprint(f"🚀 Triggering FINAL scraping for {game['team']} vs {game['opponent']}...", "green", attrs=["bold"])
                            last_triggered_games.add(game_key)
                            
                            # Call the scraping callback if provided
                            if scraping_callback:
                                scraping_callback(game, sheets_service)
                            
                            # Update next game info after scraping
                            next_game_info = get_next_game_info(sheets_service, spreadsheet_id, trigger_window)
                else:
                    cprint("   No games starting within the next 60 minutes", "yellow")
                    
                    # Show next game info if no immediate games
                    if next_game_info:
                        time_until_trigger = next_game_info['trigger_time'] - datetime.now()
                        minutes_until_trigger = int(time_until_trigger.total_seconds() / 60)
                        
                        if minutes_until_trigger > 0:
                            hours_until_trigger = minutes_until_trigger // 60
                            remaining_minutes = minutes_until_trigger % 60
                            time_str = f"{hours_until_trigger}h {remaining_minutes}m" if hours_until_trigger > 0 else f"{remaining_minutes}m"
                            cprint(f"   📅 Next game: {next_game_info['team']} vs {next_game_info['opponent']} at {next_game_info['game_time_str']}", "cyan")
                            cprint(f"   🎯 Final scrape will begin in {time_str}", "yellow")
                        else:
                            cprint(f"   📅 Next game: {next_game_info['team']} vs {next_game_info['opponent']} at {next_game_info['game_time_str']}", "cyan")
                            cprint(f"   🎯 Final scrape should begin soon!", "yellow")
                
            except Exception as e:
                cprint(f"   Error during monitoring check: {e}", "red")
            
            # Wait before next check
            cprint(f"   Next check in {check_interval} seconds...\n", "cyan")
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        cprint(f"\n🛑 Game monitoring stopped by user", "yellow", attrs=["bold"])
    except Exception as e:
        cprint(f"\n❌ Error in monitoring: {e}", "red")

def run_monitoring_session(sheets_service, spreadsheet_id, scraping_callback=None):
    """Run the monitoring mode session"""
    cprint(f"\n🎯 Starting Monitoring Mode...", "green", attrs=["bold"])
    cprint("This will continuously monitor for upcoming games and auto-scrape when games are within 60 minutes.", "cyan")
    cprint("Browser will only open when games are detected within 60 minutes.", "cyan")
    
    if not sheets_service:
        cprint("❌ Google Sheets setup failed. Cannot run monitoring mode.", "red")
        return
    
    # Start monitoring (no browser until needed)
    monitor_games(sheets_service, spreadsheet_id, scraping_callback=scraping_callback)
