#!/usr/bin/env python3

from datetime import datetime, timedelta
import re
import time
from typing import Dict, List, Optional, Any
from termcolor import cprint
import nfl_data_py as nfl
import pandas as pd
import pytz

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

def get_nfl_schedule_2025():
    """Get NFL schedule using nfl-data-py"""
    try:
        # Try multiple years to find available data
        years_to_try = [2025, 2024, 2023]
        schedule_df = None
        
        for year in years_to_try:
            try:
                schedule_df = nfl.import_schedules([year])
                if not schedule_df.empty:
                    break
            except Exception as e:
                continue
        
        if schedule_df is None or schedule_df.empty:
            cprint("❌ No NFL schedule data found for any recent year", "red")
            return []
        
        all_games = []
        current_time = datetime.now(pytz.timezone('US/Central'))
        
        upcoming_count = 0
        for _, game in schedule_df.iterrows():
            try:
                # Skip games that don't have complete data
                # nfl-data-py uses different column names
                game_date_col = 'gameday' if 'gameday' in schedule_df.columns else 'game_date'
                home_team_col = 'home_team' if 'home_team' in schedule_df.columns else 'home'
                away_team_col = 'away_team' if 'away_team' in schedule_df.columns else 'away'
                
                if pd.isna(game.get(game_date_col)) or pd.isna(game.get(home_team_col)) or pd.isna(game.get(away_team_col)):
                    continue
                
                # Parse game date and time
                # Combine gameday and gametime if both are available
                if 'gametime' in schedule_df.columns and not pd.isna(game.get('gametime')):
                    # Combine date and time
                    game_date_str = str(game[game_date_col])
                    game_time_str_raw = str(game['gametime'])
                    # Handle different time formats
                    if ':' in game_time_str_raw:
                        # Format like "20:00" or "8:00 PM"
                        # NFL times are in Eastern Time, so we need to parse as ET
                        combined_datetime = f"{game_date_str} {game_time_str_raw}"
                        game_datetime = pd.to_datetime(combined_datetime)
                        
                        # Convert from Eastern Time to local time
                        # Create timezone-aware datetime in Eastern Time
                        et_tz = pytz.timezone('US/Eastern')
                        game_datetime_et = et_tz.localize(game_datetime)
                        
                        # Convert to local timezone
                        local_tz = pytz.timezone('US/Central')  # CDT
                        game_datetime = game_datetime_et.astimezone(local_tz)
                    else:
                        # Just use the date
                        game_datetime = pd.to_datetime(game[game_date_col])
                else:
                    # Just use the date
                    game_datetime = pd.to_datetime(game[game_date_col])
                
                # Skip past games
                if game_datetime < current_time:
                    continue
                
                upcoming_count += 1
                
                # Get team names and abbreviations
                home_team = game[home_team_col]
                away_team = game[away_team_col]
                
                # Format game time for display
                game_time_str = game_datetime.strftime('%a %I:%M%p').lower()
                
                
                # Add single game representation
                all_games.append({
                    'home_team': home_team,
                    'away_team': away_team,
                    'game_date': game_datetime,
                    'game_time_str': game_time_str,
                    'season': game.get('season', 'Unknown'),
                    'game_type': game.get('game_type', 'Unknown'),
                    'week': game.get('week', 'Unknown'),
                    'gameday': game.get('gameday', 'Unknown'),
                    'weekday': game.get('weekday', 'Unknown'),
                    'gametime': game.get('gametime', 'Unknown')
                })
                
            except Exception as e:
                cprint(f"Error processing game: {e}", "red")
                continue
        
        return all_games
        
    except Exception as e:
        cprint(f"Error fetching NFL schedule: {e}", "red")
        return []

def get_next_nfl_games():
    """Get all upcoming NFL games starting at the next game time"""
    try:
        all_games = get_nfl_schedule_2025()
        
        if not all_games:
            return []
        
        current_time = datetime.now(pytz.timezone('US/Central'))
        
        # Find all upcoming games
        upcoming_games = []
        for game in all_games:
            game_date = game['game_date']
            
            # Skip past games
            if game_date <= current_time:
                continue
            
            # Calculate time difference
            time_diff = (game_date - current_time).total_seconds() / 60  # minutes
            
            upcoming_games.append({
                'game_time': game_date,
                'game_time_str': game['game_time_str'],
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'season': game.get('season', 'Unknown'),
                'game_type': game.get('game_type', 'Unknown'),
                'week': game.get('week', 'Unknown'),
                'gameday': game.get('gameday', 'Unknown'),
                'weekday': game.get('weekday', 'Unknown'),
                'gametime': game.get('gametime', 'Unknown'),
                'minutes_until': int(time_diff)
            })
        
        # Sort by game time
        upcoming_games.sort(key=lambda x: x['game_time'])
        
        # Find the next game time
        if not upcoming_games:
            return []
        
        next_game_time = upcoming_games[0]['game_time']
        
        # Return all games at the next game time
        next_games = [game for game in upcoming_games if game['game_time'] == next_game_time]
        
        return next_games
        
    except Exception as e:
        cprint(f"Error getting next NFL games: {e}", "red")
        return []

def get_next_upcoming_games_after_current(current_games):
    """Get the next set of upcoming games after the current games being monitored"""
    try:
        if not current_games:
            return get_next_nfl_games()
        
        all_games = get_nfl_schedule_2025()
        
        if not all_games:
            return []
        
        current_time = datetime.now(pytz.timezone('US/Central'))
        current_game_time = current_games[0]['game_time']
        
        # Find all upcoming games after the current game time
        upcoming_games = []
        for game in all_games:
            game_date = game['game_date']
            
            # Skip past games and current games
            if game_date <= current_game_time:
                continue
            
            # Calculate time difference
            time_diff = (game_date - current_time).total_seconds() / 60  # minutes
            
            upcoming_games.append({
                'game_time': game_date,
                'game_time_str': game['game_time_str'],
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'season': game.get('season', 'Unknown'),
                'game_type': game.get('game_type', 'Unknown'),
                'week': game.get('week', 'Unknown'),
                'gameday': game.get('gameday', 'Unknown'),
                'weekday': game.get('weekday', 'Unknown'),
                'gametime': game.get('gametime', 'Unknown'),
                'minutes_until': int(time_diff)
            })
        
        # Sort by game time
        upcoming_games.sort(key=lambda x: x['game_time'])
        
        # Find the next game time after current games
        if not upcoming_games:
            return []
        
        next_game_time = upcoming_games[0]['game_time']
        
        # Return all games at the next game time
        next_games = [game for game in upcoming_games if game['game_time'] == next_game_time]
        
        return next_games
        
    except Exception as e:
        cprint(f"Error getting next upcoming games: {e}", "red")
        return []

def is_game_within_trigger_window(game, trigger_window=60):
    """Check if a game is within the trigger window"""
    if not game:
        return False
    
    current_time = datetime.now(pytz.timezone('US/Central'))
    game_time = game['game_time']
    time_diff_minutes = (game_time - current_time).total_seconds() / 60
    
    return 0 <= time_diff_minutes <= trigger_window

def monitor_nfl_games(check_interval=600, trigger_window=60, scraping_callback=None, auto_continue=True):
    """Monitor for the next upcoming NFL game and trigger PrizePicks scraping when within trigger window"""
    cprint(f"\n🎯 Starting NFL Game Monitoring...", "green", attrs=["bold"])
    cprint(f"   Check interval: {check_interval // 60} minutes ({check_interval} seconds)", "cyan")
    cprint(f"   Trigger window: {trigger_window} minutes before game time", "cyan")
    cprint(f"   Data source: nfl-data-py (NFL official data)", "cyan")
    cprint(f"   Auto-continue: {'Enabled' if auto_continue else 'Disabled'}", "cyan")
    cprint(f"   Press Ctrl+C to stop monitoring\n", "yellow")
    
    last_triggered_games = set()
    current_monitoring_games = None
    
    try:
        while True:
            cprint(f"⏰ Checking for next upcoming NFL game... ({datetime.now().strftime('%H:%M:%S')})", "cyan")
            
            try:
                # Get games to monitor (either next games or continue with current)
                if current_monitoring_games is None:
                    next_games = get_next_nfl_games()
                else:
                    # Check if current games are still upcoming
                    current_time = datetime.now(pytz.timezone('US/Central'))
                    if current_monitoring_games and current_monitoring_games[0]['game_time'] > current_time:
                        next_games = current_monitoring_games
                    else:
                        # Current games have passed, get next set
                        next_games = get_next_upcoming_games_after_current(current_monitoring_games)
                        current_monitoring_games = next_games
                
                if next_games:
                    # Display all games at the next time slot
                    if len(next_games) == 1:
                        game = next_games[0]
                        game_key = f"{game['away_team']} vs {game['home_team']} at {game['game_time_str']}"
                        cprint(f"🏈 Found: {game_key}", "green", attrs=["bold"])
                    else:
                        cprint(f"🏈 Found {len(next_games)} games at {next_games[0]['game_time_str']}:", "green", attrs=["bold"])
                        for i, game in enumerate(next_games, 1):
                            game_key = f"{game['away_team']} vs {game['home_team']}"
                            cprint(f"   {i}. {game_key}", "green")
                    
                    # Show common game details
                    first_game = next_games[0]
                    minutes_until = first_game['minutes_until']
                    cprint(f"     Season: {first_game.get('season', 'Unknown')} | Week: {first_game.get('week', 'Unknown')} | Type: {first_game.get('game_type', 'Unknown')}", "cyan")
                    cprint(f"     Game Day: {first_game.get('gameday', 'Unknown')} | Weekday: {first_game.get('weekday', 'Unknown')} | Time: {first_game.get('gametime', 'Unknown')}", "cyan")
                    
                    # Check if games are within trigger window
                    if is_game_within_trigger_window(first_game, trigger_window):
                        cprint(f"🚀 Games start in {minutes_until} minutes - TRIGGERING PrizePicks scraping!", "green", attrs=["bold"])
                        cprint(f"   Scraper will find players for all {len(next_games)} game(s) at this time slot", "cyan")
                        cprint(f"   Teams: {', '.join(sorted(set([game['home_team'] for game in next_games] + [game['away_team'] for game in next_games])))}", "cyan")
                        
                        # Trigger scraping once for all games at this time
                        if first_game['game_time'] not in last_triggered_games:
                            last_triggered_games.add(first_game['game_time'])
                            
                            # Call the scraping callback if provided
                            if scraping_callback:
                                scrape_success = scraping_callback(next_games, None)  # Pass all games at this time slot
                                
                                # If auto-continue is enabled and scraping was successful, identify next games to monitor
                                if auto_continue and scrape_success:
                                    cprint(f"✅ Scraping completed successfully! Identifying next games to monitor...", "green", attrs=["bold"])
                                    # Get the next set of games after current ones
                                    next_upcoming = get_next_upcoming_games_after_current(next_games)
                                    if next_upcoming:
                                        current_monitoring_games = next_upcoming
                                        cprint(f"🔄 Now monitoring next games: {next_upcoming[0]['away_team']} vs {next_upcoming[0]['home_team']} at {next_upcoming[0]['game_time_str']}", "cyan")
                                        cprint(f"   Will wait until {next_upcoming[0]['minutes_until']} minutes before game time to scrape", "cyan")
                                    else:
                                        cprint(f"ℹ️  No more upcoming games found. Monitoring will continue for any new games.", "yellow")
                                        current_monitoring_games = None
                        else:
                            cprint(f"   ⚠️  Already triggered scraping for this time slot", "yellow")
                    else:
                        hours_until = minutes_until / 60
                        if hours_until < 24:
                            cprint(f"⏳ Waiting until closer to game time to scrape: {hours_until:.1f} hours remaining", "yellow")
                        else:
                            days_until = hours_until / 24
                            cprint(f"⏳ Waiting until closer to game time to scrape: {days_until:.1f} days remaining", "yellow")
                else:
                    cprint("   No upcoming NFL games found", "yellow")
                    current_monitoring_games = None
                
            except Exception as e:
                cprint(f"   Error during monitoring check: {e}", "red")
            
            # Wait before next check
            minutes = check_interval // 60
            seconds = check_interval % 60
            if minutes > 0:
                time_str = f"{minutes} minutes" if seconds == 0 else f"{minutes} minutes {seconds} seconds"
            else:
                time_str = f"{check_interval} seconds"
            cprint(f"   Next check in {time_str}...\n", "cyan")
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        cprint(f"\n🛑 NFL game monitoring stopped by user", "yellow", attrs=["bold"])
    except Exception as e:
        cprint(f"\n❌ Error in monitoring: {e}", "red")

def show_upcoming_games_schedule():
    """Show today's NFL games schedule"""
    cprint(f"\n📅 Today's NFL Games Schedule", "green", attrs=["bold"])
    cprint("="*60, "cyan")
    
    try:
        all_games = get_nfl_schedule_2025()
        if not all_games:
            cprint("No upcoming games found", "yellow")
            return
        
        current_time = datetime.now(pytz.timezone('US/Central'))
        today = current_time.date()
        
        # Filter games for today only
        today_games = []
        for game in all_games:
            game_date = game['game_date']
            if game_date.date() == today and game_date > current_time:
                # Calculate minutes until game
                time_diff = (game_date - current_time).total_seconds() / 60
                game['minutes_until'] = int(time_diff)
                today_games.append(game)
        
        if not today_games:
            cprint("No games scheduled for today", "yellow")
            return
        
        # Sort games by time
        today_games.sort(key=lambda x: x['game_date'])
        
        # Display today's games
        date_str = today.strftime('%A, %B %d, %Y')
        cprint(f"\n📅 {date_str}", "yellow", attrs=["bold"])
        
        for game in today_games:
            time_str = game['game_time_str']
            teams = f"{game['away_team']} vs {game['home_team']}"
            minutes_until = game['minutes_until']
            
            if minutes_until < 60:
                time_info = f"{minutes_until} min"
            elif minutes_until < 1440:  # Less than 24 hours
                hours = minutes_until // 60
                time_info = f"{hours}h {minutes_until % 60}m"
            else:
                days = minutes_until // 1440
                time_info = f"{days}d {minutes_until % 1440 // 60}h"
            
            cprint(f"   {time_str:>8} | {teams:<30} | {time_info:>8}", "white")
        
        cprint(f"\n💡 The monitoring system will automatically scrape games within the trigger window", "cyan")
        cprint(f"   and then identify and begin monitoring the next set of games!", "cyan")
        
    except Exception as e:
        cprint(f"Error showing schedule: {e}", "red")

def run_sequential_scraping_callback(games_info, sheets_service=None):
    """Run both PrizePicks and Underdog scrapers sequentially for monitoring (one after the other)"""
    cprint(f"\n🚀 Starting SEQUENTIAL SCRAPING SESSION...", "green", attrs=["bold"])
    cprint(f"   Games: {len(games_info)} game(s) at {games_info[0]['game_time_str']}", "cyan")
    cprint(f"   Teams: {', '.join(sorted(set([game['home_team'] for game in games_info] + [game['away_team'] for game in games_info])))}", "cyan")
    cprint(f"   Sequence: PrizePicks → Underdog Fantasy (one after the other)", "yellow")
    
    overall_success = True
    
    # Step 1: Run PrizePicks scraper
    cprint(f"\n{'='*60}", "cyan")
    cprint("STEP 1: PRIZEPICKS SCRAPING", "yellow", attrs=["bold"])
    cprint(f"{'='*60}", "cyan")
    
    try:
        import visit_prizepicks
        prizepicks_success = visit_prizepicks.run_monitoring_scraping(games_info, sheets_service)
        
        if prizepicks_success:
            cprint("✅ PrizePicks scraping completed successfully!", "green", attrs=["bold"])
        else:
            cprint("❌ PrizePicks scraping failed!", "red", attrs=["bold"])
            overall_success = False
            
    except Exception as e:
        cprint(f"❌ Error running PrizePicks scraper: {e}", "red")
        overall_success = False
    
    # Step 2: Run Underdog scraper
    cprint(f"\n{'='*60}", "cyan")
    cprint("STEP 2: UNDERDOG FANTASY SCRAPING", "yellow", attrs=["bold"])
    cprint(f"{'='*60}", "cyan")
    
    try:
        import visit_underdog
        underdog_success = visit_underdog.run_monitoring_scraping(games_info, sheets_service)
        
        if underdog_success:
            cprint("✅ Underdog Fantasy scraping completed successfully!", "green", attrs=["bold"])
        else:
            cprint("❌ Underdog Fantasy scraping failed!", "red", attrs=["bold"])
            overall_success = False
            
    except Exception as e:
        cprint(f"❌ Error running Underdog scraper: {e}", "red")
        overall_success = False
    
    # Final summary
    cprint(f"\n{'='*60}", "cyan")
    cprint("SEQUENTIAL SCRAPING SESSION COMPLETE", "green" if overall_success else "red", attrs=["bold"])
    cprint(f"{'='*60}", "cyan")
    
    if overall_success:
        cprint("🎉 Both scrapers completed successfully (one after the other)!", "green", attrs=["bold"])
    else:
        cprint("⚠️  One or more scrapers encountered issues", "yellow", attrs=["bold"])
    
    return overall_success

def run_monitoring_session(scraping_callback=None, trigger_window_hours=1, auto_continue=True, use_sequential_scraping=True):
    """Run the monitoring mode session"""
    cprint(f"\n🎯 Starting NFL Game Monitoring Mode...", "green", attrs=["bold"])
    
    if use_sequential_scraping:
        cprint("This will monitor NFL official data for upcoming games and trigger BOTH PrizePicks and Underdog scraping.", "cyan")
        cprint("🔄 Scraping sequence: PrizePicks → Underdog Fantasy (one after the other)", "yellow")
    else:
        cprint("This will monitor NFL official data for upcoming games and trigger PrizePicks scraping.", "cyan")
    
    cprint(f"Trigger window: {trigger_window_hours} hours before game time", "cyan")
    cprint(f"Auto-continue: {'Enabled' if auto_continue else 'Disabled'} - Will automatically identify and monitor next games after successful scrape", "cyan")
    
    # Show upcoming schedule
    show_upcoming_games_schedule()
    
    # Set up the scraping callback
    if scraping_callback is None:
        if use_sequential_scraping:
            scraping_callback = run_sequential_scraping_callback
            cprint("✅ Using sequential scraping callback (PrizePicks → Underdog)", "green")
        else:
            try:
                import visit_prizepicks
                scraping_callback = visit_prizepicks.run_monitoring_scraping
                cprint("✅ Using PrizePicks monitoring scraper as default callback", "green")
            except ImportError as e:
                cprint(f"❌ Could not import PrizePicks scraper: {e}", "red")
                cprint("⚠️  Monitoring will continue but no scraping will occur", "yellow")
    
    # Start monitoring with custom trigger window and auto-continue
    trigger_window_minutes = trigger_window_hours * 60
    monitor_nfl_games(trigger_window=trigger_window_minutes, scraping_callback=scraping_callback, auto_continue=auto_continue)