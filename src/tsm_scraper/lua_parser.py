"""
Lua Parser for TSM SavedVariables files.

This is where the magic happens for reading TSM's data. TSM stores everything
in Lua table format inside the SavedVariables folder. We need to parse this
to figure out what items are already in groups and what groups exist.

The tricky part is that WotLK/3.3.5a uses a different item format than retail:
- WotLK/Classic: "item:12345:0:0:0:0:0:0" (the old item link format)
- Retail TSM:    "i:12345" or "i:12345::bonusID1:bonusID2" (shorter, with optional bonuses)

We handle both formats so this tool works across all TSM versions.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple


class TSMLuaParser:
    """
    Parser for TSM SavedVariables Lua files.
    
    TSM stores its data in WoW's SavedVariables as a big Lua table.
    This parser reads that file and extracts the item-to-group mappings
    so we know what's already categorized.
    """
    
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.content = ""
        self.items: Dict[str, str] = {}  # Maps item strings like "item:12345:0:0..." to group paths
        self.groups: Set[str] = set()     # All the group paths we've found
        
    def load(self) -> bool:
        """
        Load the Lua file content into memory.
        
        Returns True if successful, False if the file couldn't be read.
        """
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.content = f.read()
            return True
        except Exception as e:
            print(f"Error loading file: {e}")
            return False
    
    def parse_items(self) -> Dict[str, str]:
        """
        Parse item assignments from the TSM data tables.
        
        This is the main parsing function. It uses regex to find all the
        item-to-group assignments in the Lua file. TSM stores these as:
        
        WotLK/3.3.5a format:
            ["item:12976:0:0:0:0:0:0"] = "Transmog`Swords`One Hand",
            
        Retail TSM format:
            ["i:220140"] = "Professions`Crafting",
            ["i:12345::4786:6652"] = "Some`Group",  (with bonus IDs)
        
        Returns a dict mapping item strings to their group paths.
        """
        self.items = {}
        
        # Pattern for WotLK/3.3.5a format: ["item:12976:0:0:0:0:0:0"] = "GroupPath",
        # The item: prefix followed by the ID and a bunch of :0 suffixes
        classic_pattern = r'\["(item:\d+(?::\d+)*?)"\]\s*=\s*"([^"]+)"'
        
        # Pattern for Retail format: ["i:12345"] or ["i:12345::bonuses"]
        # Retail uses a shorter 'i:' prefix and may have double colons before bonus IDs
        retail_pattern = r'\["(i:\d+(?::[\d:]+)?(?::[\d:]*)?)\\\"?\]\s*=\s*"([^"]+)"'
        
        # Simpler retail pattern for the common case: ["i:220140"] = "GroupPath"
        retail_simple_pattern = r'\["(i:\d+[:\d]*?)"\]\s*=\s*"([^"]+)"'
        
        # First, grab all the WotLK/3.3.5a format items
        matches = re.findall(classic_pattern, self.content)
        for item_key, group_path in matches:
            self.items[item_key] = group_path
            self.groups.add(group_path)
        
        # Now handle retail format items (both simple and with bonus IDs)
        for pattern in [retail_pattern, retail_simple_pattern]:
            matches = re.findall(pattern, self.content)
            for item_key, group_path in matches:
                # Clean up any trailing colons that might be left over
                item_key = item_key.rstrip(':')
                if item_key not in self.items:  # Don't overwrite if we already have it
                    self.items[item_key] = group_path
                    self.groups.add(group_path)
        
        return self.items
    
    def parse_groups(self) -> Set[str]:
        """
        Parse available group definitions.
        
        Extracts groups from:
        1. Item assignments (collected by parse_items)
        2. Retail format: ["GroupName`SubGroup"] = { at top level
        3. Ascension format: Groups inside ["profiles"]["Default"]["groups"] section
        """
        if not self.items:
            self.parse_items()
        
        # Detect if this is Ascension format
        if 'AscensionTSMDB' in self.content:
            # Ascension format: groups are inside ["profiles"]["Default"]["groups"]
            # Use brace-counting to properly extract the groups section
            # This handles arbitrarily nested structures
            
            groups_start = self.content.find('["groups"] = {')
            if groups_start == -1:
                groups_start = self.content.find('[\"groups\"] = {')
            
            if groups_start != -1:
                # Find the opening brace
                brace_start = self.content.find('{', groups_start)
                if brace_start != -1:
                    # Use brace counting to find matching closing brace
                    brace_depth = 1
                    pos = brace_start + 1
                    while pos < len(self.content) and brace_depth > 0:
                        if self.content[pos] == '{':
                            brace_depth += 1
                        elif self.content[pos] == '}':
                            brace_depth -= 1
                        pos += 1
                    
                    # Extract the groups section content
                    groups_content = self.content[brace_start + 1:pos - 1]
                    
                    # Find all group names: ["groupname"] = {
                    # Group names can be simple (testing) or with backticks (Armor`Cloth)
                    group_pattern = r'\[\"([^\"]+)\"\]\s*=\s*\{'
                    for match in re.finditer(group_pattern, groups_content):
                        group_name = match.group(1)
                        # Skip operation names (Mailing, Auctioning, etc.)
                        if group_name not in ['Mailing', 'Auctioning', 'Crafting', 'Shopping', 'Warehousing', 'Vendoring']:
                            self.groups.add(group_name)
        
        # Also look for retail format group definitions 
        # Pattern matches: ["Transmog`Swords`One Hand"] = { (with backticks)
        group_pattern = r'\["([^"]*`[^"]+)"\]\s*=\s*\{'
        matches = re.findall(group_pattern, self.content)
        for group in matches:
            self.groups.add(group)
        
        return self.groups
    
    def get_item_id(self, item_key: str) -> Optional[int]:
        """
        Extract the numeric item ID from an item key string.
        
        Supports both formats:
        - Classic: "item:12345:0:0:0:0:0:0" -> 12345
        - Retail:  "i:12345" or "i:12345::4786:6652" -> 12345
        """
        # Try retail format first (shorter prefix)
        match = re.match(r'i:(\d+)', item_key)
        if match:
            return int(match.group(1))
        
        # Try Classic format
        match = re.match(r'item:(\d+)', item_key)
        if match:
            return int(match.group(1))
        
        return None
    
    def is_retail_format(self, item_key: str) -> bool:
        """Check if an item key uses the retail format (i:ID)."""
        return item_key.startswith('i:')
    
    def get_format_type(self) -> str:
        """
        Detect the format type used in this file.
        
        Returns 'retail' if items use i: prefix, 'classic' otherwise.
        """
        if not self.items:
            self.parse_items()
        
        for item_key in self.items:
            if item_key.startswith('i:'):
                return 'retail'
        return 'classic'
    
    def get_existing_item_ids(self) -> Set[int]:
        """Get set of all item IDs already in the file."""
        if not self.items:
            self.parse_items()
        
        ids = set()
        for item_key in self.items:
            item_id = self.get_item_id(item_key)
            if item_id:
                ids.add(item_id)
        return ids
    
    def get_items_by_group(self, group_path: str) -> List[str]:
        """Get all item keys assigned to a specific group."""
        if not self.items:
            self.parse_items()
        
        return [key for key, grp in self.items.items() if grp == group_path]
    
    def get_group_hierarchy(self) -> Dict[str, List[str]]:
        """
        Build a hierarchy of groups.
        
        Returns dict where keys are parent paths and values are child group names.
        """
        if not self.groups:
            self.parse_groups()
        
        hierarchy: Dict[str, List[str]] = {}
        
        for group in sorted(self.groups):
            parts = group.split('`')
            for i in range(len(parts)):
                parent = '`'.join(parts[:i]) if i > 0 else ''
                child = '`'.join(parts[:i+1])
                
                if parent not in hierarchy:
                    hierarchy[parent] = []
                if child not in hierarchy[parent]:
                    hierarchy[parent].append(child)
        
        return hierarchy
    
    def find_s_table_location(self) -> Tuple[int, int]:
        """
        Find the location of the [S] (items) table in the file.
        
        Returns (start_line, end_line) of the table.
        """
        lines = self.content.split('\n')
        start = -1
        end = -1
        brace_count = 0
        in_s_table = False
        
        for i, line in enumerate(lines):
            # Look for the start of the [S] table
            if re.search(r'\["S"\]\s*=\s*\{', line) or re.search(r'\[S\]\s*=\s*\{', line):
                start = i
                in_s_table = True
                brace_count = line.count('{') - line.count('}')
                continue
            
            if in_s_table:
                brace_count += line.count('{') - line.count('}')
                if brace_count <= 0:
                    end = i
                    break
        
        return start, end
    
    def summary(self) -> str:
        """Return a summary of parsed data."""
        if not self.items:
            self.parse_items()
        if not self.groups:
            self.parse_groups()
        
        return (
            f"TSM SavedVariables Summary:\n"
            f"  File: {self.filepath}\n"
            f"  Total items: {len(self.items)}\n"
            f"  Total groups: {len(self.groups)}\n"
        )


def main():
    """Test the parser with the actual TSM file."""
    import sys
    
    if len(sys.argv) < 2:
        # Default path for testing
        filepath = r"c:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\TradeSkillMaster.lua"
    else:
        filepath = sys.argv[1]
    
    parser = TSMLuaParser(filepath)
    if parser.load():
        parser.parse_items()
        parser.parse_groups()
        print(parser.summary())
        
        print("\nTop 10 groups by item count:")
        group_counts = {}
        for group in parser.groups:
            count = len(parser.get_items_by_group(group))
            if count > 0:
                group_counts[group] = count
        
        for group, count in sorted(group_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {group}: {count} items")


if __name__ == "__main__":
    main()
