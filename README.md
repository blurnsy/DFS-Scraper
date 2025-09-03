# PrizePicks Scraper with Game Time Monitoring

A Python script that scrapes player projections from PrizePicks and includes automatic monitoring for NFL games starting within 60 minutes using PrizePicks' own game time data.

## Features

- **Manual Scraping**: Scrape specific stat types or all stats from PrizePicks
- **Automatic Monitoring**: Monitor game times from PrizePicks and auto-scrape when games are 60 minutes away
- **Google Sheets Integration**: Automatically upload data to Google Sheets
- **Smart Updates**: Only updates changed prop lines, preserves existing data
- **Live Betting Filter**: Automatically skips players when games have started (configurable)

## Installation

1. **Install Dependencies**:
   ```bash
   python main.py
   # Select option 3 (Maintenance Tools) -> 1 (Install Dependencies)
   ```
   
   Or manually:
   ```bash
   pip install -r requirements.txt
   ```

2. **Google Sheets Setup** (Optional):
   - Create a Google Cloud Project
   - Enable Google Sheets API
   - Create a service account and download the JSON key
   - Place the key file as `service-account-key.json` in the project directory
   - Update `SPREADSHEET_ID` in the script with your Google Sheets ID

## Usage

### Main Application
```bash
python main.py
```

This will show you a menu with options:
1. **🎯 Scrape PrizePicks** - Run the main scraper
2. **📊 Fetch Actual Results** - Run the results fetcher
3. **⏰ Game Monitor** - Monitor for upcoming games and auto-scrape
4. **🛠️ Maintenance Tools** - Access utility scripts
5. **❌ Exit** - Quit the application

### PrizePicks Scraper Options
When you select option 1, you'll get the scraper menu:
- Individual stat types (Pass Yards, Rush Yards, etc.)
- All Stats (scrapes everything)

### Game Monitor
When you select option 3, you'll get the monitoring mode:
- Continuously monitors Google Sheets for upcoming games
- Automatically triggers scraping when games are within 60 minutes
- No browser needed until games are detected

### How Monitoring Works
The monitoring mode (option 3) uses your existing Google Sheets data to:
- Read game times from all existing sheets every 2 minutes (no browser needed)
- Parse game time strings (e.g., "Thu 7:20pm", "Sun 1:00pm")
- Detect games starting within 60 minutes
- Automatically open browser and trigger final scraping when games are found
- Avoid duplicate triggers for the same game

1. **Data Source**: Reads game times from your existing Google Sheets (no re-scraping needed)
2. **Time Parsing**: Converts PrizePicks time format to datetime objects
3. **60-Minute Window**: Triggers final scraping when games are 0-60 minutes away
4. **Final Scrape**: Runs complete scraping process for all stat types (last update before games)
5. **Continuous Monitoring**: Keeps checking until stopped (Ctrl+C)

## Configuration

- **SPREADSHEET_ID**: Update with your Google Sheets ID
- **SKIP_LIVE_BETTING**: Set to `True` (default) to skip players when games start, `False` to track all players
- **Location Coordinates**: May need adjustment based on your screen resolution

### Live Betting Filter

The scraper automatically detects when games have started by looking for "Starting" indicators on player cards. When enabled:

- Players with "Starting" labels are automatically skipped
- A summary shows how many live betting players were filtered out
- This prevents your spreadsheet from tracking live betting lines
- Can be disabled by setting `SKIP_LIVE_BETTING = False` in the script

## Dependencies

- `seleniumbase`: Web scraping and browser automation
- `pyautogui`: Mouse coordinate clicking
- `google-api-python-client`: Google Sheets integration
- `datetime`: Time calculations and parsing

## Notes

- Monitoring mode reads game times from your existing Google Sheets data (no re-scraping needed)
- Monitoring mode runs continuously until manually stopped
- All existing scraping functionality remains unchanged
- Google Sheets integration is required for monitoring mode
- Game time parsing supports formats like "Thu 7:20pm", "Sun 1:00pm"
- Final scraping ensures you have the latest prop lines before games start

## Project Structure

```
Prizepicks/
├── main.py                    # Main entry point with menu system
├── visit_prizepicks.py        # PrizePicks scraper (core functionality)
├── monitor.py                 # Game monitoring and auto-scraping
├── actual_results_fetcher.py  # Results fetcher
├── utils/                     # Maintenance tools
│   ├── __init__.py
│   ├── install_dependencies.py
│   └── mouse_coordinates.py
├── requirements.txt           # Python dependencies
├── service-account-key.json   # Google Sheets API key
└── README.md                 # This file
```

## Troubleshooting

- **Import Errors**: Run `python main.py` and select Maintenance Tools -> Install Dependencies
- **Location Clicks**: Adjust coordinates in the script if clicks don't work
- **Google Sheets**: Ensure service account has edit permissions on your spreadsheet
- **Game Time Parsing**: If monitoring doesn't detect games, check that your Google Sheets contain game times in the expected format
- **Google Sheets Access**: Ensure your service account has read access to all sheets in your spreadsheet
