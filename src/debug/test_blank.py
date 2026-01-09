"""Test what happens with a truly blank TSM file - ACTUALLY WRITE."""
import sys
import os
sys.path.insert(0, '.')

from tsm_scraper.lua_writer import TSMLuaWriter

# Blank file structure (what user provided)
blank_content = '''
TradeSkillMasterAppDB = nil
AscensionTSMDB = {
	["global"] = {
		["frameStatus"] = {
			["TSMDestroyingFrame"] = {
				["y"] = 450,
				["x"] = 850,
			},
		},
		["infoMessage"] = 1001,
	},
	["profiles"] = {
		["Default"] = {
			["design"] = {
				["fonts"] = {
					["content"] = "Arial Narrow",
				},
			},
			["groupTreeStatus"] = {
				["groups"] = {
					true,
					["1"] = true,
				},
			},
			["operations"] = {
				["Mailing"] = {
				},
			},
		},
	},
}
TradeSkillMasterDB = nil
'''

# Save to temp file
temp_path = 'temp_blank_tsm.lua'
with open(temp_path, 'w') as f:
    f.write(blank_content)

print(f"Created temp file: {temp_path}")
print(f"Original size: {os.path.getsize(temp_path)} bytes")

# Now test the writer - NOT DRY RUN
writer = TSMLuaWriter(temp_path)

# Test adding items
test_items = {
    12345: "Test`Group",
    67890: "Test`Group2",
}

print("\n=== Calling add_items (NOT dry_run) ===")
result = writer.add_items(test_items, dry_run=False)
print(f"Result: {result}")

# Read the file back
print(f"\nNew size: {os.path.getsize(temp_path)} bytes")

with open(temp_path, 'r') as f:
    new_content = f.read()

print(f"\n=== Content after write ===")
print(new_content)

# Also check if items are in the file
import re
items_match = re.findall(r'\["item:\d+:', new_content)
print(f"\n=== Found {len(items_match)} item entries ===")
