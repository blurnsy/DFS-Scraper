"""
Stat Name Mapping System
Maps different stat names from PrizePicks and Underdog Fantasy to standardized sheet names
"""

# Mapping from various stat names to standardized sheet names
# This consolidates similar stats into shared sheets
STAT_NAME_MAPPING = {
    # Fantasy Points/Score - SHARED SHEET
    "Fantasy Points": "Fantasy Points",
    "Fantasy Score": "Fantasy Points",
    
    # Rush + Rec TDs - SHARED SHEET
    "Rush + Rec TDs": "Rush Plus Rec TDs",
    "Rush+Rec TDs": "Rush Plus Rec TDs",
    
    # Rush + Rec Yds - SHARED SHEET  
    "Rush + Rec Yds": "Rush Plus Rec Yds", 
    "Rush+Rec Yds": "Rush Plus Rec Yds",
    "Rush + Rec Yards": "Rush Plus Rec Yds",  # Underdog uses "Yards" instead of "Yds"
    
    # Pass + Rush Yards - SHARED SHEET
    "Pass + Rush Yards": "Pass Plus Rush Yards",
    "Pass+Rush Yds": "Pass Plus Rush Yards",
    
    # Tackles + Assists - SHARED SHEET
    "Tackles + Assists": "Tackles Plus Assists",
    "Tackles+Ast": "Tackles Plus Assists",
    
    # Receiving Yards - SHARED SHEET
    "Receiving Yards": "Receiving Yards",
    
    # Pass TDs - SHARED SHEET
    "Pass TDs": "Pass TDs",
    
    # FG Made - SHARED SHEET
    "FG Made": "FG Made",
    
    # Receptions - SHARED SHEET
    "Receptions": "Receptions",
    
    # Pass Attempts - SHARED SHEET
    "Pass Attempts": "Pass Attempts",
    
    # Targets/Rec Targets - SHARED SHEET
    "Targets": "Rec Targets",
    "Rec Targets": "Rec Targets",
    
    # Sacks - SHARED SHEET
    "Sacks": "Sacks",
    
    # Completions/Pass Completions - SHARED SHEET
    "Completions": "Pass Completions",
    "Pass Completions": "Pass Completions",
    
    # INT/INTs Thrown - SHARED SHEET
    "INT": "INTs Thrown",
    "INTs Thrown": "INTs Thrown",
    
    # Rush Attempts - SHARED SHEET
    "Rush Attempts": "Rush Attempts",
    
    # Kicking Points - SHARED SHEET
    "Kicking Points": "Kicking Points",
    
    # Pass Yards - SHARED SHEET
    "Pass Yards": "Pass Yards",
    
    # Rush Yards - SHARED SHEET
    "Rush Yards": "Rush Yards"
}

def get_standardized_sheet_name(stat_name):
    """
    Convert any stat name to its standardized sheet name
    
    Args:
        stat_name (str): The original stat name from either PrizePicks or Underdog
        
    Returns:
        str: The standardized sheet name
    """
    return STAT_NAME_MAPPING.get(stat_name, stat_name)

def get_all_standardized_stat_types():
    """
    Get all standardized stat types (unique sheet names)
    
    Returns:
        list: List of all standardized stat type names
    """
    return list(set(STAT_NAME_MAPPING.values()))

def get_prizepicks_stat_types():
    """
    Get PrizePicks stat types mapped to standardized names
    
    Returns:
        list: PrizePicks stat types with standardized names
    """
    prizepicks_stats = [
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
    
    return [get_standardized_sheet_name(stat) for stat in prizepicks_stats]

def get_underdog_stat_types():
    """
    Get Underdog Fantasy stat types mapped to standardized names
    
    Returns:
        list: Underdog stat types with standardized names
    """
    underdog_stats = [
        "Pass Yards",
        "Rush Yards",
        "Pass TDs",
        "Receiving Yards",
        "FG Made",
        "Receptions",
        "Rush + Rec TDs",
        "Fantasy Points",
        "Pass Attempts",
        "Targets",
        "Sacks",
        "Completions",
        "INTs Thrown",
        "Pass + Rush Yards",
        "Rush + Rec Yards",
        "Rush Attempts",
        "Kicking Points",
        "Tackles + Assists"
    ]
    
    return [get_standardized_sheet_name(stat) for stat in underdog_stats]

def get_redundant_sheet_mappings():
    """
    Get mappings of redundant sheet names to their standardized versions
    
    Returns:
        dict: Mapping of old sheet names to new standardized names
    """
    redundant_mappings = {}
    
    # Find all stat names that map to the same standardized name
    reverse_mapping = {}
    for original, standardized in STAT_NAME_MAPPING.items():
        if standardized not in reverse_mapping:
            reverse_mapping[standardized] = []
        reverse_mapping[standardized].append(original)
    
    # Create mappings for redundant names
    for standardized, originals in reverse_mapping.items():
        if len(originals) > 1:
            # Use the first original as the "canonical" name, map others to it
            canonical = originals[0]
            for original in originals[1:]:
                redundant_mappings[original] = canonical
    
    return redundant_mappings

if __name__ == "__main__":
    # Test the mapping system
    print("=== STAT NAME MAPPING SYSTEM ===")
    print("\nPrizePicks stats -> Standardized:")
    for stat in ["Fantasy Score", "Rush+Rec Yds", "Pass+Rush Yds", "Tackles+Ast"]:
        print(f"  {stat} -> {get_standardized_sheet_name(stat)}")
    
    print("\nUnderdog stats -> Standardized:")
    for stat in ["Fantasy Points", "Rush + Rec TDs", "Pass + Rush Yards", "Tackles + Assists"]:
        print(f"  {stat} -> {get_standardized_sheet_name(stat)}")
    
    print(f"\nAll standardized stat types ({len(get_all_standardized_stat_types())}):")
    for stat in sorted(get_all_standardized_stat_types()):
        print(f"  - {stat}")
    
    print("\nRedundant mappings:")
    for old_name, new_name in get_redundant_sheet_mappings().items():
        print(f"  {old_name} -> {new_name}")
