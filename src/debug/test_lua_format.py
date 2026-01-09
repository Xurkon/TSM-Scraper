"""
Test script to verify the lua_writer produces correct formatting
"""

import sys
import os
import tempfile
import shutil

# Add the project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tsm_scraper.lua_writer import TSMLuaWriter

# Sample minimal TSM file content (Ascension format with empty items/groups)
SAMPLE_TSM_CONTENT = '''
TradeSkillMasterAppDB = nil
AscensionTSMDB = {
	["global"] = {
		["infoMessage"] = 1001,
	},
	["profiles"] = {
		["Default"] = {
			["groupTreeStatus"] = {},
			["groups"] = {
				["TestGroup"] = {
					["Mailing"] = {
						"", -- [1]
					},
					["Auctioning"] = {
						"", -- [1]
					},
					["Crafting"] = {
						"", -- [1]
					},
					["Shopping"] = {
						"", -- [1]
					},
					["Warehousing"] = {
						"", -- [1]
					},
				},
			},
			["items"] = {
			},
			["operations"] = {
				["Mailing"] = {
				},
				["Auctioning"] = {
				},
			},
		},
	},
}
TradeSkillMasterDB = nil
'''

def test_add_items():
    """Test that add_items produces correct formatting"""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False, encoding='utf-8') as f:
        f.write(SAMPLE_TSM_CONTENT)
        temp_path = f.name
    
    try:
        writer = TSMLuaWriter(temp_path)
        
        # Test adding items
        test_items = {
            12345: "TestGroup",
            67890: "TestGroup`Subgroup",
        }
        
        result = writer.add_items(test_items, dry_run=False)
        print(f"add_items result: {result}")
        
        # Read the result
        with open(temp_path, 'r', encoding='utf-8') as f:
            output_content = f.read()
        
        print("\n=== Output Content (items section) ===")
        # Find and print the items section
        start = output_content.find('["items"]')
        if start != -1:
            end = output_content.find('["operations"]', start)
            if end != -1:
                items_section = output_content[start:end]
                print(items_section)
        
        # Check for formatting issues
        print("\n=== Format Checks ===")
        
        # Check 1: No double closing braces
        if '},},' in output_content:
            print("ERROR: Found },}, (malformed closing braces)")
        else:
            print("OK: No },}, found")
        
        # Check 2: Items have correct indentation (4 tabs)
        if '\t\t\t\t["item:' in output_content:
            print("OK: Items have correct 4-tab indentation")
        else:
            print("WARNING: Items may not have correct indentation")
        
        # Check 3: Items table closing has correct indentation (3 tabs)
        # Look for the items table closing
        if '\t\t\t},' in output_content:
            print("OK: Found 3-tab closing braces")
        
        return result['added'] == 2 and result['errors'] == []
        
    finally:
        # Cleanup
        os.unlink(temp_path)
        backup_dir = os.path.dirname(temp_path) + "/backups"
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)

if __name__ == "__main__":
    success = test_add_items()
    print(f"\n=== Test {'PASSED' if success else 'FAILED'} ===")
    sys.exit(0 if success else 1)
