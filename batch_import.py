"""
Simple batch import script for TSM items.

This script directly imports item IDs from a text file into your TSM saved variables.
Much simpler than scraping - just paste item IDs from any source.

Usage:
    python batch_import.py <group_path> <items_file>
    
Example:
    python batch_import.py "Transmog`Swords`One Hand" sword_ids.txt
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from tsm_scraper.lua_parser import TSMLuaParser
from tsm_scraper.lua_writer import TSMLuaWriter

# Default TSM path
DEFAULT_TSM_PATH = r"c:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\TradeSkillMaster.lua"


def load_item_ids(source: str) -> list[int]:
    """
    Load item IDs from a file or comma-separated string.
    
    File format: One item ID per line, or comma-separated
    Can also include Wowhead links - will extract IDs from them.
    """
    ids = []
    
    if os.path.isfile(source):
        with open(source, 'r') as f:
            content = f.read()
    else:
        content = source
    
    # Split by common delimiters
    import re
    
    # Find all numbers that look like item IDs (3-8 digits)
    matches = re.findall(r'\b(\d{3,8})\b', content)
    
    for match in matches:
        try:
            item_id = int(match)
            if item_id not in ids:
                ids.append(item_id)
        except ValueError:
            continue
    
    return ids


def main():
    print("=" * 60)
    print("TSM Batch Item Importer")
    print("=" * 60)
    
    # Check arguments
    if len(sys.argv) < 3:
        print("\nUsage: python batch_import.py <group_path> <items>")
        print("\nExamples:")
        print('  python batch_import.py "Transmog`Swords`One Hand" items.txt')
        print('  python batch_import.py "Transmog`Daggers" "12345,12346,12347"')
        print("\nAvailable Groups (from your TSM):")
        
        # Show some groups
        parser = TSMLuaParser(DEFAULT_TSM_PATH)
        if parser.load():
            parser.parse_groups()
            for group in sorted(parser.groups)[:30]:
                print(f"  {group}")
            if len(parser.groups) > 30:
                print(f"  ... and {len(parser.groups) - 30} more")
        
        return
    
    group_path = sys.argv[1]
    items_source = sys.argv[2]
    dry_run = "--dry-run" in sys.argv
    
    # Load item IDs
    print(f"\nLoading items from: {items_source}")
    item_ids = load_item_ids(items_source)
    
    if not item_ids:
        print("ERROR: No valid item IDs found!")
        return
    
    print(f"Found {len(item_ids)} item IDs")
    
    if len(item_ids) <= 10:
        print(f"Items: {item_ids}")
    else:
        print(f"First 10: {item_ids[:10]} ...")
    
    # Check TSM file
    print(f"\nTSM File: {DEFAULT_TSM_PATH}")
    parser = TSMLuaParser(DEFAULT_TSM_PATH)
    if not parser.load():
        print("ERROR: Could not load TSM file!")
        return
    
    parser.parse_items()
    parser.parse_groups()
    
    print(f"Current items in TSM: {len(parser.items)}")
    print(f"Target group: {group_path}")
    
    # Check if group exists
    if group_path not in parser.groups:
        print(f"\nWARNING: Group '{group_path}' does not exist in TSM!")
        print("Items will still be added, but make sure to create the group in-game.")
    
    # Check for already existing items
    existing_ids = parser.get_existing_item_ids()
    new_ids = [i for i in item_ids if i not in existing_ids]
    duplicate_ids = [i for i in item_ids if i in existing_ids]
    
    print(f"\nNew items to add: {len(new_ids)}")
    print(f"Already in TSM: {len(duplicate_ids)}")
    
    if not new_ids:
        print("\nNo new items to add!")
        return
    
    if dry_run:
        print("\n[DRY RUN] No changes made.")
        print("Remove --dry-run to actually import items.")
        return
    
    # Import items
    print("\nImporting items...")
    writer = TSMLuaWriter(DEFAULT_TSM_PATH)
    
    items_dict = {item_id: group_path for item_id in new_ids}
    result = writer.add_items(items_dict, dry_run=False)
    
    print(f"\n{'=' * 60}")
    print("RESULTS:")
    print(f"  Added: {result['added']}")
    print(f"  Skipped: {result['skipped']}")
    if result['errors']:
        print(f"  Errors: {result['errors']}")
    print(f"{'=' * 60}")
    
    print("\nDone! Restart WoW or /reload to see changes in TSM.")


if __name__ == "__main__":
    main()
