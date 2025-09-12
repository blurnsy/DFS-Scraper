#!/usr/bin/env python3

import sys
import os
from typing import Optional
from termcolor import cprint

def show_menu():
    """Display the main menu options"""
    cprint("\n" + "="*60, "cyan")
    cprint("🤖 PrizePicks Bot", "yellow", attrs=["bold"])
    cprint("="*60, "cyan")
    cprint("1. 📊 Scrape Stats", "white")
    cprint("2. 📈 Fetch Game Stats", "white")
    cprint("3. ⏰ Game Monitor (Sequential: PrizePicks → Underdog)", "white")
    cprint("4. 📈 Results Analyzer", "white")
    cprint("5. 🧪 Testing Tools", "white")
    cprint("6. 🛠️  Maintenance Tools", "white")
    cprint("7. ❌ Exit", "white")
    cprint("="*60, "cyan")

def show_scraping_menu():
    """Display scraping options menu"""
    cprint("\n" + "="*50, "cyan")
    cprint("📊 Scrape Stats", "yellow", attrs=["bold"])
    cprint("="*50, "cyan")
    cprint("1. 🎯 PrizePicks", "white")
    cprint("2. 🐕 Underdog Fantasy", "white")
    cprint("3. ⬅️  Back to Main Menu", "white")
    cprint("="*50, "cyan")

def show_testing_menu():
    """Display testing tools menu"""
    cprint("\n" + "="*50, "cyan")
    cprint("🧪 Testing Tools", "yellow", attrs=["bold"])
    cprint("="*50, "cyan")
    cprint("1. ⚡ Quick Test (Connection & Components)", "white")
    cprint("2. 🎭 Mock Mode Test (Simulate Results)", "white")
    cprint("3. 📊 Comprehensive Test (All Features)", "white")
    cprint("4. ⬅️  Back to Main Menu", "white")
    cprint("="*50, "cyan")

def show_results_analyzer_menu():
    """Display results analyzer menu"""
    cprint("\n" + "="*50, "cyan")
    cprint("📈 Results Analyzer", "yellow", attrs=["bold"])
    cprint("="*50, "cyan")
    cprint("1. 📈 Quick Summary Report", "white")
    cprint("2. 🏆 Best Performers Report", "white")
    cprint("3. 🎯 Analyze by Stat Type", "white")
    cprint("4. ⬅️  Back to Main Menu", "white")
    cprint("="*50, "cyan")

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

def get_underdog_stat_type_selection():
    """Get and validate Underdog stat type selection from menu"""
    # Import the STAT_TYPES from visit_underdog
    try:
        import visit_underdog
        stat_types = visit_underdog.STAT_TYPES
    except ImportError:
        cprint("Error importing Underdog stat types", "red")
        return None
    
    cprint("\n" + "="*50, "cyan")
    cprint("UNDERDOG FANTASY - STAT TYPE SELECTION", "yellow", attrs=["bold"])
    cprint("="*50, "cyan")
    cprint("Select which prop type you want to scrape:", "white")
    print()
    
    for i, stat_type in enumerate(stat_types, 1):
        cprint(f"{i:2d}) {stat_type}", "white")
    
    cprint(f"{len(stat_types) + 1:2d}) All Stats", "green")
    print()
    
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
            cprint("\n👋 Scraping cancelled", "yellow")
            return None

def ask_time_filtering_prizepicks():
    """Ask if user wants to use time-based filtering for PrizePicks"""
    while True:
        try:
            response = input("\nUse time-based filtering for PrizePicks (only scrape next game time)? (y/n): ").strip().lower()
            
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                cprint("Please enter 'y' for yes or 'n' for no.", "red")
                
        except KeyboardInterrupt:
            cprint("\n👋 Scraping cancelled", "yellow")
            return False

def ask_time_filtering_underdog():
    """Ask if user wants to use time-based filtering for Underdog"""
    while True:
        try:
            response = input("\nUse time-based filtering for Underdog (only scrape next game time)? (y/n): ").strip().lower()
            
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                cprint("Please enter 'y' for yes or 'n' for no.", "red")
                
        except KeyboardInterrupt:
            cprint("\n👋 Scraping cancelled", "yellow")
            return False

def show_maintenance_menu():
    """Display maintenance tools menu"""
    cprint("\n" + "="*50, "cyan")
    cprint("🛠️  Maintenance Tools", "yellow", attrs=["bold"])
    cprint("="*50, "cyan")
    cprint("1. 📦 Install Dependencies", "white")
    cprint("2. 🖱️  Mouse Coordinates Tracker", "white")
    cprint("3. ⬅️  Back to Main Menu", "white")
    cprint("="*50, "cyan")

def run_prizepicks_scraper():
    """Run the PrizePicks scraper"""
    try:
        cprint("\n🎯 Starting PrizePicks Scraper...", "green", attrs=["bold"])
        import visit_prizepicks
        
        # Get stat type selection from user
        selected_stat_types = get_stat_type_selection()
        if not selected_stat_types:
            return False
        
        # Ask about time filtering
        use_time_filtering = ask_time_filtering_prizepicks()
        
        # Run non-interactive scraping
        success = visit_prizepicks.run_non_interactive_scraping(selected_stat_types, use_time_filtering)
        return success
        
    except ImportError as e:
        cprint(f"❌ Error importing visit_prizepicks: {e}", "red")
        return False
    except Exception as e:
        cprint(f"❌ Error running PrizePicks scraper: {e}", "red")
        return False

def run_underdog_scraper():
    """Run the Underdog Fantasy scraper"""
    try:
        cprint("\n🐕 Starting Underdog Fantasy Scraper...", "green", attrs=["bold"])
        import visit_underdog
        
        # Get stat type selection from user
        selected_stat_types = get_underdog_stat_type_selection()
        if not selected_stat_types:
            return False
        
        # Ask about time filtering
        use_time_filtering = ask_time_filtering_underdog()
        
        # Run non-interactive scraping
        success = visit_underdog.run_non_interactive_scraping(selected_stat_types, use_time_filtering)
        return success
        
    except ImportError as e:
        cprint(f"❌ Error importing visit_underdog: {e}", "red")
        return False
    except Exception as e:
        cprint(f"❌ Error running Underdog Fantasy scraper: {e}", "red")
        return False

def run_results_fetcher():
    """Run the NFL stats fetcher"""
    try:
        cprint("\n📊 Starting NFL Stats Fetcher...", "green", attrs=["bold"])
        cprint("Using nfl_data_py for official NFL statistics", "cyan")
        import nfl_stats_fetcher
        nfl_stats_fetcher.main()
        return True
    except ImportError as e:
        cprint(f"❌ Error importing nfl_stats_fetcher: {e}", "red")
        return False
    except Exception as e:
        cprint(f"❌ Error running NFL stats fetcher: {e}", "red")
        return False

def run_game_monitor():
    """Run the game monitor"""
    try:
        cprint("\n⏰ Starting Game Monitor...", "green", attrs=["bold"])
        import monitor
        
        # Run monitoring session with sequential scraping (PrizePicks → Underdog)
        monitor.run_monitoring_session(use_sequential_scraping=True, trigger_window_hours=1)
        return True
            
    except ImportError as e:
        cprint(f"❌ Error importing monitor: {e}", "red")
        return False
    except Exception as e:
        cprint(f"❌ Error running game monitor: {e}", "red")
        return False

def run_install_dependencies():
    """Run the dependency installer"""
    try:
        cprint("\n📦 Installing Dependencies...", "green", attrs=["bold"])
        sys.path.append('utils')
        import install_dependencies
        install_dependencies.main()
        return True
    except ImportError as e:
        cprint(f"❌ Error importing install_dependencies: {e}", "red")
        return False
    except Exception as e:
        cprint(f"❌ Error running dependency installer: {e}", "red")
        return False

def run_mouse_coordinates():
    """Run the mouse coordinates tracker"""
    try:
        cprint("\n🖱️  Starting Mouse Coordinates Tracker...", "green", attrs=["bold"])
        cprint("Press Ctrl+C to exit", "yellow")
        sys.path.append('utils')
        import mouse_coordinates
        mouse_coordinates.display_mouse_coordinates()
        return True
    except ImportError as e:
        cprint(f"❌ Error importing mouse_coordinates: {e}", "red")
        return False
    except Exception as e:
        cprint(f"❌ Error running mouse coordinates tracker: {e}", "red")
        return False

def run_quick_test():
    """Run the quick test"""
    try:
        cprint("\n⚡ Starting Quick Test...", "green", attrs=["bold"])
        sys.path.append('tests')
        import quick_test
        quick_test.run_quick_tests()
        return True
    except ImportError as e:
        cprint(f"❌ Error importing quick_test: {e}", "red")
        return False
    except Exception as e:
        cprint(f"❌ Error running quick test: {e}", "red")
        return False

def run_mock_test():
    """Run the mock mode test"""
    try:
        cprint("\n🎭 Starting Mock Mode Test...", "green", attrs=["bold"])
        sys.path.append('tests')
        import mock_test_mode
        mock_test_mode.test_mock_mode()
        return True
    except ImportError as e:
        cprint(f"❌ Error importing mock_test_mode: {e}", "red")
        return False
    except Exception as e:
        cprint(f"❌ Error running mock test: {e}", "red")
        return False

def run_comprehensive_test():
    """Run the comprehensive test"""
    try:
        cprint("\n📊 Starting Comprehensive Test...", "green", attrs=["bold"])
        sys.path.append('tests')
        import test_actual_results
        test_actual_results.run_comprehensive_test()
        return True
    except ImportError as e:
        cprint(f"❌ Error importing test_actual_results: {e}", "red")
        return False
    except Exception as e:
        cprint(f"❌ Error running comprehensive test: {e}", "red")
        return False

def run_results_analyzer():
    """Run the results analyzer"""
    try:
        cprint("\n📈 Starting Results Analyzer...", "green", attrs=["bold"])
        import results_analyzer
        analyzer = results_analyzer.ResultsAnalyzer("1H9HcjtjoG9AlRJ3lAvgZXpefYfuVcylwqc4D4B_Ai1g")
        return analyzer
    except ImportError as e:
        cprint(f"❌ Error importing results_analyzer: {e}", "red")
        return None
    except Exception as e:
        cprint(f"❌ Error initializing results analyzer: {e}", "red")
        return None


def run_quick_summary():
    """Run quick summary report using Master File"""
    analyzer = run_results_analyzer()
    if not analyzer:
        return False
    
    try:
        cprint("\n📊 Loading Master File data...", "cyan")
        if analyzer.load_sheet_data("Master File") and analyzer.data:
            ratios = analyzer.calculate_over_under_ratios()
            analyzer.display_summary_report(ratios)
            return True
        else:
            cprint("❌ No data found in Master File. Please check your data.", "red")
            return False
    except Exception as e:
        cprint(f"❌ Error running quick summary: {e}", "red")
        return False

def run_best_performers():
    """Run best performers report"""
    analyzer = run_results_analyzer()
    if not analyzer:
        return False
    
    try:
        sheet_name = input("\nEnter sheet name for best performers report: ").strip()
        if not sheet_name:
            cprint("❌ Sheet name cannot be empty", "red")
            return False
        
        if not analyzer.load_sheet_data(sheet_name):
            return False
        
        if not analyzer.data:
            cprint("No completed bets found in this sheet", "yellow")
            return False
        
        ratios = analyzer.calculate_over_under_ratios()
        
        # Display focused reports
        analyzer.display_stat_type_ratios(ratios['by_stat_type'])
        analyzer.display_player_ratios(ratios['by_player'])
        
        return True
    except KeyboardInterrupt:
        cprint("\n\n👋 Analysis cancelled", "yellow")
        return False
    except Exception as e:
        cprint(f"❌ Error running best performers report: {e}", "red")
        return False


def run_analyze_by_stat_type():
    """Analyze results by selected stat type(s)"""
    analyzer = run_results_analyzer()
    if not analyzer:
        return False
    
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
    """Main application entry point"""
    while True:
        show_menu()
        
        try:
            choice = input("\nSelect an option (1-7): ").strip()
            
            if choice == '1':
                # Scraping submenu
                while True:
                    show_scraping_menu()
                    scraping_choice = input("\nSelect scraping option (1-3): ").strip()
                    
                    if scraping_choice == '1':
                        success = run_prizepicks_scraper()
                        if success:
                            cprint("✅ PrizePicks scraping completed successfully!", "green")
                        else:
                            cprint("❌ PrizePicks scraping failed or was cancelled", "red")
                    elif scraping_choice == '2':
                        success = run_underdog_scraper()
                        if success:
                            cprint("✅ Underdog Fantasy scraping completed successfully!", "green")
                        else:
                            cprint("❌ Underdog Fantasy scraping failed or was cancelled", "red")
                    elif scraping_choice == '3':
                        break
                    else:
                        cprint("❌ Invalid choice. Please select 1-3.", "red")
            elif choice == '2':
                run_results_fetcher()
            elif choice == '3':
                run_game_monitor()
            elif choice == '4':
                # Results analyzer submenu
                while True:
                    show_results_analyzer_menu()
                    analyzer_choice = input("\nSelect analyzer option (1-4): ").strip()
                    
                    if analyzer_choice == '1':
                        run_quick_summary()
                    elif analyzer_choice == '2':
                        run_best_performers()
                    elif analyzer_choice == '3':
                        run_analyze_by_stat_type()
                    elif analyzer_choice == '4':
                        break
                    else:
                        cprint("❌ Invalid choice. Please select 1-4.", "red")
            elif choice == '5':
                # Testing submenu
                while True:
                    show_testing_menu()
                    test_choice = input("\nSelect testing option (1-4): ").strip()
                    
                    if test_choice == '1':
                        run_quick_test()
                    elif test_choice == '2':
                        run_mock_test()
                    elif test_choice == '3':
                        run_comprehensive_test()
                    elif test_choice == '4':
                        break
                    else:
                        cprint("❌ Invalid choice. Please select 1-4.", "red")
            elif choice == '6':
                # Maintenance submenu
                while True:
                    show_maintenance_menu()
                    maint_choice = input("\nSelect maintenance option (1-3): ").strip()
                    
                    if maint_choice == '1':
                        run_install_dependencies()
                    elif maint_choice == '2':
                        run_mouse_coordinates()
                    elif maint_choice == '3':
                        break
                    else:
                        cprint("❌ Invalid choice. Please select 1-3.", "red")
            elif choice == '7':
                cprint("\n👋 Goodbye!", "green", attrs=["bold"])
                break
            else:
                cprint("❌ Invalid choice. Please select 1-7.", "red")
                
        except KeyboardInterrupt:
            cprint("\n\n👋 Goodbye!", "green", attrs=["bold"])
            break
        except Exception as e:
            cprint(f"❌ Unexpected error: {e}", "red")

if __name__ == "__main__":
    main()
