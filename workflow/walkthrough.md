# TSM Scraper Walkthrough - v3.4.20

## Latest Changes: Critical Lua Writer Fix

### What Was Fixed

#### 1. groupTreeStatus Separator

Fixed the key format in `groupTreeStatus.groups` table in [lua_writer.py](file:///C:/Ascension%20Launcher/resources/client/TSMItemScraper/tsm_scraper/lua_writer.py):

**Before (Broken):**
```lua
["1 TestGroup"] = true,
["1 TestGroup TestGroup`SubGroup"] = true,
```

**After (Correct):**
```lua
["1\x01TestGroup"] = true,
["1\x01TestGroup\x01TestGroup`SubGroup"] = true,
```

The separator is ASCII SOH (0x01), not a space character.

#### 2. Cumulative Path Chain

groupTreeStatus keys now build a cumulative path chain:
- `1\x01GroupName`
- `1\x01GroupName\x01GroupName`SubGroup``
- `1\x01GroupName\x01GroupName`SubGroup`\x01GroupName`SubGroup`SubSub``

#### 3. Auctioning Operation Template

Reverted the default Auctioning operation from `"AlwaysUndercut"` back to empty string `""` to match native TSM behavior.

---

## Previous Changes

### v3.4.18 - Linux/Wine Compatibility

- Wine/Bottles/Proton detection
- Smart path fallback for config/logs
- Crash logging for debugging

### v3.4.15 - NameError Fix

- Fixed critical crash in lua_writer.py

---

## Files Modified in v3.4.20

- [lua_writer.py](file:///C:/Ascension%20Launcher/resources/client/TSMItemScraper/tsm_scraper/lua_writer.py) - Fixed groupTreeStatus separator, operation templates
- [CHANGELOG.md](file:///C:/Ascension%20Launcher/resources/client/TSMItemScraper/CHANGELOG.md) - Version history
