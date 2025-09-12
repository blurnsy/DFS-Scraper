#!/usr/bin/env python3

from google.oauth2 import service_account
from googleapiclient.discovery import build
import nfl_data_py as nfl
import pandas as pd
from datetime import datetime, timedelta
import re
import time
from typing import Dict, List, Optional, Any
from termcolor import cprint
import pytz

class NFLStatsFetcher:
    def __init__(self, spreadsheet_id: str, service_account_file: str = 'service-account-key.json'):
        self.spreadsheet_id = spreadsheet_id
        self.service_account_file = service_account_file
        self.sheets_service = self._setup_google_sheets()
        
        # Team abbreviation mapping for nfl_data_py
        self.team_mapping = {
            'ARI': 'ARI', 'ATL': 'ATL', 'BAL': 'BAL', 'BUF': 'BUF', 'CAR': 'CAR',
            'CHI': 'CHI', 'CIN': 'CIN', 'CLE': 'CLE', 'DAL': 'DAL', 'DEN': 'DEN',
            'DET': 'DET', 'GB': 'GB', 'HOU': 'HOU', 'IND': 'IND', 'JAC': 'JAX',
            'KC': 'KC', 'LV': 'LV', 'LAC': 'LAC', 'LAR': 'LAR', 'MIA': 'MIA',
            'MIN': 'MIN', 'NE': 'NE', 'NO': 'NO', 'NYG': 'NYG', 'NYJ': 'NYJ',
            'PHI': 'PHI', 'PIT': 'PIT', 'SF': 'SF', 'SEA': 'SEA', 'TB': 'TB',
            'TEN': 'TEN', 'WAS': 'WAS'
        }
        
        # Stat type mapping to nfl_data_py columns
        self.stat_mapping = {
            'Pass Yards': 'passing_yards',
            'Rush Yards': 'rushing_yards', 
            'Pass TDs': 'passing_tds',
            'Receiving Yards': 'receiving_yards',
            'FG Made': 'field_goals_made',  # Will calculate from PBP
            'Receptions': 'receptions',
            'Rush+Rec Yds': 'rushing_yards',  # Will combine with receiving
            'Rush+Rec TDs': 'rushing_tds',  # Will combine with receiving TDs
            'Fantasy Score': 'fantasy_points',  # Use built-in fantasy points
            'Pass Attempts': 'attempts',
            'Rec Targets': 'targets',
            'Sacks': 'sacks',  # Will calculate from PBP
            'Pass Completions': 'completions',
            'INT': 'interceptions',
            'Pass+Rush Yds': 'passing_yards',  # Will combine with rushing
            'Rush Attempts': 'carries',
            'Kicking Points': 'kicking_points',  # Will calculate from PBP
            'Tackles+Ast': 'tackles'  # Will calculate from PBP
        }

    def _setup_google_sheets(self):
        try:
            scopes = ['https://www.googleapis.com/auth/spreadsheets']
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=scopes)
            return build('sheets', 'v4', credentials=credentials)
        except Exception as e:
            cprint(f"Error setting up Google Sheets: {e}", "red")
            return None

    def read_sheet_data(self, sheet_name: str) -> List[Dict[str, Any]]:
        try:
            range_name = f"'{sheet_name}'!A:I"
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if len(values) <= 1:
                return []
            
            players = []
            for i, row in enumerate(values[1:], start=2):  # Skip header, start from row 2
                if len(row) >= 5:
                    players.append({
                        'row_index': i,
                        'player_name': row[0].strip(),
                        'position': row[1].strip(),
                        'team': row[2].strip(),
                        'opponent': row[3].strip(),
                        'game_time': row[4].strip(),
                        'line': row[5] if len(row) > 5 else '',
                        'payout_type': row[6] if len(row) > 6 else 'Standard',
                        'actual': row[7] if len(row) > 7 else '',
                        'over_under': row[8] if len(row) > 8 else '',
                        'stat_type': sheet_name.replace(' Plus ', '+')
                    })
            
            return players
        except Exception as e:
            cprint(f"Error reading sheet {sheet_name}: {e}", "red")
            return []

    def get_all_sheets(self) -> List[str]:
        try:
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id).execute()
            return [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
        except Exception as e:
            cprint(f"Error getting sheet names: {e}", "red")
            return []

    def parse_game_date(self, game_time_str: str) -> Optional[datetime]:
        try:
            
            # Handle countdown timers - these are always today's games
            if 'm' in game_time_str and 's' in game_time_str and any(char.isdigit() for char in game_time_str):
                return datetime.now().date()
            
            game_time_clean = game_time_str.strip()
            
            # Handle format like "Thu 07:15PM" (day + time)
            match = re.match(r'(\w{3})\s+(\d{1,2}):(\d{2})([ap]m)', game_time_clean, re.IGNORECASE)
            if match:
                day_abbr, hour, minute, ampm = match.groups()
                hour = int(hour)
                minute = int(minute)
                
                if ampm.lower() == 'pm' and hour != 12:
                    hour += 12
                elif ampm.lower() == 'am' and hour == 12:
                    hour = 0
                
                day_map = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
                day_num = day_map.get(day_abbr.lower())
                if day_num is None:
                    cprint(f"Unknown day abbreviation: {day_abbr}", "red")
                    return None
                
                today = datetime.now()
                days_ahead = (day_num - today.weekday()) % 7
                if days_ahead == 0 and (hour < today.hour or (hour == today.hour and minute <= today.minute)):
                    days_ahead = 7
                
                game_date = today + timedelta(days=days_ahead)
                return game_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Handle format like "7:15PM CDT" (time + timezone, no day)
            match = re.match(r'(\d{1,2}):(\d{2})([ap]m)', game_time_clean, re.IGNORECASE)
            if match:
                hour, minute, ampm = match.groups()
                hour = int(hour)
                minute = int(minute)
                
                if ampm.lower() == 'pm' and hour != 12:
                    hour += 12
                elif ampm.lower() == 'am' and hour == 12:
                    hour = 0
                
                # For time-only format, assume it's today's game
                today = datetime.now()
                game_date = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If the time has already passed today, assume it's tomorrow
                if game_date < today:
                    game_date += timedelta(days=1)
                
                return game_date
            
            cprint(f"No match found for game time: '{game_time_str}'", "red")
            return None
            
        except Exception as e:
            cprint(f"Error parsing game time '{game_time_str}': {e}", "red")
            return None

    def get_nfl_game_data(self, year: int = None) -> pd.DataFrame:
        """Get NFL game data for the specified year"""
        if year is None:
            year = datetime.now().year
        
        try:
            # Try multiple years to find available data
            years_to_try = [year, year - 1, year + 1]
            game_data = None
            
            for test_year in years_to_try:
                try:
                    game_data = nfl.import_schedules([test_year])
                    if not game_data.empty:
                        cprint(f"Found NFL data for {test_year}", "green")
                        break
                except Exception as e:
                    cprint(f"No data for {test_year}: {e}", "yellow")
                    continue
            
            if game_data is None or game_data.empty:
                cprint("No NFL schedule data found", "red")
                return pd.DataFrame()
            
            return game_data
            
        except Exception as e:
            cprint(f"Error fetching NFL game data: {e}", "red")
            return pd.DataFrame()

    def get_player_stats_data(self, year: int = None) -> pd.DataFrame:
        """Get player stats data for the specified year"""
        if year is None:
            year = datetime.now().year
        
        try:
            # Try multiple years to find available data
            years_to_try = [year, year - 1, year + 1]
            
            for test_year in years_to_try:
                try:
                    # First try weekly data (preferred)
                    stats_data = nfl.import_weekly_data([test_year])
                    
                    if not stats_data.empty:
                        cprint(f"Found weekly player stats data for {test_year} ({len(stats_data)} records)", "green")
                        return stats_data
                        
                except Exception as e:
                    cprint(f"No weekly data for {test_year}: {e}", "yellow")
                    
                    # If weekly data fails, try play-by-play data
                    try:
                        cprint(f"Trying play-by-play data for {test_year}...", "cyan")
                        pbp_data = nfl.import_pbp_data([test_year])
                        
                        if not pbp_data.empty:
                            cprint(f"Found play-by-play data for {test_year} ({len(pbp_data)} plays)", "green")
                            # Convert play-by-play to weekly stats
                            weekly_stats = self._convert_pbp_to_weekly_stats(pbp_data)
                            if not weekly_stats.empty:
                                cprint(f"Converted to weekly stats: {len(weekly_stats)} player records", "green")
                                return weekly_stats
                        
                    except Exception as pbp_error:
                        cprint(f"No play-by-play data for {test_year}: {pbp_error}", "yellow")
                        continue
            
            return pd.DataFrame()
            
        except Exception as e:
            cprint(f"Error fetching player stats data: {e}", "red")
            return pd.DataFrame()

    def _convert_pbp_to_weekly_stats(self, pbp_data: pd.DataFrame) -> pd.DataFrame:
        """Convert play-by-play data to weekly player stats"""
        try:
            if pbp_data.empty:
                return pd.DataFrame()
            
            # Group by player and week to calculate stats
            weekly_stats = []
            
            # Get unique players and weeks
            players = set()
            weeks = set()
            
            # Collect all unique players from various play types
            for col in ['passer_player_name', 'rusher_player_name', 'receiver_player_name', 'kicker_player_name',
                       'sack_player_name', 'solo_tackle_1_player_name', 'solo_tackle_2_player_name',
                       'assist_tackle_1_player_name', 'assist_tackle_2_player_name', 'assist_tackle_3_player_name', 'assist_tackle_4_player_name']:
                if col in pbp_data.columns:
                    players.update(pbp_data[col].dropna().unique())
            
            weeks = pbp_data['week'].unique()
            
            for player in players:
                if pd.isna(player) or player == '':
                    continue
                    
                for week in weeks:
                    if pd.isna(week):
                        continue
                    
                    # Filter plays for this player in this week
                    player_plays = pbp_data[
                        ((pbp_data['passer_player_name'] == player) |
                         (pbp_data['rusher_player_name'] == player) |
                         (pbp_data['receiver_player_name'] == player) |
                         (pbp_data['kicker_player_name'] == player) |
                         (pbp_data['sack_player_name'] == player) |
                         (pbp_data['solo_tackle_1_player_name'] == player) |
                         (pbp_data['solo_tackle_2_player_name'] == player) |
                         (pbp_data['assist_tackle_1_player_name'] == player) |
                         (pbp_data['assist_tackle_2_player_name'] == player) |
                         (pbp_data['assist_tackle_3_player_name'] == player) |
                         (pbp_data['assist_tackle_4_player_name'] == player)) &
                        (pbp_data['week'] == week)
                    ]
                    
                    if player_plays.empty:
                        continue
                    
                    # Calculate stats
                    passing_yards = player_plays[player_plays['passer_player_name'] == player]['passing_yards'].sum()
                    passing_tds = player_plays[player_plays['passer_player_name'] == player]['pass_touchdown'].sum()
                    passing_attempts = len(player_plays[player_plays['passer_player_name'] == player])
                    passing_completions = player_plays[player_plays['passer_player_name'] == player]['complete_pass'].sum()
                    interceptions = player_plays[player_plays['passer_player_name'] == player]['interception'].sum()
                    
                    rushing_yards = player_plays[player_plays['rusher_player_name'] == player]['rushing_yards'].sum()
                    rushing_tds = player_plays[player_plays['rusher_player_name'] == player]['rush_touchdown'].sum()
                    rushing_attempts = len(player_plays[player_plays['rusher_player_name'] == player])
                    
                    receiving_yards = player_plays[player_plays['receiver_player_name'] == player]['receiving_yards'].sum()
                    receiving_tds = player_plays[player_plays['receiver_player_name'] == player]['pass_touchdown'].sum()
                    receptions = player_plays[player_plays['receiver_player_name'] == player]['complete_pass'].sum()
                    targets = len(player_plays[player_plays['receiver_player_name'] == player])
                    
                    # Calculate defensive stats
                    sacks = len(player_plays[player_plays['sack_player_name'] == player])
                    solo_tackles = len(player_plays[player_plays['solo_tackle_1_player_name'] == player]) + len(player_plays[player_plays['solo_tackle_2_player_name'] == player])
                    assist_tackles = (len(player_plays[player_plays['assist_tackle_1_player_name'] == player]) + 
                                    len(player_plays[player_plays['assist_tackle_2_player_name'] == player]) +
                                    len(player_plays[player_plays['assist_tackle_3_player_name'] == player]) +
                                    len(player_plays[player_plays['assist_tackle_4_player_name'] == player]))
                    tackles_plus_assists = solo_tackles + assist_tackles
                    
                    # Calculate kicking stats
                    field_goals_made = len(player_plays[(player_plays['kicker_player_name'] == player) & 
                                                       (player_plays['field_goal_attempt'] == 1) & 
                                                       (player_plays['field_goal_result'] == 'made')])
                    field_goals_attempted = len(player_plays[(player_plays['kicker_player_name'] == player) & 
                                                            (player_plays['field_goal_attempt'] == 1)])
                    
                    # Calculate kicking points (3 points per field goal made)
                    kicking_points = field_goals_made * 3
                    
                    # Get team from the first play
                    first_play = player_plays.iloc[0]
                    
                    # For defensive players (sacks, tackles), assign to the defensive team
                    if (player_plays['sack_player_name'] == player).any() or \
                       (player_plays['solo_tackle_1_player_name'] == player).any() or \
                       (player_plays['solo_tackle_2_player_name'] == player).any() or \
                       (player_plays['assist_tackle_1_player_name'] == player).any() or \
                       (player_plays['assist_tackle_2_player_name'] == player).any() or \
                       (player_plays['assist_tackle_3_player_name'] == player).any() or \
                       (player_plays['assist_tackle_4_player_name'] == player).any():
                        # For defensive players, use the defteam (defensive team)
                        team = first_play['defteam']
                    elif (player_plays['kicker_player_name'] == player).any():
                        # For kickers, prioritize field goal and extra point attempts to determine their team
                        fg_xp_plays = player_plays[
                            (player_plays['kicker_player_name'] == player) & 
                            ((player_plays['field_goal_attempt'] == 1) | (player_plays['extra_point_attempt'] == 1))
                        ]
                        if not fg_xp_plays.empty:
                            team = fg_xp_plays.iloc[0]['posteam']
                        else:
                            # Fallback to first play's posteam
                            team = first_play['posteam'] if first_play['posteam'] == first_play['home_team'] or first_play['posteam'] == first_play['away_team'] else first_play['home_team']
                    else:
                        # For offensive players, use the posteam
                        team = first_play['posteam'] if first_play['posteam'] == first_play['home_team'] or first_play['posteam'] == first_play['away_team'] else first_play['home_team']
                    
                    # Calculate fantasy points (basic scoring)
                    fantasy_points = (
                        (passing_yards / 25) + (passing_tds * 4) + (rushing_yards / 10) + (rushing_tds * 6) +
                        (receiving_yards / 10) + (receiving_tds * 6) + receptions - (interceptions * 2)
                    )
                    
                    weekly_stats.append({
                        'player_name': player,
                        'recent_team': team,
                        'week': int(week),
                        'season': int(first_play['season']),
                        'passing_yards': float(passing_yards) if pd.notna(passing_yards) else 0.0,
                        'passing_tds': int(passing_tds) if pd.notna(passing_tds) else 0,
                        'attempts': int(passing_attempts) if pd.notna(passing_attempts) else 0,
                        'completions': int(passing_completions) if pd.notna(passing_completions) else 0,
                        'interceptions': int(interceptions) if pd.notna(interceptions) else 0,
                        'rushing_yards': float(rushing_yards) if pd.notna(rushing_yards) else 0.0,
                        'rushing_tds': int(rushing_tds) if pd.notna(rushing_tds) else 0,
                        'carries': int(rushing_attempts) if pd.notna(rushing_attempts) else 0,
                        'receiving_yards': float(receiving_yards) if pd.notna(receiving_yards) else 0.0,
                        'receiving_tds': int(receiving_tds) if pd.notna(receiving_tds) else 0,
                        'receptions': int(receptions) if pd.notna(receptions) else 0,
                        'targets': int(targets) if pd.notna(targets) else 0,
                        'fantasy_points': float(fantasy_points) if pd.notna(fantasy_points) else 0.0,
                        'sacks': int(sacks),
                        'tackles': int(solo_tackles),
                        'assists': int(assist_tackles),
                        'field_goals_made': int(field_goals_made),
                        'field_goals_attempted': int(field_goals_attempted),
                        'kicking_points': int(kicking_points),
                        'special_teams_tds': 0.0  # Not available in basic PBP
                    })
            
            return pd.DataFrame(weekly_stats)
            
        except Exception as e:
            cprint(f"Error converting PBP to weekly stats: {e}", "red")
            return pd.DataFrame()

    def find_game_week(self, team: str, opponent: str, game_date) -> Optional[int]:
        """Find the week number for a specific game"""
        try:
            # Handle both date and datetime objects
            if isinstance(game_date, datetime):
                year = game_date.year
            else:
                year = game_date.year if hasattr(game_date, 'year') else datetime.now().year
            
            game_data = self.get_nfl_game_data(year)
            if game_data.empty:
                return None
            
            team_code = self.team_mapping.get(team)
            opponent_code = self.team_mapping.get(opponent)
            
            if not team_code or not opponent_code:
                return None
            
            # Look for games where either team is home or away
            game_match = game_data[
                ((game_data['home_team'] == team_code) & (game_data['away_team'] == opponent_code)) |
                ((game_data['home_team'] == opponent_code) & (game_data['away_team'] == team_code))
            ]
            
            if not game_match.empty:
                return int(game_match.iloc[0]['week'])
            
            return None
            
        except Exception as e:
            cprint(f"Error finding game week: {e}", "red")
            return None

    def get_player_stat_value(self, stats_data: pd.DataFrame, player_name: str, 
                            stat_type: str, team: str, week: int) -> Optional[float]:
        """Get a specific stat value for a player"""
        try:
            if stats_data.empty:
                return None
            
            # Normalize player name for matching
            player_name_lower = player_name.lower().strip()
            
            # Filter by team and week
            team_code = self.team_mapping.get(team)
            if not team_code:
                return None
            
            team_week_data = stats_data[(stats_data['recent_team'] == team_code) & (stats_data['week'] == week)]
            
            if team_week_data.empty:
                return None
            
            # Find player by name (try different name matching strategies)
            player_match = None
            
            # Try exact match first
            for _, player in team_week_data.iterrows():
                if player['player_name'].lower().strip() == player_name_lower:
                    player_match = player
                    break
            
            # Try partial match if exact fails
            if player_match is None:
                name_parts = player_name_lower.split()
                for _, player in team_week_data.iterrows():
                    player_name_parts = player['player_name'].lower().strip().split()
                    if len(name_parts) >= 2 and len(player_name_parts) >= 2:
                        if (name_parts[0] in player_name_parts[0] and 
                            name_parts[-1] in player_name_parts[-1]):
                            player_match = player
                            break
            
            # Try abbreviated name matching (e.g., "Jalen Hurts" vs "J.Hurts" or "J Hurts")
            if player_match is None:
                for _, player in team_week_data.iterrows():
                    pbp_name = player['player_name'].lower().strip()
                    
                    # Handle "J.Hurts" format
                    if '.' in pbp_name:
                        pbp_parts = pbp_name.split('.')
                        if len(pbp_parts) == 2:
                            first_initial = pbp_parts[0]
                            last_name = pbp_parts[1]
                            # Check if our player's first name starts with the initial and last names match
                            if (player_name_lower.split()[0].startswith(first_initial) and 
                                player_name_lower.endswith(last_name)):
                                player_match = player
                                break
                    
                    # Handle "J Hurts" format (first initial + space + last name)
                    elif ' ' in pbp_name:
                        pbp_parts = pbp_name.split(' ', 1)
                        if len(pbp_parts) == 2 and len(pbp_parts[0]) == 1:
                            first_initial = pbp_parts[0]
                            last_name = pbp_parts[1]
                            # Check if our player's first name starts with the initial and last names match
                            if (player_name_lower.split()[0].startswith(first_initial) and 
                                player_name_lower.endswith(last_name)):
                                player_match = player
                                break
            
            # Try reverse abbreviated matching (e.g., "J.Hurts" or "J Hurts" vs "Jalen Hurts")
            if player_match is None:
                name_parts = player_name_lower.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = name_parts[-1]
                    first_initial = first_name[0]
                    
                    for _, player in team_week_data.iterrows():
                        pbp_name = player['player_name'].lower().strip()
                        
                        # Handle "J.Hurts" format
                        if '.' in pbp_name:
                            pbp_parts = pbp_name.split('.')
                            if len(pbp_parts) == 2:
                                pbp_initial = pbp_parts[0]
                                pbp_last = pbp_parts[1]
                                if (first_initial == pbp_initial and last_name == pbp_last):
                                    player_match = player
                                    break
                        
                        # Handle "J Hurts" format
                        elif ' ' in pbp_name:
                            pbp_parts = pbp_name.split(' ', 1)
                            if len(pbp_parts) == 2 and len(pbp_parts[0]) == 1:
                                pbp_initial = pbp_parts[0]
                                pbp_last = pbp_parts[1]
                                if (first_initial == pbp_initial and last_name == pbp_last):
                                    player_match = player
                                    break
            
            if player_match is None:
                # Debug: Show available players for this team/week
                available_players = [p['player_name'] for p in team_week_data.to_dict('records')]
                cprint(f"Could not find stats for {player_name} ({stat_type}) - Available players: {available_players[:5]}", "red")
                return None
            
            # Get the stat value
            stat_attr = self.stat_mapping.get(stat_type)
            if not stat_attr:
                return None
            
            # Handle special cases for defensive and kicking stats
            if stat_type == 'Sacks':
                value = player_match.get('sacks', 0)
            elif stat_type == 'FG Made':
                value = player_match.get('field_goals_made', 0)
            elif stat_type == 'Kicking Points':
                value = player_match.get('kicking_points', 0)
            elif stat_attr in player_match:
                value = player_match[stat_attr]
            else:
                return None
            
            return float(value) if pd.notna(value) else 0.0
            
        except Exception as e:
            cprint(f"Error getting stat value for {player_name}: {e}", "red")
            return None

    def calculate_combined_stats(self, stats_data: pd.DataFrame, player_name: str, 
                               stat_type: str, team: str, week: int) -> Optional[float]:
        """Calculate combined stats like Rush+Rec Yds, Pass+Rush Yds, etc."""
        try:
            if stats_data.empty:
                return None
            
            player_name_lower = player_name.lower().strip()
            team_code = self.team_mapping.get(team)
            if not team_code:
                return None
            
            # Filter by team and week
            team_week_data = stats_data[(stats_data['recent_team'] == team_code) & (stats_data['week'] == week)]
            
            if team_week_data.empty:
                return None
            
            # Find player by name
            player_match = None
            for _, player in team_week_data.iterrows():
                if player['player_name'].lower().strip() == player_name_lower:
                    player_match = player
                    break
            
            # Try partial match if exact fails
            if player_match is None:
                name_parts = player_name_lower.split()
                for _, player in team_week_data.iterrows():
                    player_name_parts = player['player_name'].lower().strip().split()
                    if len(name_parts) >= 2 and len(player_name_parts) >= 2:
                        if (name_parts[0] in player_name_parts[0] and 
                            name_parts[-1] in player_name_parts[-1]):
                            player_match = player
                            break
            
            # Try abbreviated name matching (e.g., "Jalen Hurts" vs "J.Hurts" or "J Hurts")
            if player_match is None:
                for _, player in team_week_data.iterrows():
                    pbp_name = player['player_name'].lower().strip()
                    
                    # Handle "J.Hurts" format
                    if '.' in pbp_name:
                        pbp_parts = pbp_name.split('.')
                        if len(pbp_parts) == 2:
                            first_initial = pbp_parts[0]
                            last_name = pbp_parts[1]
                            # Check if our player's first name starts with the initial and last names match
                            if (player_name_lower.split()[0].startswith(first_initial) and 
                                player_name_lower.endswith(last_name)):
                                player_match = player
                                break
                    
                    # Handle "J Hurts" format (first initial + space + last name)
                    elif ' ' in pbp_name:
                        pbp_parts = pbp_name.split(' ', 1)
                        if len(pbp_parts) == 2 and len(pbp_parts[0]) == 1:
                            first_initial = pbp_parts[0]
                            last_name = pbp_parts[1]
                            # Check if our player's first name starts with the initial and last names match
                            if (player_name_lower.split()[0].startswith(first_initial) and 
                                player_name_lower.endswith(last_name)):
                                player_match = player
                                break
            
            # Try reverse abbreviated matching (e.g., "J.Hurts" or "J Hurts" vs "Jalen Hurts")
            if player_match is None:
                name_parts = player_name_lower.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = name_parts[-1]
                    first_initial = first_name[0]
                    
                    for _, player in team_week_data.iterrows():
                        pbp_name = player['player_name'].lower().strip()
                        
                        # Handle "J.Hurts" format
                        if '.' in pbp_name:
                            pbp_parts = pbp_name.split('.')
                            if len(pbp_parts) == 2:
                                pbp_initial = pbp_parts[0]
                                pbp_last = pbp_parts[1]
                                if (first_initial == pbp_initial and last_name == pbp_last):
                                    player_match = player
                                    break
                        
                        # Handle "J Hurts" format
                        elif ' ' in pbp_name:
                            pbp_parts = pbp_name.split(' ', 1)
                            if len(pbp_parts) == 2 and len(pbp_parts[0]) == 1:
                                pbp_initial = pbp_parts[0]
                                pbp_last = pbp_parts[1]
                                if (first_initial == pbp_initial and last_name == pbp_last):
                                    player_match = player
                                    break
            
            if player_match is None:
                # Debug: Show available players for this team/week
                available_players = [p['player_name'] for p in team_week_data.to_dict('records')]
                cprint(f"Could not find stats for {player_name} ({stat_type}) - Available players: {available_players[:5]}", "red")
                return None
            
            if stat_type == 'Rush+Rec Yds':
                rush_yards = float(player_match['rushing_yards']) if pd.notna(player_match['rushing_yards']) else 0.0
                rec_yards = float(player_match['receiving_yards']) if pd.notna(player_match['receiving_yards']) else 0.0
                return rush_yards + rec_yards
            
            elif stat_type == 'Rush+Rec TDs':
                rush_tds = float(player_match['rushing_tds']) if pd.notna(player_match['rushing_tds']) else 0.0
                rec_tds = float(player_match['receiving_tds']) if pd.notna(player_match['receiving_tds']) else 0.0
                return rush_tds + rec_tds
            
            elif stat_type == 'Pass+Rush Yds':
                pass_yards = float(player_match['passing_yards']) if pd.notna(player_match['passing_yards']) else 0.0
                rush_yards = float(player_match['rushing_yards']) if pd.notna(player_match['rushing_yards']) else 0.0
                return pass_yards + rush_yards
            
            elif stat_type == 'Fantasy Score':
                # Use the built-in fantasy points from nfl_data_py
                return float(player_match['fantasy_points']) if pd.notna(player_match['fantasy_points']) else 0.0
            
            elif stat_type == 'Tackles+Ast':
                tackles = float(player_match['tackles']) if pd.notna(player_match['tackles']) else 0.0
                assists = float(player_match['assists']) if pd.notna(player_match['assists']) else 0.0
                return tackles + assists
            
            return None
            
        except Exception as e:
            cprint(f"Error calculating combined stats for {player_name}: {e}", "red")
            return None

    def update_actual_results(self, sheet_name: str, players: List[Dict[str, Any]]) -> int:
        """Update actual results for players in a specific sheet"""
        updates = []
        
        # Get player stats data once for efficiency
        stats_data = self.get_player_stats_data()
        if stats_data.empty:
            cprint("Could not fetch player stats data", "red")
            return 0
        
        for player in players:
            if player['actual']:  # Skip if already has actual result
                continue
            
            game_date = self.parse_game_date(player['game_time'])
            if not game_date:
                cprint(f"Could not parse game date for {player['player_name']}", "red")
                continue
            
            # Check if game has been played (game date is in the past)
            if isinstance(game_date, datetime):
                if game_date > datetime.now():
                    cprint(f"Game for {player['player_name']} hasn't been played yet", "yellow")
                    continue
            else:
                # If it's a date object, compare with today's date
                if game_date > datetime.now().date():
                    cprint(f"Game for {player['player_name']} hasn't been played yet", "yellow")
                    continue
            
            # Find the week number for this game
            week = self.find_game_week(player['team'], player['opponent'], game_date)
            if not week:
                cprint(f"Could not find week for {player['team']} vs {player['opponent']}", "red")
                continue
            
            # Get player stats
            stat_type = player['stat_type']
            if stat_type in ['Rush+Rec Yds', 'Rush+Rec TDs', 'Pass+Rush Yds', 'Fantasy Score', 'Tackles+Ast']:
                actual_value = self.calculate_combined_stats(stats_data, player['player_name'], 
                                                          stat_type, player['team'], week)
            else:
                actual_value = self.get_player_stat_value(stats_data, player['player_name'], 
                                                        stat_type, player['team'], week)
            
            if actual_value is not None:
                line_value = float(player['line']) if player['line'] else 0
                over_under = 'Over' if actual_value > line_value else 'Under' if line_value > 0 else ''
                
                updates.append({
                    'row': player['row_index'],
                    'player': player['player_name'],
                    'actual': actual_value,
                    'line': line_value,
                    'over_under': over_under
                })
                cprint(f"Found actual result for {player['player_name']}: {actual_value} {stat_type}", "green")
            else:
                cprint(f"Could not find stats for {player['player_name']} ({stat_type})", "red")
        
        # Update Google Sheets
        if updates:
            self._update_sheets(sheet_name, updates)
        
        return len(updates)

    def _update_sheets(self, sheet_name: str, updates: List[Dict[str, Any]]):
        """Update Google Sheets with actual results"""
        try:
            actual_updates = []
            over_under_updates = []
            
            for update in updates:
                actual_updates.append({
                    'range': f"'{sheet_name}'!H{update['row']}",
                    'values': [[update['actual']]]
                })
                
                if update['over_under']:
                    over_under_updates.append({
                        'range': f"'{sheet_name}'!I{update['row']}",
                        'values': [[update['over_under']]]
                    })
            
            # Batch update
            body = {
                'valueInputOption': 'RAW',
                'data': actual_updates + over_under_updates
            }
            
            self.sheets_service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
            cprint(f"Updated {len(updates)} players in {sheet_name}", "green")
            
        except Exception as e:
            cprint(f"Error updating sheets: {e}", "red")

    def fetch_all_actual_results(self):
        """Fetch actual results for all sheets"""
        if not self.sheets_service:
            cprint("Google Sheets service not available", "red")
            return
        
        sheet_names = self.get_all_sheets()
        total_updates = 0
        
        cprint(f"\n🏈 Starting NFL Stats Fetch for {len(sheet_names)} sheets...", "green", attrs=["bold"])
        cprint("Using nfl_data_py for official NFL statistics", "cyan")
        
        for sheet_name in sheet_names:
            cprint(f"\n📊 Processing sheet: {sheet_name}", "cyan", attrs=["bold"])
            players = self.read_sheet_data(sheet_name)
            
            if not players:
                cprint(f"No players found in {sheet_name}", "yellow")
                continue
            
            updates = self.update_actual_results(sheet_name, players)
            total_updates += updates
            cprint(f"✅ Updated {updates} players in {sheet_name}", "green")
            
            # Small delay between sheets
            time.sleep(1)
        
        cprint(f"\n🎯 Total updates across all sheets: {total_updates}", "green", attrs=["bold"])

def main():
    spreadsheet_id = "1H9HcjtjoG9AlRJ3lAvgZXpefYfuVcylwqc4D4B_Ai1g"
    
    fetcher = NFLStatsFetcher(spreadsheet_id)
    fetcher.fetch_all_actual_results()

if __name__ == "__main__":
    main()
