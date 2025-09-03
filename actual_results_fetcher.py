from google.oauth2 import service_account
from googleapiclient.discovery import build
from sportsreference.nfl.boxscore import Boxscore
from sportsreference.nfl.teams import Teams
from sportsreference.nfl.schedule import Schedule
from datetime import datetime, timedelta
import re
import time
from typing import Dict, List, Optional, Any
from termcolor import cprint

class ActualResultsFetcher:
    def __init__(self, spreadsheet_id: str, service_account_file: str = 'service-account-key.json'):
        self.spreadsheet_id = spreadsheet_id
        self.service_account_file = service_account_file
        self.sheets_service = self._setup_google_sheets()
        
        # Team abbreviation mapping for sportsreference
        self.team_mapping = {
            'ARI': 'ARI', 'ATL': 'ATL', 'BAL': 'BAL', 'BUF': 'BUF', 'CAR': 'CAR',
            'CHI': 'CHI', 'CIN': 'CIN', 'CLE': 'CLE', 'DAL': 'DAL', 'DEN': 'DEN',
            'DET': 'DET', 'GB': 'GNB', 'HOU': 'HOU', 'IND': 'IND', 'JAC': 'JAX',
            'KC': 'KAN', 'LV': 'LVR', 'LAC': 'LAC', 'LAR': 'LAR', 'MIA': 'MIA',
            'MIN': 'MIN', 'NE': 'NWE', 'NO': 'NOR', 'NYG': 'NYG', 'NYJ': 'NYJ',
            'PHI': 'PHI', 'PIT': 'PIT', 'SF': 'SFO', 'SEA': 'SEA', 'TB': 'TAM',
            'TEN': 'TEN', 'WAS': 'WAS'
        }
        
        # Stat type mapping to sportsreference attributes
        self.stat_mapping = {
            'Pass Yards': 'passing_yards',
            'Rush Yards': 'rushing_yards', 
            'Pass TDs': 'passing_touchdowns',
            'Receiving Yards': 'receiving_yards',
            'FG Made': 'field_goals_made',
            'Receptions': 'receptions',
            'Rush+Rec Yds': 'rushing_yards',  # Will need to combine with receiving
            'Fantasy Score': None,  # Will need to calculate
            'Pass Attempts': 'passing_attempts',
            'Rec Targets': 'receiving_targets',
            'Sacks': 'sacks',
            'Pass Completions': 'passing_completions',
            'INT': 'interceptions',
            'Pass+Rush Yds': 'passing_yards',  # Will need to combine with rushing
            'Rush Attempts': 'rushing_attempts',
            'Kicking Points': 'kicking_points',
            'Tackles+Ast': 'tackles'  # Will need to combine with assists
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
            for row in values[1:]:  # Skip header
                if len(row) >= 5:
                    players.append({
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
            match = re.match(r'(\w{3})\s+(\d{1,2}):(\d{2})([ap]m)', game_time_str.strip())
            if not match:
                return None
            
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
                return None
            
            today = datetime.now()
            days_ahead = (day_num - today.weekday()) % 7
            if days_ahead == 0 and (hour < today.hour or (hour == today.hour and minute <= today.minute)):
                days_ahead = 7
            
            game_date = today + timedelta(days=days_ahead)
            return game_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
        except Exception as e:
            cprint(f"Error parsing game time '{game_time_str}': {e}", "red")
            return None

    def find_game_boxscore(self, team: str, opponent: str, game_date: datetime) -> Optional[Boxscore]:
        try:
            team_code = self.team_mapping.get(team)
            opponent_code = self.team_mapping.get(opponent)
            
            if not team_code or not opponent_code:
                cprint(f"Unknown team codes: {team} -> {team_code}, {opponent} -> {opponent_code}", "red")
                return None
            
            # Get team schedule to find the game
            teams = Teams(2025)  # Assuming 2025 season, adjust as needed
            team_obj = teams(team_code)
            
            if not team_obj:
                cprint(f"Team {team_code} not found", "red")
                return None
            
            schedule = team_obj.schedule
            for game in schedule:
                game_date_obj = game.date
                if (game_date_obj.date() == game_date.date() and 
                    (game.opponent_abbr == opponent_code or game.opponent_abbr == team_code)):
                    return game.boxscore
            
            return None
            
        except Exception as e:
            cprint(f"Error finding game boxscore for {team} vs {opponent}: {e}", "red")
            return None

    def get_player_stats(self, boxscore: Boxscore, player_name: str, stat_type: str) -> Optional[float]:
        try:
            if not boxscore:
                return None
            
            # Map stat type to sportsreference attribute
            stat_attr = self.stat_mapping.get(stat_type)
            if not stat_attr:
                return None
            
            # Search through all players in the boxscore
            for player in boxscore.away_players + boxscore.home_players:
                if player.name.lower() == player_name.lower():
                    if hasattr(player, stat_attr):
                        value = getattr(player, stat_attr)
                        return float(value) if value is not None else 0.0
            
            return None
            
        except Exception as e:
            cprint(f"Error getting stats for {player_name}: {e}", "red")
            return None

    def calculate_combined_stats(self, boxscore: Boxscore, player_name: str, stat_type: str) -> Optional[float]:
        try:
            if not boxscore:
                return None
            
            for player in boxscore.away_players + boxscore.home_players:
                if player.name.lower() == player_name.lower():
                    if stat_type == 'Rush+Rec Yds':
                        rush_yards = float(player.rushing_yards) if player.rushing_yards else 0.0
                        rec_yards = float(player.receiving_yards) if player.receiving_yards else 0.0
                        return rush_yards + rec_yards
                    
                    elif stat_type == 'Pass+Rush Yds':
                        pass_yards = float(player.passing_yards) if player.passing_yards else 0.0
                        rush_yards = float(player.rushing_yards) if player.rushing_yards else 0.0
                        return pass_yards + rush_yards
                    
                    elif stat_type == 'Fantasy Score':
                        # Basic fantasy scoring: 1 point per 25 passing yards, 4 per passing TD, etc.
                        pass_yards = float(player.passing_yards) if player.passing_yards else 0.0
                        pass_tds = float(player.passing_touchdowns) if player.passing_touchdowns else 0.0
                        rush_yards = float(player.rushing_yards) if player.rushing_yards else 0.0
                        rush_tds = float(player.rushing_touchdowns) if player.rushing_touchdowns else 0.0
                        rec_yards = float(player.receiving_yards) if player.receiving_yards else 0.0
                        rec_tds = float(player.receiving_touchdowns) if player.receiving_touchdowns else 0.0
                        receptions = float(player.receptions) if player.receptions else 0.0
                        interceptions = float(player.interceptions) if player.interceptions else 0.0
                        
                        fantasy_points = (
                            (pass_yards / 25) + (pass_tds * 4) + (rush_yards / 10) + (rush_tds * 6) +
                            (rec_yards / 10) + (rec_tds * 6) + receptions - (interceptions * 2)
                        )
                        return fantasy_points
                    
                    elif stat_type == 'Tackles+Ast':
                        tackles = float(player.tackles) if player.tackles else 0.0
                        assists = float(player.assists) if player.assists else 0.0
                        return tackles + assists
            
            return None
            
        except Exception as e:
            cprint(f"Error calculating combined stats for {player_name}: {e}", "red")
            return None

    def update_actual_results(self, sheet_name: str, players: List[Dict[str, Any]]) -> int:
        updates = []
        
        for player in players:
            if player['actual']:  # Skip if already has actual result
                continue
            
            game_date = self.parse_game_date(player['game_time'])
            if not game_date:
                cprint(f"Could not parse game date for {player['player_name']}", "red")
                continue
            
            # Check if game has been played (game date is in the past)
            if game_date > datetime.now():
                cprint(f"Game for {player['player_name']} hasn't been played yet", "yellow")
                continue
            
            boxscore = self.find_game_boxscore(player['team'], player['opponent'], game_date)
            if not boxscore:
                cprint(f"Could not find boxscore for {player['team']} vs {player['opponent']}", "red")
                continue
            
            # Get player stats
            stat_type = player['stat_type']
            if stat_type in ['Rush+Rec Yds', 'Pass+Rush Yds', 'Fantasy Score', 'Tackles+Ast']:
                actual_value = self.calculate_combined_stats(boxscore, player['player_name'], stat_type)
            else:
                actual_value = self.get_player_stats(boxscore, player['player_name'], stat_type)
            
            if actual_value is not None:
                updates.append({
                    'row': players.index(player) + 2,  # +2 because we skip header and 0-indexed
                    'player': player['player_name'],
                    'actual': actual_value,
                    'line': float(player['line']) if player['line'] else 0,
                    'over_under': 'Over' if actual_value > float(player['line']) else 'Under' if player['line'] else ''
                })
                cprint(f"Found actual result for {player['player_name']}: {actual_value}", "green")
            else:
                cprint(f"Could not find stats for {player['player_name']}", "red")
        
        # Update Google Sheets
        if updates:
            self._update_sheets(sheet_name, updates)
        
        return len(updates)

    def _update_sheets(self, sheet_name: str, updates: List[Dict[str, Any]]):
        try:
            # Update Actual column (H)
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
        if not self.sheets_service:
            cprint("Google Sheets service not available", "red")
            return
        
        sheet_names = self.get_all_sheets()
        total_updates = 0
        
        for sheet_name in sheet_names:
            cprint(f"\nProcessing sheet: {sheet_name}", "cyan", attrs=["bold"])
            players = self.read_sheet_data(sheet_name)
            
            if not players:
                cprint(f"No players found in {sheet_name}", "yellow")
                continue
            
            updates = self.update_actual_results(sheet_name, players)
            total_updates += updates
            cprint(f"Updated {updates} players in {sheet_name}", "green")
            
            # Small delay between sheets
            time.sleep(1)
        
        cprint(f"\nTotal updates across all sheets: {total_updates}", "green", attrs=["bold"])

def main():
    spreadsheet_id = "1H9HcjtjoG9AlRJ3lAvgZXpefYfuVcylwqc4D4B_Ai1g"
    
    fetcher = ActualResultsFetcher(spreadsheet_id)
    fetcher.fetch_all_actual_results()

if __name__ == "__main__":
    main()
