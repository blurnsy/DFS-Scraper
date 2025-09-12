"""
Rate-limited Google Sheets operations to avoid API quota exceeded errors
"""

import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from termcolor import cprint

class RateLimitedSheetsService:
    def __init__(self, service_account_file='service-account-key.json'):
        self.service = self._setup_service(service_account_file)
        self.last_request_time = 0
        self.min_request_interval = 1.1  # Minimum 1.1 seconds between requests (allows ~54 requests/minute)
        self.request_count = 0
        self.request_window_start = time.time()
        self.max_requests_per_minute = 50  # Conservative limit (actual limit is 60)
    
    def _setup_service(self, service_account_file):
        """Setup Google Sheets API connection"""
        try:
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES)
            return build('sheets', 'v4', credentials=credentials)
        except Exception as e:
            cprint(f"Error setting up Google Sheets: {e}", "red")
            return None
    
    def _wait_if_needed(self):
        """Wait if we need to respect rate limits"""
        current_time = time.time()
        
        # Reset request count every minute
        if current_time - self.request_window_start >= 60:
            self.request_count = 0
            self.request_window_start = current_time
        
        # Check if we're approaching the rate limit
        if self.request_count >= self.max_requests_per_minute:
            wait_time = 60 - (current_time - self.request_window_start)
            if wait_time > 0:
                cprint(f"⏳ Rate limit approaching, waiting {wait_time:.1f} seconds...", "yellow")
                time.sleep(wait_time)
                self.request_count = 0
                self.request_window_start = time.time()
        
        # Ensure minimum interval between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def batch_update(self, spreadsheet_id, requests):
        """Perform a batch update with rate limiting"""
        if not self.service:
            return False
        
        self._wait_if_needed()
        
        try:
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            return True
        except Exception as e:
            cprint(f"Batch update error: {e}", "red")
            return False
    
    def update_values(self, spreadsheet_id, range_name, values, value_input_option='RAW'):
        """Update values with rate limiting"""
        if not self.service:
            return False
        
        self._wait_if_needed()
        
        try:
            body = {'values': values}
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body
            ).execute()
            return True
        except Exception as e:
            cprint(f"Update values error: {e}", "red")
            return False
    
    def append_values(self, spreadsheet_id, range_name, values, value_input_option='RAW'):
        """Append values with rate limiting"""
        if not self.service:
            return False
        
        self._wait_if_needed()
        
        try:
            body = {'values': values}
            self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body
            ).execute()
            return True
        except Exception as e:
            cprint(f"Append values error: {e}", "red")
            return False
    
    def get_values(self, spreadsheet_id, range_name):
        """Get values with rate limiting"""
        if not self.service:
            return None
        
        self._wait_if_needed()
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            return result.get('values', [])
        except Exception as e:
            cprint(f"Get values error: {e}", "red")
            return None
    
    def get_spreadsheet(self, spreadsheet_id):
        """Get spreadsheet metadata with rate limiting"""
        if not self.service:
            return None
        
        self._wait_if_needed()
        
        try:
            return self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        except Exception as e:
            cprint(f"Get spreadsheet error: {e}", "red")
            return None

def create_rate_limited_sheets_service():
    """Create a rate-limited Google Sheets service"""
    return RateLimitedSheetsService()
