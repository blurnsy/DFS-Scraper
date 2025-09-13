# DFS Scraper with Game Time Monitoring

A comprehensive Python application that scrapes player projections from both PrizePicks and Underdog Fantasy, includes automatic game monitoring, and provides detailed analysis tools for sports betting data.

## Features

- **Multi-Platform Scraping**: Scrape specific stat types or all stats from both PrizePicks and Underdog Fantasy
- **Automatic Game Monitoring**: Monitor game times and auto-scrape both platforms when games are 60 minutes away
- **Google Sheets Integration**: Automatically upload data to Google Sheets with smart updates
- **Results Analysis**: Comprehensive analysis tools for betting performance and trends
- **NFL Stats Integration**: Official NFL statistics using nfl_data_py
- **Testing Framework**: Built-in testing tools for validation and debugging
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
1. **📊 Scrape Stats** - Scrape from PrizePicks or Underdog Fantasy
2. **📈 Fetch Game Stats** - Fetch official NFL statistics
3. **⏰ Game Monitor** - Monitor for upcoming games and auto-scrape both platforms
4. **📈 Results Analyzer** - Analyze betting performance and trends
5. **🧪 Testing Tools** - Run tests and validation tools
6. **🛠️ Maintenance Tools** - Access utility scripts
7. **❌ Exit** - Quit the application

### Scraping Options
When you select option 1, you'll get the scraper menu:
- **PrizePicks**: Individual stat types (Pass Yards, Rush Yards, etc.) or All Stats
- **Underdog Fantasy**: Individual prop types or All Props
- Both platforms support time-based filtering (next game only)

### Game Monitor
When you select option 3, you'll get the monitoring mode:
- Continuously monitors Google Sheets for upcoming games
- Automatically triggers sequential scraping (PrizePicks → Underdog) when games are within 60 minutes
- No browser needed until games are detected

### Results Analyzer
When you select option 4, you'll get analysis tools:
- **Quick Summary Report**: Overview of betting performance
- **Best Performers Report**: Top performing players and teams
- **Analyze by Stat Type**: Detailed analysis by specific statistics

### How Monitoring Works
The monitoring mode (option 3) uses your existing Google Sheets data to:
- Read game times from all existing sheets every 2 minutes (no browser needed)
- Parse game time strings (e.g., "Thu 7:20pm", "Sun 1:00pm")
- Detect games starting within 60 minutes
- Automatically open browser and trigger sequential scraping (PrizePicks → Underdog) when games are found
- Avoid duplicate triggers for the same game

1. **Data Source**: Reads game times from your existing Google Sheets (no re-scraping needed)
2. **Time Parsing**: Converts time format to datetime objects
3. **60-Minute Window**: Triggers final scraping when games are 0-60 minutes away
4. **Sequential Scraping**: Runs PrizePicks first, then Underdog Fantasy (last update before games)
5. **Continuous Monitoring**: Keeps checking until stopped (Ctrl+C)

### Testing Tools
When you select option 5, you'll get testing tools:
- **Quick Test**: Connection and component validation
- **Mock Mode Test**: Simulate results without live scraping
- **Comprehensive Test**: Full feature testing and validation

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
- `nfl_data_py`: Official NFL statistics
- `termcolor`: Colored terminal output
- `python-dotenv`: Environment variable management
- `pandas`: Data analysis and manipulation

## Key Features & Improvements

### Multi-Platform Support
- **PrizePicks**: Original platform with comprehensive stat coverage
- **Underdog Fantasy**: Additional platform with different prop types and odds
- **Sequential Monitoring**: Automatically scrapes both platforms when games are approaching

### Advanced Analysis
- **Performance Tracking**: Track over/under hit rates by player, team, and stat type
- **Trend Analysis**: Identify patterns in betting performance
- **Comprehensive Reports**: Multiple analysis views for different insights

### Robust Testing
- **Component Validation**: Test individual features and connections
- **Mock Mode**: Simulate results without live scraping
- **Comprehensive Testing**: Full system validation

## Notes

- Monitoring mode reads game times from your existing Google Sheets data (no re-scraping needed)
- Monitoring mode runs continuously until manually stopped
- Sequential scraping ensures both platforms are updated before games start
- Google Sheets integration is required for monitoring and analysis features
- Game time parsing supports formats like "Thu 7:20pm", "Sun 12:00pm"
- Analysis tools require completed bet data in your Google Sheets

## Project Structure

```
Prizepicks/
├── main.py                    # Main entry point with menu system
├── visit_prizepicks.py        # PrizePicks scraper
├── visit_underdog.py          # Underdog Fantasy scraper
├── monitor.py                 # Game monitoring and auto-scraping
├── nfl_stats_fetcher.py       # NFL statistics fetcher
├── actual_results_fetcher.py  # Results fetcher
├── results_analyzer.py        # Betting analysis tools
├── stat_mapping.py            # Stat type standardization
├── rate_limited_sheets.py     # Google Sheets rate limiting
├── utils/                     # Maintenance tools
│   ├── __init__.py
│   ├── install_dependencies.py
│   └── mouse_coordinates.py
├── requirements.txt           # Python dependencies
├── service-account-key.json   # Google Sheets API key
├── underdog_config.env        # Underdog Fantasy configuration
└── README.md                 # This file
```

## Troubleshooting

- **Import Errors**: Run `python main.py` and select Maintenance Tools -> Install Dependencies
- **Location Clicks**: Adjust coordinates in the script if clicks don't work
- **Google Sheets**: Ensure service account has edit permissions on your spreadsheet
- **Game Time Parsing**: If monitoring doesn't detect games, check that your Google Sheets contain game times in the expected format
- **Google Sheets Access**: Ensure your service account has read access to all sheets in your spreadsheet