"""
Test to compare working .bak format vs tool-generated format
"""
import re

# Read working file
with open(r"C:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\TradeSkillMaster.lua.bak", 'r', encoding='utf-8') as f:
    working_content = f.read()

# Read current file 
with open(r"C:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\TradeSkillMaster.lua", 'r', encoding='utf-8') as f:
    current_content = f.read()

print("=== WORKING FILE (.bak) ===")
print(f"Size: {len(working_content)} bytes")

# Find groups table structure
groups_match = re.search(r'\["groups"\]\s*=\s*\{', working_content[500:])  # Skip groupTreeStatus
if groups_match:
    print(f"\nGroups table starts at position ~{500 + groups_match.start()}")

# Find items table
items_match = re.search(r'\["items"\]\s*=\s*\{', working_content)
if items_match:
    print(f"Items table starts at position {items_match.start()}")
    # Show first few items
    items_start = items_match.end()
    items_sample = working_content[items_start:items_start+500]
    print(f"\nItems sample:\n{items_sample}")

# Extract a working group structure
print("\n--- Working group structure (first group) ---")
group_match = re.search(r'\["Tools"\]\s*=\s*\{[^}]+\["Mailing"\][^}]+\}[^}]+\}', working_content, re.DOTALL)
if group_match:
    print(working_content[group_match.start():group_match.start()+300])

print("\n" + "="*60)
print("=== CURRENT FILE (tool-generated) ===")
print(f"Size: {len(current_content)} bytes")

# Find items table
items_match = re.search(r'\["items"\]\s*=\s*\{', current_content)
if items_match:
    print(f"Items table starts at position {items_match.start()}")
    items_start = items_match.end()
    items_sample = current_content[items_start:items_start+500]
    print(f"\nItems sample:\n{items_sample}")
else:
    print("NO ITEMS TABLE FOUND!")

# Extract a current group structure
print("\n--- Current group structure (Transmog`Axes`One Hand) ---")
group_match = re.search(r'\["Transmog`Axes`One Hand"\]\s*=\s*\{[^}]+\["Mailing"\][^}]+\}[^}]+\}', current_content, re.DOTALL)
if group_match:
    print(current_content[group_match.start():group_match.start()+350])
else:
    print("Group Transmog`Axes`One Hand not found!")

# Key comparison: Line endings
print("\n" + "="*60)
print("=== LINE ENDING ANALYSIS ===")
working_crlf = working_content.count('\r\n')
working_lf = working_content.count('\n') - working_crlf
current_crlf = current_content.count('\r\n')
current_lf = current_content.count('\n') - current_crlf

print(f"Working file: {working_crlf} CRLF, {working_lf} LF-only")
print(f"Current file: {current_crlf} CRLF, {current_lf} LF-only")

# Check for any mixed line endings in current file
if current_lf > 0 and current_crlf > 0:
    print("WARNING: Current file has MIXED line endings!")
