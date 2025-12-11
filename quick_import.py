"""
Quick Import Script - Scrape from Ascension DB and import to TSM in one step.

Usage:
    python quick_import.py <category>
    python quick_import.py <category> --dry-run

Examples:
    python quick_import.py dagger
    python quick_import.py sword_1h
    python quick_import.py axe_2h --dry-run
    
Available Categories:
    Weapons: axe_1h, axe_2h, bow, crossbow, dagger, fist, gun, mace_1h, mace_2h,
             polearm, staff, sword_1h, sword_2h, thrown, wand, fishing_pole
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tsm_scraper.ascension_scraper import AscensionDBScraper
from tsm_scraper.lua_parser import TSMLuaParser
from tsm_scraper.lua_writer import TSMLuaWriter

DEFAULT_TSM_PATH = r"c:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\TradeSkillMaster.lua"


def main():
    print("=" * 60)
    print("TSM Quick Import - Ascension Database")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\nUsage: python quick_import.py <category> [--dry-run]")
        print("\nWeapon Categories:")
        scraper = AscensionDBScraper()
        for weapon_type, group in scraper.WEAPON_TO_GROUP.items():
            print(f"  {weapon_type:15} -> {group}")
        return
    
    category = sys.argv[1].lower()
    dry_run = "--dry-run" in sys.argv
    
    # Initialize
    scraper = AscensionDBScraper()
    parser = TSMLuaParser(DEFAULT_TSM_PATH)
    writer = TSMLuaWriter(DEFAULT_TSM_PATH)
    
    # Get TSM group for this category
    tsm_group = scraper.get_tsm_group_for_weapon(category)
    
    print(f"\nCategory: {category}")
    print(f"TSM Group: {tsm_group}")
    
    # Load existing TSM data
    print(f"\nLoading TSM file...")
    if not parser.load():
        print("ERROR: Could not load TSM file!")
        return
    
    parser.parse_items()
    existing_ids = parser.get_existing_item_ids()
    print(f"  Existing items in TSM: {len(parser.items)}")
    
    # Scrape from Ascension DB
    print(f"\nScraping {category} from Ascension DB...")
    item_ids = scraper.scrape_weapons(category, limit=500)
    
    if not item_ids:
        print("No items found!")
        return
    
    print(f"  Found: {len(item_ids)} items")
    
    # Filter out already existing items
    new_ids = [i for i in item_ids if i not in existing_ids]
    print(f"  New items: {len(new_ids)}")
    print(f"  Already in TSM: {len(item_ids) - len(new_ids)}")
    
    if not new_ids:
        print("\nNo new items to import!")
        return
    
    # Show some of the new IDs
    print(f"\n  New IDs (first 20): {new_ids[:20]}")
    
    if dry_run:
        print("\n[DRY RUN] No changes made.")
        return
    
    # Import to TSM
    print(f"\nImporting to TSM...")
    items_dict = {item_id: tsm_group for item_id in new_ids}
    result = writer.add_items(items_dict, dry_run=False)
    
    print(f"\n{'=' * 60}")
    print("RESULTS:")
    print(f"  Added: {result['added']}")
    print(f"  Skipped: {result['skipped']}")
    if result['errors']:
        print(f"  Errors: {result['errors']}")
    print(f"{'=' * 60}")
    print("\nDone! Restart WoW or /reload to see changes.")


if __name__ == "__main__":
    main()
