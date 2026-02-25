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
    
    def detect_tsm_format(self, content: str) -> str:
        """
        Detect if file uses WotLK/Ascension format or Retail format.
        
        Returns:
            'ascension' - Uses AscensionTSMDB with nested profiles structure
            'retail' - Uses TradeSkillMasterDB with flat group keys
            'unknown' - Format not recognized
        """
        if 'AscensionTSMDB' in content:
            return 'ascension'
        elif 'TradeSkillMasterDB' in content and 'TradeSkillMasterDB = nil' not in content:
            return 'retail'
        return 'unknown'
        
    def create_backup(self) -> Optional[Path]:
        """Create a timestamped backup of the file."""
        if not self.filepath.exists():
            return None
        
        self.backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"TradeSkillMaster_{timestamp}.lua"
        
        shutil.copy2(self.filepath, backup_path)
        return backup_path
    
    def ensure_group_exists(self, group_path: str, content: str) -> str:
        """
        Ensure a group path exists in the TSM SavedVariables.
        
        Handles both formats:
        - Ascension: Groups stored in AscensionTSMDB.profiles.Default.groups
        - Retail: Groups stored as top-level keys in TradeSkillMasterDB
        """
        tsm_format = self.detect_tsm_format(content)
        
        if tsm_format == 'retail':
            # Check if group exists (flat structure)
            escaped_path = re.escape(group_path)
            if re.search(rf'\["{escaped_path}"\]\s*=\s*\{{', content):
                return content
            return self._ensure_group_exists_retail(group_path, content)
        
        # Default/Ascension format
        # First, find where groups are actually stored for the active profile
        match_info = self._find_real_groups_table(content)
        if not match_info:
            # If not found at all, we'll let _ensure_group_exists_ascension handle creation
            return self._ensure_group_exists_ascension(group_path, content)
            
        real_groups_match, real_groups_end_pos = match_info
        
        # Check for existence ONLY within the real groups table content
        # Find the closing brace for this table
        brace_count = 1
        search_pos = real_groups_match.end()
        while search_pos < len(content) and brace_count > 0:
            if content[search_pos] == '{':
                brace_count += 1
            elif content[search_pos] == '}':
                brace_count -= 1
            search_pos += 1
            
        real_groups_content = content[real_groups_match.end():search_pos-1]
        
        # Robust check for existence that handles backticks correctly
        escaped_path = re.escape(group_path)
        # Lua keys for groups in this table are always formatted as ["Path"] = {
        # Using {{ for a single { in f-string regex
        search_pattern = rf'\["{escaped_path}"\]\s*=\s*\{{'
        
        if re.search(search_pattern, real_groups_content):
            return content # Group already exists in the correct table
            
        return self._ensure_group_exists_ascension(group_path, content)

    def _find_real_groups_table(self, content: str) -> Optional[tuple]:
        """
        Locates the real ["groups"] table in Ascension format, avoiding UI state tables.
        Returns (Match object, end_position) or None.
        """
        groups_matches = list(re.finditer(r'\["groups"\]\s*=\s*\{', content))
        
        for match in groups_matches:
            # Check context - look backwards for groupTreeStatus
            start_check = max(0, match.start() - 500)
            preceding_text = content[start_check:match.start()]
            
            if '["groupTreeStatus"]' in preceding_text:
                gts_pos = preceding_text.rfind('["groupTreeStatus"]')
                segment = preceding_text[gts_pos:]
                if segment.count('{') > segment.count('}'):
                    continue # Inside groupTreeStatus
            
            # Look ahead to verify content
            brace_count = 1
            search_pos = match.end()
            while search_pos < len(content) and brace_count > 0:
                if content[search_pos] == '{':
                    brace_count += 1
                elif content[search_pos] == '}':
                    brace_count -= 1
                search_pos += 1
            
            if brace_count == 0:
                table_content = content[match.end():search_pos-1]
                # Real groups table contains nested tables or is empty but sibling to others
                # Fake ones contain true/false or simple IDs
                if 'true,' in table_content or '= true' in table_content:
                    continue
                    
                return (match, search_pos)
                
        return None
    
    def _ensure_group_exists_ascension(self, group_path: str, content: str) -> str:
        """
        Add a group to Ascension TSM format.
        
        Ascension TSM stores groups at:
        AscensionTSMDB.profiles.Default.groups.GroupName = { ... }
        """
        # First, we need to find the REAL ["groups"] table, avoiding groupTreeStatus
        groups_matches = list(re.finditer(r'\["groups"\]\s*=\s*\{', content))
        real_groups_end_pos = None
        
        for match in groups_matches:
            # Check context - look backwards for groupTreeStatus
            start_check = max(0, match.start() - 500)
            preceding_text = content[start_check:match.start()]
            
            if '["groupTreeStatus"]' in preceding_text:
                gts_pos = preceding_text.rfind('["groupTreeStatus"]')
                segment = preceding_text[gts_pos:]
                if segment.count('{') > segment.count('}'):
                    continue # Inside groupTreeStatus
            
            # Look ahead to see content
            brace_count = 1
            search_pos = match.end()
            while search_pos < len(content) and brace_count > 0:
                if content[search_pos] == '{':
                    brace_count += 1
                elif content[search_pos] == '}':
                    brace_count -= 1
                search_pos += 1
            
            table_content = content[match.end():search_pos-1]
            
            # Check for tell-tale signs of groupTreeStatus
            if 'true,' in table_content or '= true' in table_content:
                continue # Likely groupTreeStatus content or just boolean flags
                
            # This is the real groups table
            real_groups_end_pos = search_pos - 1
            break
        
        if real_groups_end_pos:
            insert_pos = real_groups_end_pos
            
            # Determine indentation - groups are at 4 tabs, groups table closing is at 3 tabs
            group_indent = "\t\t\t\t"
            table_indent = "\t\t\t"
            
            # The group entry (without trailing comma - we handle that separately)
            # The group entry - removed leading newline and streamlined
            group_entry = f'{group_indent}["{group_path}"] = {{\n' \
                          f'{group_indent}\t["Mailing"] = {{\n' \
                          f'{group_indent}\t\t"", -- [1]\n' \
                          f'{group_indent}\t}},\n' \
                          f'{group_indent}\t["Auctioning"] = {{\n' \
                          f'{group_indent}\t\t"", -- [1]\n' \
                          f'{group_indent}\t}},\n' \
                          f'{group_indent}\t["Crafting"] = {{\n' \
                          f'{group_indent}\t\t"", -- [1]\n' \
                          f'{group_indent}\t}},\n' \
                          f'{group_indent}\t["Shopping"] = {{\n' \
                          f'{group_indent}\t\t"", -- [1]\n' \
                          f'{group_indent}\t}},\n' \
                          f'{group_indent}\t["Warehousing"] = {{\n' \
                          f'{group_indent}\t\t"", -- [1]\n' \
                          f'{group_indent}\t}}\n' \
                          f'{group_indent}}}'
            
            # Find what character is before the insert position (skipping whitespace)
            prev_char_idx = insert_pos - 1
            while prev_char_idx > 0 and content[prev_char_idx] in ' \t\r\n':
                prev_char_idx -= 1
            
            # Check what's after insert_pos - it should be the closing } of groups table + comma
            # We need to handle this carefully to avoid },}, malformation
            
            # Find the line start of the closing brace
            line_start = content.rfind('\n', 0, insert_pos)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1
            
            # What's on the current line before the closing brace?
            line_before_close = content[line_start:insert_pos]
            
            if content[prev_char_idx] == '{':
                # Empty table - insert group then add proper closing
                # We're replacing from after { to the closing }
                # Result: { + group_entry + \n\t\t\t}
                new_content = group_entry + ",\n" + table_indent
                content = content[:insert_pos] + new_content + content[insert_pos:]
            else:
                # Table has content - add comma after previous entry, then our group
                prefix = ""
                if content[prev_char_idx] != ',':
                    prefix = ","
                # Insert our group with comma, then ensure proper newline before closing brace
                new_content = prefix + group_entry + ",\n" + table_indent
                content = content[:insert_pos] + new_content + content[insert_pos:]
            
            return content

        # If we didn't find the groups table, we need to create it.
        # This logic should generally be handled by _ensure_items... which often runs first or concurrently,
        # but if we are just adding a group, we need to create the groups table ourselves.
        
        # Similar fallback logic to _ensure_items...
        op_match = re.search(r'\["operations"\]\s*=\s*\{', content)
        if op_match:
            insert_pos = op_match.start()
            
            # Get indentation
            line_start = content.rfind('\n', 0, insert_pos) + 1
            indent = content[line_start:insert_pos]
            if not indent.strip() == "":
                 indent = "\t\t\t"
                 
            # Create groups table with our group inside
            group_entry = f'''["groups"] = {{
{indent}\t["{group_path}"] = {{
{indent}\t\t["Mailing"] = {{
{indent}\t\t\t"", -- [1]
{indent}\t\t}},
{indent}\t\t["Auctioning"] = {{
{indent}\t\t\t"", -- [1]
{indent}\t\t}},
{indent}\t\t["Crafting"] = {{
{indent}\t\t\t"", -- [1]
{indent}\t\t}},
{indent}\t\t["Shopping"] = {{
{indent}\t\t\t"", -- [1]
{indent}\t\t}},
{indent}\t\t["Warehousing"] = {{
{indent}\t\t\t"", -- [1]
{indent}\t\t}},
{indent}\t}},
{indent}}},\r\n{indent}'''
            
            content = content[:insert_pos] + group_entry + content[insert_pos:]
            return content

        return content
    
    def _ensure_group_tree_status_ascension(self, group_path: str, content: str) -> str:
        """
        Add a group to the groupTreeStatus.groups table in Ascension TSM format.
        
        Format uses SOH (0x01) as separator and builds a cumulative path:
        ["1\x01GroupName"] = true (for top-level)
        ["1\x01GroupName\x01GroupName`SubGroup"] = true (for children)
        ["1\x01GroupName\x01GroupName`SubGroup\x01GroupName`SubGroup`SubSub"] = true (deeper)
        """
        # Find groupTreeStatus -> groups table
        gts_pattern = r'\["groupTreeStatus"\]\s*=\s*\{'
        gts_match = re.search(gts_pattern, content)
        if not gts_match:
            return content
            
        # Find the nested ["groups"] table inside groupTreeStatus
        brace_count = 1
        search_pos = gts_match.end()
        gts_end = -1
        while search_pos < len(content) and brace_count > 0:
            if content[search_pos] == '{':
                brace_count += 1
            elif content[search_pos] == '}':
                brace_count -= 1
            search_pos += 1
        gts_end = search_pos
        
        gts_content = content[gts_match.end():gts_end]
        sub_groups_match = re.search(r'\["groups"\]\s*=\s*\{', gts_content)
        if not sub_groups_match:
            return content
            
        inner_groups_start = gts_match.end() + sub_groups_match.end()
        
        brace_count = 1
        search_pos = inner_groups_start
        while search_pos < len(content) and brace_count > 0:
            if content[search_pos] == '{':
                brace_count += 1
            elif content[search_pos] == '}':
                brace_count -= 1
            search_pos += 1
        inner_groups_end = search_pos - 1
        
        inner_groups_content = content[inner_groups_start:inner_groups_end]
        
        # Prepare the key - uses space separator and builds cumulative path for Ascension
        # Example: "1 TestGroup TestGroup`SubGroup TestGroup`SubGroup`SubSub"
        parts = group_path.split('`')
        path_parts = ["1"]  # Always starts with "1"
        for i in range(len(parts)):
            # Build cumulative path: first part alone, then with each backtick segment
            cumulative_path = '`'.join(parts[:i+1])
            path_parts.append(cumulative_path)
        gts_key = " ".join(path_parts)
            
        # Check if already exists
        escaped_key = re.escape(gts_key)
        if re.search(rf'\["{escaped_key}"\]\s*=\s*true', inner_groups_content):
            return content
            
        # Insert inside groups table
        indent = "\t\t\t\t\t"
        new_entry = f'\n{indent}["{gts_key}"] = true,'
        
        return content[:inner_groups_end] + new_entry + content[inner_groups_end:]
    
    def _ensure_items_table_exists_ascension(self, content: str) -> str:
        """
        Create ["items"] table in Ascension TSM format if it doesn't exist.
        
        The items table should be at:
        AscensionTSMDB.profiles.Default.items = { ... }
        
        Critically, we must distinguish between:
        1. The REAL groups table: ["groups"] = { ["GroupName"] = { ... } } or ["groups"] = { }
        2. The UI status groups table: ["groupTreeStatus"] ... ["groups"] = { true, ["1"] = true }
        
        Our strategy:
        1. Parse the file to find the real ["groups"] table by checking its content.
        2. If found, insert ["items"] after it.
        3. If not found (blank profile), find ["operations"] and insert BOTH ["groups"] and ["items"] before it.
        """
        # 1. Check if ["items"] already exists in a valid location
        # A valid ["items"] table usually contains "item:ID" keys OR is empty but parallel to operations/groups
        # We search specifically for ["items"] that is NOT inside groupTreeStatus
        
        # Find all occurrences of ["items"] = {
        items_matches = list(re.finditer(r'\["items"\]\s*=\s*\{', content))
        for match in items_matches:
            # Check context - look backwards for groupTreeStatus
            start_check = max(0, match.start() - 500)
            preceding_text = content[start_check:match.start()]
            
            # If we see groupTreeStatus without a closing brace before us, we are inside it
            # This is a heuristic; a perfect parser would be better but this covers 99% of TSM files
            if '["groupTreeStatus"]' in preceding_text:
                gts_pos = preceding_text.rfind('["groupTreeStatus"]')
                segment = preceding_text[gts_pos:]
                if segment.count('{') > segment.count('}'):
                    continue # We are inside groupTreeStatus, skip this match
            
            # This looks like a valid items table
            return content

        # 2. If we are here, we need to create the items table.
        # First, let's try to find the REAL ["groups"] table to insert after.
        
        groups_matches = list(re.finditer(r'\["groups"\]\s*=\s*\{', content))
        real_groups_end_pos = None
        
        for match in groups_matches:
            # Check if this is the groupTreeStatus fake
            start_check = max(0, match.start() - 500)
            preceding_text = content[start_check:match.start()]
            
            if '["groupTreeStatus"]' in preceding_text:
                gts_pos = preceding_text.rfind('["groupTreeStatus"]')
                segment = preceding_text[gts_pos:]
                # If unclosed, it's inside groupTreeStatus
                if segment.count('{') > segment.count('}'):
                    continue

            # Look ahead to see if the content looks like real groups (nested tables) or boolean flags
            # Real groups: ["GroupName"] = {
            # Fake groups: true, or ["1"] = true
            
            # Find the closing brace for this table
            brace_count = 1
            search_pos = match.end()
            while search_pos < len(content) and brace_count > 0:
                if content[search_pos] == '{':
                    brace_count += 1
                elif content[search_pos] == '}':
                    brace_count -= 1
                search_pos += 1
            
            table_content = content[match.end():search_pos-1]
            
            # Check for tell-tale signs of groupTreeStatus
            if 'true,' in table_content or '= true' in table_content:
                continue # This is likely groupTreeStatus content
                
            # If we are here, it's likely the real groups table (even if empty)
            real_groups_end_pos = search_pos
            break
            
        if real_groups_end_pos:
            # FOUND IT! Insert items after the groups table
            # Handle comma if present
            insert_pos = real_groups_end_pos
            while insert_pos < len(content) and content[insert_pos] in ' \t\r\n':
                insert_pos += 1
            if insert_pos < len(content) and content[insert_pos] == ',':
                insert_pos += 1
                
            items_section = '\r\n\t\t\t["items"] = {\r\n\t\t\t},\r\n\t\t\t["groupTreeCollapsedStatus"] = {\r\n\t\t\t},\r\n\t\t\t["isBankui"] = false,\r\n\t\t\t["moveImportedItems"] = true,'
            content = content[:insert_pos] + items_section + content[insert_pos:]
            return content

        # 3. If no real groups table found, this is a FRESH profile.
        # We should insert both ["groups"] and ["items"] before ["operations"].
        # ["operations"] is a standard TSM table that should essentially always exist.
        
        op_match = re.search(r'\["operations"\]\s*=\s*\{', content)
        if op_match:
            insert_pos = op_match.start()
            
            # Get indentation from the existing line
            line_start = content.rfind('\n', 0, insert_pos) + 1
            indent = content[line_start:insert_pos]
            if not indent.strip() == "": # If we didn't catch just indentation
                indent = "\t\t\t" # Default fallback
            
            new_tables = f'["groups"] = {{\r\n{indent}}},\r\n{indent}["items"] = {{\r\n{indent}}},\r\n' \
                         f'{indent}["groupTreeCollapsedStatus"] = {{\r\n{indent}}},\r\n' \
                         f'{indent}["isBankui"] = false,\r\n' \
                         f'{indent}["moveImportedItems"] = true,\r\n{indent}'
            content = content[:insert_pos] + new_tables + content[insert_pos:]
            return content
            
        # 4. Total fallback - insert into Default table
        default_match = re.search(r'\["Default"\]\s*=\s*\{', content)
        if default_match:
            content = content[:default_match.end()] + '\r\n\t\t\t["groups"] = {\r\n\t\t\t},\r\n\t\t\t["items"] = {\r\n\t\t\t},' + content[default_match.end():]
            
        return content
    
    def _find_real_items_table(self, content: str) -> Optional[re.Match]:
        """
        Finds the match object for the real ["items"] table, avoiding false positives 
        in groupTreeStatus or other UI state tables.
        """
        items_matches = list(re.finditer(r'\["items"\]\s*=\s*\{', content))
        
        for match in items_matches:
            # Check context - look backwards for groupTreeStatus
            start_check = max(0, match.start() - 500)
            preceding_text = content[start_check:match.start()]
            
            if '["groupTreeStatus"]' in preceding_text:
                gts_pos = preceding_text.rfind('["groupTreeStatus"]')
                segment = preceding_text[gts_pos:]
                # Simple check: if we are inside the braces of groupTreeStatus
                if segment.count('{') > segment.count('}'):
                    continue 
            
            # Check content inside the table for tell-tale signs
            # Look ahead to see content
            brace_count = 1
            search_pos = match.end()
            while search_pos < len(content) and brace_count > 0:
                if content[search_pos] == '{':
                    brace_count += 1
                elif content[search_pos] == '}':
                    brace_count -= 1
                search_pos += 1
            
            table_content = content[match.end():search_pos-1]
            
            # If it's inside groupTreeStatus, it might look like ["items"] = { ["1"] = true }
            if 'true,' in table_content or '= true' in table_content:
                continue
                
            return match
            
        return None

    def _ensure_group_exists_retail(self, group_path: str, content: str) -> str:
        """
        Add a group to Retail TSM format.
        
        Retail TSM stores groups as top-level keys in TradeSkillMasterDB.
        """
        # Find the TradeSkillMasterDB opening brace to insert after
        db_pattern = r'(TradeSkillMasterDB\s*=\s*\{)'
        match = re.search(db_pattern, content)
        
        if not match:
            return content  # Can't find database table
        
        insert_pos = match.end()
        
        # Create group entry with default TSM settings (retail format)
        group_entry = f'''\r
["{group_path}"] = {{\r
["Mailing"] = {{\r
"#Default",\r
}},\r
["Auctioning"] = {{\r
"#Default",\r
}},\r
["Crafting"] = {{\r
"#Default",\r
}},\r
["Warehousing"] = {{\r
"#Default",\r
}},\r
["Vendoring"] = {{\r
"#Default",\r
}},\r
["Shopping"] = {{\r
"#Default",\r
}},\r
}},'''
        
        new_content = content[:insert_pos] + group_entry + content[insert_pos:]
        return new_content
    
    def cleanup_ui_state(self, content: str) -> str:
        """
        Resets TSM UI state tables (groupTreeCollapsedStatus) to empty tables.
        Bypasses groupTreeStatus for Ascension to prevent wiping newly added entries.
        """
        # For Ascension, we only want to reset collapsed status, as groupTreeStatus is handled separately
        tables_to_reset = ['groupTreeCollapsedStatus']
        
        # If not ascension, maybe we can be more aggressive, but for now we follow the safe path
        for table_name in tables_to_reset:
            pattern = rf'\["{table_name}"\]\s*=\s*\{{'
            matches = list(re.finditer(pattern, content))
            
            for match in reversed(matches): # Process from end to avoid offsetting indices
                # Find the end of the table
                brace_count = 1
                search_pos = match.end()
                while search_pos < len(content) and brace_count > 0:
                    if content[search_pos] == '{':
                        brace_count += 1
                    elif content[search_pos] == '}':
                        brace_count -= 1
                    search_pos += 1
                
                if brace_count == 0:
                    full_match_start = match.start()
                    full_match_end = search_pos
                    content = content[:full_match_start] + f'["{table_name}"] = {{}}' + content[full_match_end:]
                    
        return content

    def add_groups(self, group_paths: List[str], dry_run: bool = False) -> Dict[str, any]:
        """
        Add multiple groups to the TSM saved variables.
        
        Args:
            group_paths: List of group paths (using backticks, e.g. "Armor`Cloth`Chest")
            dry_run: If True, don't actually modify the file
            
        Returns:
            Dict with 'added', 'skipped', 'errors' counts
        """
        result = {'added': 0, 'skipped': 0, 'errors': [], 'groups_added': []}
        
        # Read current content
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            result['errors'].append(f"Failed to read file: {e}")
            return result
        
        # Add each group
        # First, expand all paths to include their parents to ensure hierarchy exists
        expanded_groups = set()
        for group_path in group_paths:
            parts = group_path.split('`')
            for i in range(1, len(parts) + 1):
                parent_path = '`'.join(parts[:i])
                expanded_groups.add(parent_path)
                
        # Sort by length to add parents first (cosmetic preference, not strictly required)
        sorted_groups = sorted(list(expanded_groups), key=len)
                
        for group_path in sorted_groups:
            old_content = content
            content = self.ensure_group_exists(group_path, content)
            
            # For Ascension, also ensure groupTreeStatus entry exists
            if self.detect_tsm_format(content) == 'ascension':
                content = self._ensure_group_tree_status_ascension(group_path, content)
            
            if content != old_content:
                result['added'] += 1
                result['groups_added'].append(group_path)
            else:
                result['skipped'] += 1
        
        # Always clean UI state when modifying groups to force TSM to recognize changes
        content = self.cleanup_ui_state(content)
        
        if not dry_run:
            # Create backup first
            backup_path = self.create_backup()
            if backup_path:
                print(f"Backup created: {backup_path}")
            
            # Write new content
            try:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                result['errors'].append(f"Failed to write file: {e}")
        
        return result

    def add_items(self, items_dict: Dict[int, str], dry_run: bool = False) -> Dict[str, int]:
        """
        Add items to the TSM saved variables.
        
        In TSM 2.8 (Ascension format), items are stored inside an ["items"] table
        at the profile level: AscensionTSMDB.profiles.Default.items = { ... }
        
        Format: ["item:ID:0:0:0:0:0:0"] = "Group`Path", at 4-tab indentation
        """
        result = {'added': 0, 'skipped': 0, 'errors': []}
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            result['errors'].append(f"Failed to read file: {e}")
            return result

        tsm_format = self.detect_tsm_format(content)
        
        if tsm_format == 'ascension':
            # Ensure the ["items"] table exists first
            content = self._ensure_items_table_exists_ascension(content)
            
            # Find the REAL ["items"] table (avoiding groupTreeStatus)
            items_match = self._find_real_items_table(content)
            if not items_match:
                result['errors'].append("Could not find or create real ['items'] table.")
                return result
                
            insert_pos = items_match.end()
            indent = "\t\t\t\t"
        else:
            # For Retail or other formats, we might fallback or handle differently.
            # Currently focused on Ascension (TSM 2.8) fix.
            # Retail also uses a similar structure but top-level.
            # Let's stick to the Ascension fix for now as requested.
            result['errors'].append(f"Unsupported format for item addition: {tsm_format}")
            return result

        new_entries = []
        for item_id, group_path in items_dict.items():
            item_id = str(item_id).strip()
            # Format: ["item:1234:0:0:0:0:0:0"] = "Group`Name",
            entry_key = f'["item:{item_id}:0:0:0:0:0:0"]'
            
            # Check if this item already exists in the file (careful with exact match in content)
            # Use regex for safer matching of keys to avoid partial matches
            if re.search(rf'\["item:{item_id}:0:0:0:0:0:0"\]\s*=', content):
                result['skipped'] += 1
                continue
                
            new_entries.append(f'{indent}{entry_key} = "{group_path}",')
            result['added'] += 1

        if new_entries:
            # Build the insert block - use single line ending between entries
            new_block = "\n" + "\n".join(new_entries)

            # Insert INSIDE the items table (at the beginning of it)
            content = content[:insert_pos] + new_block + content[insert_pos:]
            
            # Reset UI state to ensure items show up in groups
            content = self.cleanup_ui_state(content)

            if not dry_run:
                self.create_backup()
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

        return result
    
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
    
    def rename_group(self, old_path: str, new_path: str, dry_run: bool = False) -> Dict[str, any]:
        """
        Rename a group and update all item references.
        
        Uses simple string replacement for safety - replaces all occurrences of
        the old group path with the new path in both group definitions and item assignments.
        
        Args:
            old_path: Current group path (e.g., "Armor`Cloth")
            new_path: New group path (e.g., "Armor`Cloth Items")
            dry_run: If True, don't actually modify the file
            
        Returns:
            Dict with 'renamed', 'items_updated', 'errors' counts
        """
        result = {'renamed': False, 'items_updated': 0, 'groups_updated': 0, 'errors': []}
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            result['errors'].append(f"Failed to read file: {e}")
            return result
        
        # Count occurrences before replacement
        old_count = content.count(f'"{old_path}"')
        old_subgroup_count = content.count(f'"{old_path}`')
        
        if old_count == 0 and old_subgroup_count == 0:
            result['errors'].append(f"Group not found: {old_path}")
            return result
        
        # Simple string replacement - safe and predictable
        # Replace exact matches: "OldPath" -> "NewPath"
        new_content = content.replace(f'"{old_path}"', f'"{new_path}"')
        
        # Replace as parent of subgroups: "OldPath` -> "NewPath`
        new_content = new_content.replace(f'"{old_path}`', f'"{new_path}`')
        
        # Count what was actually replaced
        new_count = new_content.count(f'"{new_path}"')
        new_subgroup_count = new_content.count(f'"{new_path}`')
        
        result['renamed'] = True
        result['groups_updated'] = old_count + old_subgroup_count
        result['items_updated'] = old_count  # Items use exact match
        
        if not dry_run:
            backup_path = self.create_backup()
            if backup_path:
                print(f"Backup created: {backup_path}")
            
            try:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            except Exception as e:
                result['errors'].append(f"Failed to write file: {e}")
        
        return result
    
    def delete_group(self, group_path: str, delete_items: bool = False, dry_run: bool = False) -> Dict[str, any]:
        """
        Delete a group from the TSM saved variables.
        
        Args:
            group_path: Group path to delete (e.g., "Armor`Cloth")
            delete_items: If True, also delete item assignments in this group
            dry_run: If True, don't actually modify the file
            
        Returns:
            Dict with 'deleted', 'items_removed', 'errors' counts
        """
        result = {'deleted': False, 'items_removed': 0, 'subgroups_removed': 0, 'errors': []}
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            result['errors'].append(f"Failed to read file: {e}")
            return result
        
        escaped_path = re.escape(group_path)
        
        # Use line-by-line approach to handle nested braces in group definitions
        lines = content.split('\n')
        new_lines = []
        skip_until_closed = False
        brace_depth = 0
        
        for line in lines:
            # Check if we're starting a group definition for this path or its subgroups
            if re.match(rf'\s*\["{escaped_path}("\]|`)', line) and '= {' in line:
                # Start skipping this group definition
                skip_until_closed = True
                brace_depth = line.count('{') - line.count('}')
                result['deleted'] = True
                continue
            
            # Check if we're starting a subgroup definition
            if re.match(rf'\s*\["{escaped_path}`[^"]+"\]\s*=\s*\{{', line):
                skip_until_closed = True
                brace_depth = line.count('{') - line.count('}')
                result['subgroups_removed'] += 1
                continue
            
            if skip_until_closed:
                brace_depth += line.count('{') - line.count('}')
                if brace_depth <= 0:
                    skip_until_closed = False
                    brace_depth = 0
                continue
            
            new_lines.append(line)
        
        new_content = '\n'.join(new_lines)

        # Remove item assignments
        lines = new_content.split('\n')
        new_lines = []
        items_found = 0
        for line in lines:
            # Check if line assigns item to this group or its subgroups
            if re.search(rf'=\s*"{escaped_path}(`.*)?"\s*,?', line):
                items_found += 1
                if delete_items:
                    result['items_removed'] += 1
                    continue  # Skip this line (delete the item)
            new_lines.append(line)
        new_content = '\n'.join(new_lines)

        # Remove ALL UI state references for this group and subgroups
        # This includes groupTreeStatus, groupTreeSelectedGroupStatus, and any other tables
        # that store group paths as keys or values (e.g., ["GroupPath"] = true/false)
        lines = new_content.split('\n')
        new_lines = []
        ui_refs_removed = 0
        for line in lines:
            # Check if line contains a reference to this group path
            # Match patterns like:
            # - ["GroupPath"] = true/false (groupTreeStatus entries)
            # - ["GroupPath`SubGroup"] = true/false
            # - ["1GroupPath..."] = true (with or without SOH separators)
            # - Any line with the group path as a key followed by = true/false
            if f'"{group_path}"' in line or f'"{group_path}`' in line:
                # This line references the group - check if it's a UI state entry
                # (contains = true, = false, or is a simple key reference)
                if '= true' in line or '= false' in line:
                    ui_refs_removed += 1
                    continue  # Skip this line
            # Also catch entries where group path appears at end of a compound key
            # e.g., ["1TransmogTransmog`Swords"] or with SOH separators
            if (f'{group_path}"]' in line or f'{group_path}`' in line) and ('= true' in line or '= false' in line):
                ui_refs_removed += 1
                continue
            new_lines.append(line)
        new_content = '\n'.join(new_lines)
        result['ui_refs_removed'] = ui_refs_removed

        # Clean up consecutive blank lines - reduce multiple blank lines to single blank line
        # This prevents blank line accumulation from repeated deletions
        while '\n\n\n' in new_content:
            new_content = new_content.replace('\n\n\n', '\n\n')

        # Also clean up blank lines inside tables (e.g., ["items"] = {\n\n\n\t\t\t})
        # These should have no blank lines between opening brace and content/closing brace
        new_content = re.sub(r'(\{\s*)\n\n+(\s*\})', r'\1\n\2', new_content)
        # Clean blank lines right after opening brace before content
        new_content = re.sub(r'(\{\s*)\n\n+(\s*\[)', r'\1\n\2', new_content)

        # Check if anything was found (group, subgroups, or items)
        if not result['deleted'] and result['subgroups_removed'] == 0 and items_found == 0:
            result['errors'].append(f"Group not found: {group_path}")
            return result

        if not dry_run:
            backup_path = self.create_backup()
            if backup_path:
                print(f"Backup created: {backup_path}")
            
            try:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
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
