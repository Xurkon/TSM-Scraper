"""
Test script to verify item removal completely removes IDs from SavedVariables.
"""

import tempfile
import shutil
from pathlib import Path
from tsm_scraper.lua_writer import TSMLuaWriter
from tsm_scraper.lua_parser import TSMLuaParser

# Create a minimal test TSM SavedVariables file
TEST_LUA_CONTENT = """TradeSkillMasterDB = {
    ["profileKeys"] = {
        ["Character - Server"] = "Default",
    },
    ["profiles"] = {
        ["Default"] = {
            ["userData"] = {
                ["items"] = {
                    ["S"] = {
                        ["item:12345:0:0:0:0:0:0"] = "Test`Group`One",
                        ["item:67890:0:0:0:0:0:0"] = "Test`Group`Two",
                        ["item:11111:0:0:0:0:0:0"] = "Test`Group`Three",
                        ["item:22222:0:0:0:0:0:0"] = "Test`Group`Three",
                    },
                },
            },
        },
    },
}
"""

def test_item_removal():
    """Test that remove_items completely removes item entries from the file."""

    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False, encoding='utf-8') as f:
        temp_path = f.name
        f.write(TEST_LUA_CONTENT)

    try:
        print("=" * 60)
        print("Testing Item Removal Functionality")
        print("=" * 60)

        # Parse initial state
        print("\n1. Initial State:")
        parser = TSMLuaParser(temp_path)
        parser.load()
        parser.parse_items()
        print(f"   Items in file: {len(parser.items)}")
        for item_key, group in parser.items.items():
            item_id = parser.get_item_id(item_key)
            print(f"   - Item {item_id}: {group}")

        # Remove some items
        items_to_remove = [12345, 22222]
        print(f"\n2. Removing items: {items_to_remove}")

        writer = TSMLuaWriter(temp_path)
        result = writer.remove_items(items_to_remove, dry_run=False)

        print(f"   Removed: {result['removed']}")
        print(f"   Not found: {result['not_found']}")
        if result['errors']:
            print(f"   Errors: {result['errors']}")

        # Parse after removal
        print("\n3. After Removal:")
        parser2 = TSMLuaParser(temp_path)
        parser2.load()
        parser2.parse_items()
        print(f"   Items remaining: {len(parser2.items)}")
        for item_key, group in parser2.items.items():
            item_id = parser2.get_item_id(item_key)
            print(f"   - Item {item_id}: {group}")

        # Verify the removed items are NOT in the file content
        print("\n4. Verification (searching raw file content):")
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()

        all_passed = True
        for item_id in items_to_remove:
            if f"item:{item_id}:" in content:
                print(f"   ❌ FAILED: Item {item_id} still found in file!")
                all_passed = False
            else:
                print(f"   ✓ SUCCESS: Item {item_id} completely removed")

        # Verify remaining items ARE in the file
        remaining_ids = [67890, 11111]
        for item_id in remaining_ids:
            if f"item:{item_id}:" in content:
                print(f"   ✓ SUCCESS: Item {item_id} still in file (as expected)")
            else:
                print(f"   ❌ FAILED: Item {item_id} was incorrectly removed!")
                all_passed = False

        print("\n" + "=" * 60)
        if result['removed'] == len(items_to_remove) and all_passed:
            print("✓ TEST PASSED: All items removed successfully")
        else:
            print("❌ TEST FAILED: Not all items were removed correctly")
        print("=" * 60)

    finally:
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
        # Also remove backup if created
        backup_dir = Path(temp_path).parent / "backups"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)

if __name__ == "__main__":
    test_item_removal()
