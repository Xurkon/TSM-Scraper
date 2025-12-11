"""
Lua Writer for TSM SavedVariables files.

Writes new item assignments back to TradeSkillMaster.lua while preserving
existing structure and formatting.
"""

import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class TSMLuaWriter:
    """Writer for TSM SavedVariables Lua files."""
    
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.backup_dir = self.filepath.parent / "backups"
        
    def create_backup(self) -> Optional[Path]:
        """Create a timestamped backup of the file."""
        if not self.filepath.exists():
            return None
        
        self.backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"TradeSkillMaster_{timestamp}.lua"
        
        shutil.copy2(self.filepath, backup_path)
        return backup_path
    
    def add_items(self, items: Dict[int, str], dry_run: bool = False) -> Dict[str, any]:
        """
        Add new items to the TSM saved variables.
        
        Args:
            items: Dict of item_id -> group_path
            dry_run: If True, don't actually modify the file
            
        Returns:
            Dict with 'added', 'skipped', 'errors' counts
        """
        result = {'added': 0, 'skipped': 0, 'errors': [], 'items_added': []}
        
        # Read current content
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            result['errors'].append(f"Failed to read file: {e}")
            return result
        
        # Find existing items
        existing_pattern = r'\["item:(\d+):'
        existing_ids = set(int(m) for m in re.findall(existing_pattern, content))
        
        # Find the [S] table insertion point
        # We'll insert before the closing of that table
        # Look for the pattern that ends the item list section
        
        # Find the last item entry in the [S] table
        s_table_pattern = r'(\["item:\d+:\d+:\d+:\d+:\d+:\d+:\d+"\]\s*=\s*"[^"]+",?\s*\n)'
        matches = list(re.finditer(s_table_pattern, content))
        
        if not matches:
            result['errors'].append("Could not find [S] table or item entries in file")
            return result
        
        # Insert after the last item entry
        last_match = matches[-1]
        insert_position = last_match.end()
        
        # Build new entries
        new_entries = []
        for item_id, group_path in items.items():
            if item_id in existing_ids:
                result['skipped'] += 1
                continue
            
            # Format: ["item:ID:0:0:0:0:0:0"] = "Group`Path",
            entry = f'\t\t\t\t["item:{item_id}:0:0:0:0:0:0"] = "{group_path}",\n'
            new_entries.append(entry)
            result['items_added'].append((item_id, group_path))
            result['added'] += 1
        
        if not new_entries:
            return result
        
        # Insert new entries
        new_content = content[:insert_position] + ''.join(new_entries) + content[insert_position:]
        
        if not dry_run:
            # Create backup first
            backup_path = self.create_backup()
            if backup_path:
                print(f"Backup created: {backup_path}")
            
            # Write new content
            try:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            except Exception as e:
                result['errors'].append(f"Failed to write file: {e}")
        
        return result
    
    def ensure_group_exists(self, group_path: str, content: str) -> str:
        """
        Ensure a group path exists in the groups table.
        
        If the group doesn't exist, create it with default settings.
        """
        # Check if group exists
        escaped_path = re.escape(group_path)
        if re.search(rf'\["{escaped_path}"\]\s*=\s*\{{', content):
            return content  # Group exists
        
        # Find the groups table and add the new group
        # Pattern to find groups table
        groups_pattern = r'(\["groups"\]\s*=\s*\{)'
        match = re.search(groups_pattern, content)
        
        if not match:
            return content  # Can't find groups table
        
        insert_pos = match.end()
        
        # Create group entry with default TSM settings
        group_entry = f'''
\t\t\t\t["{group_path}"] = {{
\t\t\t\t\t["Mailing"] = {{
\t\t\t\t\t\t"", -- [1]
\t\t\t\t\t}},
\t\t\t\t\t["Auctioning"] = {{
\t\t\t\t\t\t"AlwaysUndercut", -- [1]
\t\t\t\t\t}},
\t\t\t\t\t["Crafting"] = {{
\t\t\t\t\t\t"", -- [1]
\t\t\t\t\t}},
\t\t\t\t\t["Shopping"] = {{
\t\t\t\t\t\t"", -- [1]
\t\t\t\t\t}},
\t\t\t\t\t["Warehousing"] = {{
\t\t\t\t\t\t"", -- [1]
\t\t\t\t\t}},
\t\t\t\t}},'''
        
        new_content = content[:insert_pos] + group_entry + content[insert_pos:]
        return new_content
    
    def remove_items(self, item_ids: List[int], dry_run: bool = False) -> Dict[str, any]:
        """
        Remove items from the TSM saved variables.
        
        Args:
            item_ids: List of item IDs to remove
            dry_run: If True, don't actually modify the file
            
        Returns:
            Dict with 'removed', 'not_found' counts
        """
        result = {'removed': 0, 'not_found': 0, 'errors': []}
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            result['errors'].append(f"Failed to read file: {e}")
            return result
        
        ids_to_remove = set(item_ids)
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # Check if this line contains an item we want to remove
            match = re.search(r'\["item:(\d+):', line)
            if match and int(match.group(1)) in ids_to_remove:
                result['removed'] += 1
                ids_to_remove.remove(int(match.group(1)))
                continue  # Skip this line
            new_lines.append(line)
        
        result['not_found'] = len(ids_to_remove)
        
        if not dry_run and result['removed'] > 0:
            backup_path = self.create_backup()
            if backup_path:
                print(f"Backup created: {backup_path}")
            
            try:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
            except Exception as e:
                result['errors'].append(f"Failed to write file: {e}")
        
        return result


def main():
    """Test the writer."""
    import sys
    
    filepath = r"c:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\TradeSkillMaster.lua"
    writer = TSMLuaWriter(filepath)
    
    # Test dry run
    test_items = {
        999999: "Test`Group",
        999998: "Test`Group`SubGroup"
    }
    
    result = writer.add_items(test_items, dry_run=True)
    print(f"Dry run result: {result}")


if __name__ == "__main__":
    main()
