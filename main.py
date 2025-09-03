#!/usr/bin/env python3

import sys
import os
from typing import Optional
from termcolor import cprint

def show_menu():
    """Display the main menu options"""
    cprint("\n" + "="*60, "cyan")
    cprint("🏈 PrizePicks Scraper & Results Fetcher", "yellow", attrs=["bold"])
    cprint("="*60, "cyan")
    cprint("1. 🎯 Scrape PrizePicks", "white")
    cprint("2. 📊 Fetch Actual Results", "white")
    cprint("3. ⏰ Game Monitor", "white")
    cprint("4. 🛠️  Maintenance Tools", "white")
    cprint("5. ❌ Exit", "white")
    cprint("="*60, "cyan")

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
        visit_prizepicks.main()
        return True
    except ImportError as e:
        cprint(f"❌ Error importing visit_prizepicks: {e}", "red")
        return False
    except Exception as e:
        cprint(f"❌ Error running PrizePicks scraper: {e}", "red")
        return False

def run_results_fetcher():
    """Run the actual results fetcher"""
    try:
        cprint("\n📊 Starting Actual Results Fetcher...", "green", attrs=["bold"])
        import actual_results_fetcher
        actual_results_fetcher.main()
        return True
    except ImportError as e:
        cprint(f"❌ Error importing actual_results_fetcher: {e}", "red")
        return False
    except Exception as e:
        cprint(f"❌ Error running results fetcher: {e}", "red")
        return False

def run_game_monitor():
    """Run the game monitor"""
    try:
        cprint("\n⏰ Starting Game Monitor...", "green", attrs=["bold"])
        import monitor
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        # Setup Google Sheets service
        try:
            scopes = ['https://www.googleapis.com/auth/spreadsheets']
            service_account_file = 'service-account-key.json'
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=scopes)
            sheets_service = build('sheets', 'v4', credentials=credentials)
            
            # Use the same spreadsheet ID as the scraper
            spreadsheet_id = "1H9HcjtjoG9AlRJ3lAvgZXpefYfuVcylwqc4D4B_Ai1g"
            
            # Run monitoring session
            monitor.run_monitoring_session(sheets_service, spreadsheet_id)
            return True
        except Exception as e:
            cprint(f"❌ Error setting up Google Sheets: {e}", "red")
            cprint("Please ensure you have a service account key file named 'service-account-key.json'", "yellow")
            return False
            
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

def main():
    """Main application entry point"""
    while True:
        show_menu()
        
        try:
            choice = input("\nSelect an option (1-5): ").strip()
            
            if choice == '1':
                run_prizepicks_scraper()
            elif choice == '2':
                run_results_fetcher()
            elif choice == '3':
                run_game_monitor()
            elif choice == '4':
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
            elif choice == '5':
                cprint("\n👋 Goodbye!", "green", attrs=["bold"])
                break
            else:
                cprint("❌ Invalid choice. Please select 1-5.", "red")
                
        except KeyboardInterrupt:
            cprint("\n\n👋 Goodbye!", "green", attrs=["bold"])
            break
        except Exception as e:
            cprint(f"❌ Unexpected error: {e}", "red")

if __name__ == "__main__":
    main()
