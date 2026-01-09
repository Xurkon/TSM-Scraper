"""Compare structures between working and broken files."""
import re

# Reference file (working)
ref_path = r"C:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\FULLTradeSkillMaster.lua"
# Current file (not working)
cur_path = r"C:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\TradeSkillMaster.lua"

output = []

def analyze_file(filepath, name):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    output.append(f"\n=== {name} ===")
    output.append(f"Total size: {len(content)} bytes")
    
    # Check for ["items"] table
    items_match = re.search(r'\["items"\]\s*=\s*\{', content)
    if items_match:
        line = content[:items_match.start()].count('\n') + 1
        output.append(f'Found ["items"] at line {line}')
    else:
        output.append('No ["items"] table found!')
    
    # Check for item entries with group assignments
    item_group_pattern = r'\["item:\d+:\d+:\d+:\d+:\d+:\d+:\d+"\]\s*=\s*"[^"]+"'
    item_matches = list(re.finditer(item_group_pattern, content))
    output.append(f"Found {len(item_matches)} item-to-group assignments")
    
    # Find ["groups"] tables
    groups_matches = list(re.finditer(r'\["groups"\]\s*=\s*\{', content))
    output.append(f"Found {len(groups_matches)} groups tables")
    for i, m in enumerate(groups_matches):
        line = content[:m.start()].count('\n') + 1
        # Check if it's inside groupTreeStatus
        prev_200 = content[max(0, m.start()-200):m.start()]
        in_tree_status = 'groupTreeStatus' in prev_200 or 'groupTreeCollapsedStatus' in prev_200
        output.append(f"  Groups {i+1} at line {line}, in_tree_status={in_tree_status}")

analyze_file(ref_path, "REFERENCE (working)")
analyze_file(cur_path, "CURRENT (broken)")

# Write to file
with open('analysis_output.txt', 'w') as f:
    f.write('\n'.join(output))

print("Results saved to analysis_output.txt")
