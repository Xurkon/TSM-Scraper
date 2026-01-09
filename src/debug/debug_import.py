
import os
import sys
import re

# Add the parent directory to sys.path to import tsm_scraper
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '.')))

try:
    from tsm_scraper.lua_writer import TSMLuaWriter
except ImportError:
    # If that fails, try looking for it in the TSMItemScraper directory directly
    sys.path.append(os.path.abspath(os.getcwd()))
    from tsm_scraper.lua_writer import TSMLuaWriter

def test_add_item():
    filepath = r"C:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\TradeSkillMaster.lua"
    writer = TSMLuaWriter(filepath)
    
    # Try to add a test item
    items_dict = {1234: "TestGroup"}
    print(f"Adding item 1234 to TestGroup...")
    result = writer.add_items(items_dict, dry_run=True)
    
    print(f"Result: {result}")

if __name__ == "__main__":
    test_add_item()
