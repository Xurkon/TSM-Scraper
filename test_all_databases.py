"""
Quick test script to verify all database scrapers work.
Tests a single item lookup from each database.
"""
import sys
sys.path.insert(0, r'c:\Ascension Launcher\resources\client\TSMItemScraper')

from tsm_scraper.wowhead_scraper import WowheadScraper
from tsm_scraper.ascension_scraper import AscensionDBScraper
from tsm_scraper.turtlewow_scraper import TurtleWoWScraper

# Test item IDs that should exist in each version
# Using Hearthstone (6948) as a common item that exists in most versions
TEST_ITEMS = {
    'ascension': (6948, AscensionDBScraper),
    'turtlewow': (6948, TurtleWoWScraper),
    'wotlk': (6948, 'wotlk'),
    'tbc': (6948, 'tbc'),
    'classic': (6948, 'classic'),
    'cata': (6948, 'cata'),
    'mop': (6948, 'mop'),
    'retail': (6948, 'retail'),
}

print("=" * 60)
print("TSM Scraper - Database Test Results")
print("=" * 60)

results = []

for db_name, (item_id, scraper_info) in TEST_ITEMS.items():
    print(f"\nTesting {db_name.upper()}...")
    try:
        if db_name == 'ascension':
            scraper = AscensionDBScraper()
        elif db_name == 'turtlewow':
            scraper = TurtleWoWScraper()
        else:
            scraper = WowheadScraper(game_version=scraper_info)
        
        item = scraper.get_item(item_id)
        
        if item:
            print(f"  ✓ SUCCESS: {item.name} (ID: {item.id})")
            results.append((db_name, True, item.name))
        else:
            print(f"  ✗ FAILED: No item returned")
            results.append((db_name, False, "No item returned"))
    except Exception as e:
        print(f"  ✗ ERROR: {str(e)[:50]}")
        results.append((db_name, False, str(e)[:50]))

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

passed = sum(1 for _, success, _ in results if success)
total = len(results)

for db_name, success, info in results:
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"  {status}: {db_name.upper():12} -> {info}")

print(f"\nTotal: {passed}/{total} databases working")
