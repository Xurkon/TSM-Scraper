"""Test the actual import process to diagnose the issue."""
import sys
sys.path.insert(0, '.')

from tsm_scraper.lua_writer import TSMLuaWriter
from tsm_scraper.lua_parser import TSMLuaParser

tsm_path = r"C:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\TradeSkillMaster.lua"

output = []

# First, check existing items
parser = TSMLuaParser(tsm_path)
if parser.load():
    parser.parse_items()
    existing_ids = parser.get_existing_item_ids()
    output.append(f"Found {len(existing_ids)} existing items in TSM file")
    output.append(f"Sample existing IDs: {list(existing_ids)[:10]}")
else:
    output.append("ERROR: Could not load TSM file!")
    existing_ids = set()

# Now test adding a new item (dry run)
writer = TSMLuaWriter(tsm_path)

# Use a test ID that definitely shouldn't exist: 999999999
test_items = {
    999999999: "Test`TestGroup",
}

output.append(f"\n=== Testing add_items with test ID 999999999 ===")
result = writer.add_items(test_items, dry_run=True)
output.append(f"Result: {result}")

# Also test with a real ID that might be "new"
test_items2 = {
    12345: "Test`TestGroup",
}
output.append(f"\n=== Testing add_items with ID 12345 ===")
result2 = writer.add_items(test_items2, dry_run=True)
output.append(f"Result: {result2}")

# Check if 12345 is already in the file
if 12345 in existing_ids:
    output.append("Note: 12345 already exists in the file")
else:
    output.append("Note: 12345 does NOT exist in the file")

# Write to file
with open('test_output.txt', 'w') as f:
    f.write('\n'.join(output))

print("Results saved to test_output.txt")
