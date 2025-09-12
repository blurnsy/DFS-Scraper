#!/usr/bin/env python3

import json
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
from google.oauth2 import service_account
from googleapiclient.discovery import build
from termcolor import cprint
import pandas as pd

class ResultsAnalyzer:
    def __init__(self, spreadsheet_id: str, service_account_file: str = 'service-account-key.json'):
        self.spreadsheet_id = spreadsheet_id
        self.service_account_file = service_account_file
        self.service = None
        self.data = []
        
    def initialize_service(self):
        """Initialize Google Sheets service"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            return True
        except Exception as e:
            cprint(f"Error initializing Google Sheets service: {e}", "red")
            return False
    
    def list_available_sheets(self):
        """List all available sheets in the spreadsheet"""
        if not self.service:
            if not self.initialize_service():
                return []
        
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            sheets = spreadsheet.get('sheets', [])
            sheet_names = [sheet['properties']['title'] for sheet in sheets]
            
            cprint(f"\n📋 Available sheets in spreadsheet:", "cyan", attrs=["bold"])
            for i, name in enumerate(sheet_names, 1):
                cprint(f"  {i}. {name}", "white")
            
            return sheet_names
            
        except Exception as e:
            cprint(f"Error listing sheets: {e}", "red")
            return []
    
    def load_sheet_data(self, sheet_name: str) -> bool:
        """Load data from a specific sheet"""
        if not self.service:
            if not self.initialize_service():
                return False
        
        try:
            # Properly escape sheet names with spaces or special characters
            range_name = f"'{sheet_name}'!A:K"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values or len(values) < 2:
                cprint(f"No data found in sheet '{sheet_name}'", "yellow")
                return False
            
            # Parse data into structured format
            self.data = []
            headers = values[0]
            total_rows = 0
            filtered_rows = 0
            
            for i, row in enumerate(values[1:], start=2):
                if len(row) >= 11:  # Ensure we have all required columns
                    # Safely convert line to float, handle non-numeric values
                    line_value = 0
                    if len(row) > 7 and row[7]:
                        try:
                            line_value = float(row[7])
                        except (ValueError, TypeError):
                            line_value = 0
                    
                    # Safely convert actual to float
                    actual_value = None
                    if len(row) > 9 and row[9]:
                        try:
                            actual_value = float(row[9])
                        except (ValueError, TypeError):
                            actual_value = None
                    
                    player_data = {
                        'row_index': i,
                        'week': row[0] if len(row) > 0 else '',
                        'stat_type': row[1] if len(row) > 1 else '',
                        'player_name': row[2] if len(row) > 2 else '',
                        'position': row[3] if len(row) > 3 else '',
                        'team': row[4] if len(row) > 4 else '',
                        'opponent': row[5] if len(row) > 5 else '',
                        'game_time': row[6] if len(row) > 6 else '',
                        'line': line_value,
                        'payout_type': row[8] if len(row) > 8 else 'Standard',
                        'actual': actual_value,
                        'over_under': row[10] if len(row) > 10 else ''
                    }
                    
                    total_rows += 1
                    
                    # Only include rows with actual results
                    if player_data['actual'] is not None and player_data['over_under']:
                        self.data.append(player_data)
                        filtered_rows += 1
            
            cprint(f"Processed {total_rows} rows, filtered to {filtered_rows} completed bets from '{sheet_name}'", "green")
            return True
            
        except Exception as e:
            cprint(f"Error loading data from sheet '{sheet_name}': {e}", "red")
            return False
    
    def get_stat_type_from_line(self, line_value: float, position: str) -> str:
        """Infer stat type from line value and position"""
        if position == 'QB':
            if line_value > 200:
                return 'Pass Yards'
            elif line_value > 50:
                return 'Rush Yards'
            else:
                return 'Pass TDs'
        elif position == 'RB':
            if line_value > 100:
                return 'Rush Yards'
            elif line_value > 10:
                return 'Rush Attempts'
            else:
                return 'Rush TDs'
        elif position == 'WR' or position == 'TE':
            if line_value > 100:
                return 'Receiving Yards'
            elif line_value > 10:
                return 'Receptions'
            else:
                return 'Receiving TDs'
        else:
            return 'Unknown'
    
    def calculate_over_under_ratios(self) -> Dict[str, Any]:
        """Calculate comprehensive over/under ratios"""
        if not self.data:
            return {}
        
        # Initialize counters
        stat_type_ratios = defaultdict(lambda: {'over': 0, 'under': 0, 'total': 0})
        player_ratios = defaultdict(lambda: {'over': 0, 'under': 0, 'total': 0})
        team_ratios = defaultdict(lambda: {'over': 0, 'under': 0, 'total': 0})
        position_ratios = defaultdict(lambda: {'over': 0, 'under': 0, 'total': 0})
        
        # Process each bet
        for bet in self.data:
            over_under = bet['over_under'].lower()
            if over_under not in ['over', 'under']:
                continue
            
            # Use the actual stat type from the data
            stat_type = bet['stat_type']
            
            # Update counters
            stat_type_ratios[stat_type][over_under] += 1
            stat_type_ratios[stat_type]['total'] += 1
            
            player_ratios[bet['player_name']][over_under] += 1
            player_ratios[bet['player_name']]['total'] += 1
            
            team_ratios[bet['team']][over_under] += 1
            team_ratios[bet['team']]['total'] += 1
            
            position_ratios[bet['position']][over_under] += 1
            position_ratios[bet['position']]['total'] += 1
        
        # Calculate percentages
        def calculate_percentages(ratios_dict):
            result = {}
            for key, counts in ratios_dict.items():
                if counts['total'] > 0:
                    result[key] = {
                        'over': counts['over'],
                        'under': counts['under'],
                        'total': counts['total'],
                        'over_pct': round((counts['over'] / counts['total']) * 100, 1),
                        'under_pct': round((counts['under'] / counts['total']) * 100, 1)
                    }
            return result
        
        return {
            'by_stat_type': calculate_percentages(stat_type_ratios),
            'by_player': calculate_percentages(player_ratios),
            'by_team': calculate_percentages(team_ratios),
            'by_position': calculate_percentages(position_ratios)
        }
    
    def display_stat_type_ratios(self, ratios: Dict[str, Any]):
        """Display over/under ratios by stat type"""
        cprint("\n" + "="*60, "cyan")
        cprint("📊 OVER/UNDER RATIOS BY STAT TYPE", "yellow", attrs=["bold"])
        cprint("="*60, "cyan")
        
        if not ratios:
            cprint("No data available", "red")
            return
        
        # Sort by total bets (descending)
        sorted_stats = sorted(ratios.items(), key=lambda x: x[1]['total'], reverse=True)
        
        for stat_type, data in sorted_stats:
            over_color = "green" if data['over_pct'] > 50 else "red"
            under_color = "green" if data['under_pct'] > 50 else "red"
            
            cprint(f"\n{stat_type}:", "white", attrs=["bold"])
            cprint(f"  Total Bets: {data['total']}", "cyan")
            cprint(f"  Over: {data['over']} ({data['over_pct']}%)", over_color)
            cprint(f"  Under: {data['under']} ({data['under_pct']}%)", under_color)
    
    def display_player_ratios(self, ratios: Dict[str, Any], min_bets: int = 3):
        """Display over/under ratios by player"""
        cprint("\n" + "="*60, "cyan")
        cprint("👤 OVER/UNDER RATIOS BY PLAYER", "yellow", attrs=["bold"])
        cprint("="*60, "cyan")
        
        if not ratios:
            cprint("No data available", "red")
            return
        
        # Filter players with minimum bets and sort by total
        filtered_players = {k: v for k, v in ratios.items() if v['total'] >= min_bets}
        sorted_players = sorted(filtered_players.items(), key=lambda x: x[1]['total'], reverse=True)
        
        if not sorted_players:
            cprint(f"No players with at least {min_bets} bets", "yellow")
            return
        
        for player, data in sorted_players:
            over_color = "green" if data['over_pct'] > 50 else "red"
            under_color = "green" if data['under_pct'] > 50 else "red"
            
            cprint(f"\n{player}:", "white", attrs=["bold"])
            cprint(f"  Total Bets: {data['total']}", "cyan")
            cprint(f"  Over: {data['over']} ({data['over_pct']}%)", over_color)
            cprint(f"  Under: {data['under']} ({data['under_pct']}%)", under_color)
    
    def display_team_ratios(self, ratios: Dict[str, Any]):
        """Display over/under ratios by team"""
        cprint("\n" + "="*60, "cyan")
        cprint("🏈 OVER/UNDER RATIOS BY TEAM", "yellow", attrs=["bold"])
        cprint("="*60, "cyan")
        
        if not ratios:
            cprint("No data available", "red")
            return
        
        # Sort by total bets (descending)
        sorted_teams = sorted(ratios.items(), key=lambda x: x[1]['total'], reverse=True)
        
        for team, data in sorted_teams:
            over_color = "green" if data['over_pct'] > 50 else "red"
            under_color = "green" if data['under_pct'] > 50 else "red"
            
            cprint(f"\n{team}:", "white", attrs=["bold"])
            cprint(f"  Total Bets: {data['total']}", "cyan")
            cprint(f"  Over: {data['over']} ({data['over_pct']}%)", over_color)
            cprint(f"  Under: {data['under']} ({data['under_pct']}%)", under_color)
    
    def display_position_ratios(self, ratios: Dict[str, Any]):
        """Display over/under ratios by position"""
        cprint("\n" + "="*60, "cyan")
        cprint("⚡ OVER/UNDER RATIOS BY POSITION", "yellow", attrs=["bold"])
        cprint("="*60, "cyan")
        
        if not ratios:
            cprint("No data available", "red")
            return
        
        # Sort by total bets (descending)
        sorted_positions = sorted(ratios.items(), key=lambda x: x[1]['total'], reverse=True)
        
        for position, data in sorted_positions:
            over_color = "green" if data['over_pct'] > 50 else "red"
            under_color = "green" if data['under_pct'] > 50 else "red"
            
            cprint(f"\n{position}:", "white", attrs=["bold"])
            cprint(f"  Total Bets: {data['total']}", "cyan")
            cprint(f"  Over: {data['over']} ({data['over_pct']}%)", over_color)
            cprint(f"  Under: {data['under']} ({data['under_pct']}%)", under_color)
    
    def display_summary_report(self, ratios: Dict[str, Any]):
        """Display comprehensive summary report"""
        cprint("\n" + "="*80, "cyan")
        cprint("📈 COMPREHENSIVE RESULTS SUMMARY", "yellow", attrs=["bold"])
        cprint("="*80, "cyan")
        
        if not ratios:
            cprint("No data available", "red")
            return
        
        # Overall totals
        total_bets = sum(data['total'] for data in ratios['by_stat_type'].values())
        total_over = sum(data['over'] for data in ratios['by_stat_type'].values())
        total_under = sum(data['under'] for data in ratios['by_stat_type'].values())
        overall_over_pct = round((total_over / total_bets) * 100, 1) if total_bets > 0 else 0
        
        cprint(f"\n🎯 OVERALL PERFORMANCE", "white", attrs=["bold"])
        cprint(f"Total Bets: {total_bets}", "cyan")
        cprint(f"Over: {total_over} ({overall_over_pct}%)", "green" if overall_over_pct > 50 else "red")
        cprint(f"Under: {total_under} ({100 - overall_over_pct}%)", "green" if overall_over_pct < 50 else "red")
        
        # Best performing stat types
        cprint(f"\n🏆 BEST PERFORMING STAT TYPES", "white", attrs=["bold"])
        stat_performance = []
        for stat_type, data in ratios['by_stat_type'].items():
            if data['total'] >= 5:  # Only show stats with at least 5 bets
                over_pct = data['over_pct']
                stat_performance.append((stat_type, over_pct, data['total']))
        
        stat_performance.sort(key=lambda x: x[1], reverse=True)
        for i, (stat_type, over_pct, total) in enumerate(stat_performance[:5], 1):
            color = "green" if over_pct > 50 else "red"
            cprint(f"  {i}. {stat_type}: {over_pct}% over ({total} bets)", color)
        
        # Best performing players
        cprint(f"\n⭐ BEST PERFORMING PLAYERS", "white", attrs=["bold"])
        player_performance = []
        for player, data in ratios['by_player'].items():
            if data['total'] >= 3:  # Only show players with at least 3 bets
                over_pct = data['over_pct']
                player_performance.append((player, over_pct, data['total']))
        
        player_performance.sort(key=lambda x: x[1], reverse=True)
        for i, (player, over_pct, total) in enumerate(player_performance[:5], 1):
            color = "green" if over_pct > 50 else "red"
            cprint(f"  {i}. {player}: {over_pct}% over ({total} bets)", color)
    
    def analyze_sheet(self, sheet_name: str):
        """Perform complete analysis of a sheet"""
        cprint(f"\n🔍 Analyzing sheet: {sheet_name}", "green", attrs=["bold"])
        
        if not self.load_sheet_data(sheet_name):
            return False
        
        if not self.data:
            cprint("No completed bets found in this sheet", "yellow")
            return False
        
        ratios = self.calculate_over_under_ratios()
        
        # Display all reports
        self.display_summary_report(ratios)
        self.display_stat_type_ratios(ratios['by_stat_type'])
        self.display_player_ratios(ratios['by_player'])
        self.display_team_ratios(ratios['by_team'])
        self.display_position_ratios(ratios['by_position'])
        
        return True
    
    def analyze_master_file(self):
        """Convenience method to analyze the Master File worksheet"""
        return self.analyze_sheet("Master File")

def get_all_stat_types():
    """Get all available stat types for analysis"""
    return [
        "Pass Yards",
        "Rush Yards", 
        "Pass TDs",
        "Receiving Yards",
        "FG Made",
        "Receptions",
        "Rush+Rec Yds",
        "Rush+Rec TDs",
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

def display_stat_type_menu():
    """Display stat type selection menu"""
    stat_types = get_all_stat_types()
    
    cprint("\n" + "="*50, "cyan")
    cprint("📊 STAT TYPE SELECTION", "yellow", attrs=["bold"])
    cprint("="*50, "cyan")
    cprint("Select which stat type you want to analyze:", "white")
    print()
    
    for i, stat_type in enumerate(stat_types, 1):
        cprint(f"{i:2d}) {stat_type}", "white")
    
    cprint(f"{len(stat_types) + 1:2d}) All Stats", "green")
    print()
    
    return stat_types

def get_stat_type_selection():
    """Get and validate stat type selection from menu"""
    stat_types = display_stat_type_menu()
    
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
            cprint("\n👋 Analysis cancelled", "yellow")
            return None

def analyze_by_stat_type():
    """Analyze results by selected stat type(s)"""
    spreadsheet_id = "1H9HcjtjoG9AlRJ3lAvgZXpefYfuVcylwqc4D4B_Ai1g"
    analyzer = ResultsAnalyzer(spreadsheet_id)
    
    try:
        # Get stat type selection from user
        selected_stats = get_stat_type_selection()
        if not selected_stats:
            return False
        
        cprint(f"\n🎯 Analyzing stat type(s): {', '.join(selected_stats)}", "green", attrs=["bold"])
        
        # Load data from Master File
        if not analyzer.load_sheet_data("Master File"):
            cprint("❌ Failed to load Master File data", "red")
            return False
        
        if not analyzer.data:
            cprint("❌ No data found in Master File", "red")
            return False
        
        # Filter data by selected stat types
        if len(selected_stats) == 1 and selected_stats[0] != "All Stats":
            # Single stat type - filter the data
            filtered_data = [bet for bet in analyzer.data if bet['stat_type'] == selected_stats[0]]
            if not filtered_data:
                cprint(f"❌ No data found for stat type: {selected_stats[0]}", "red")
                return False
            
            # Temporarily replace analyzer.data with filtered data
            original_data = analyzer.data
            analyzer.data = filtered_data
            
            cprint(f"📊 Found {len(filtered_data)} bets for {selected_stats[0]}", "cyan")
            
            # Calculate and display ratios
            ratios = analyzer.calculate_over_under_ratios()
            analyzer.display_summary_report(ratios)
            analyzer.display_stat_type_ratios(ratios['by_stat_type'])
            analyzer.display_player_ratios(ratios['by_player'])
            analyzer.display_team_ratios(ratios['by_team'])
            analyzer.display_position_ratios(ratios['by_position'])
            
            # Restore original data
            analyzer.data = original_data
            
        else:
            # All stats or multiple stats - show full analysis
            ratios = analyzer.calculate_over_under_ratios()
            
            if len(selected_stats) > 1:
                # Multiple specific stats - filter the display
                filtered_stat_ratios = {stat: data for stat, data in ratios['by_stat_type'].items() 
                                      if stat in selected_stats}
                ratios['by_stat_type'] = filtered_stat_ratios
            
            analyzer.display_summary_report(ratios)
            analyzer.display_stat_type_ratios(ratios['by_stat_type'])
            analyzer.display_player_ratios(ratios['by_player'])
            analyzer.display_team_ratios(ratios['by_team'])
            analyzer.display_position_ratios(ratios['by_position'])
        
        return True
        
    except KeyboardInterrupt:
        cprint("\n\n👋 Analysis cancelled", "yellow")
        return False
    except Exception as e:
        cprint(f"❌ Error analyzing by stat type: {e}", "red")
        return False

def main():
    """Main function for command line usage"""
    import sys
    
    spreadsheet_id = "1H9HcjtjoG9AlRJ3lAvgZXpefYfuVcylwqc4D4B_Ai1g"  # Your spreadsheet ID
    
    # Default to "Master File" if no sheet name provided
    if len(sys.argv) < 2:
        # Use stat type selection menu
        analyze_by_stat_type()
    else:
        sheet_name = sys.argv[1]
        analyzer = ResultsAnalyzer(spreadsheet_id)
        analyzer.analyze_sheet(sheet_name)

if __name__ == "__main__":
    main()
