# Changelog

## [3.4.22] - 2026-01-07
### Fixed
- **Fixed Ascension DB URL filtering**: Armor slot filtering now correctly uses `&filter=sl=X` parameter instead of appending to items path (e.g., `?items=4.1&filter=sl=1` instead of `?items=4.1.1`).
- **Fixed armor "other" categories**: Cloaks, offhand, tabards, shirts now use correct negative subclass IDs (e.g., `?items=4.-6` for cloaks).
- **Fixed bind filter combination with slot filter**: Filter parts are now properly combined (e.g., `&filter=cr=3;crs=1;crv=0;sl=1`).
- **Fixed group deletion leaving blank lines**: Added cleanup logic to remove consecutive blank lines after deleting groups/items.

### Added
- **New armor categories**: amulet, ring, trinket, idol, libram, totem, sigil, armor_misc
- **New consumable categories**: elixir_battle, elixir_guardian, item_enhancement, item_enhancement_temp, consumable_other
- **New trade goods categories**: trade_parts, trade_explosives, trade_devices, trade_other, trade_materials, armor_enchantment, weapon_enchantment
- **New recipe categories**: recipe_book, recipe_fishing, recipe_inscription, recipe_mining
- **Full gem categories**: gem_red, gem_blue, gem_yellow, gem_purple, gem_green, gem_orange, gem_meta, gem_simple, gem_prismatic
- **Full container categories**: soul_bag, herb_bag, enchanting_bag, engineering_bag, gem_bag, mining_bag, leatherworking_bag, inscription_bag
- **Quiver categories**: quiver, quiver_arrows, ammo_pouch
- **Glyph categories**: All class-specific glyphs (warrior, paladin, hunter, rogue, priest, dk, shaman, mage, warlock, druid)
- **Ascension pet whistles**: beastmaster, blood_soaked, summoner, draconic, elemental
- **Additional categories**: quest, key, currency, misc

## [3.4.20] - 2026-01-06
### Fixed
- Fixed critical `groupTreeStatus` key format: now uses SOH (0x01) separator instead of space, matching actual TSM format.
- Fixed `groupTreeStatus` key generation to build cumulative path chain (e.g., `1\x01GroupName\x01GroupName\`SubGroup`).
- Reverted Auctioning operation template from "AlwaysUndercut" to empty string to match native TSM behavior.
- **Fixed Ascension DB bind filter**: BoE/BoP/BoU filter now properly appends `&filter=cr=X;crs=1;crv=0` to category URLs.

### Added
- **Wowhead to Ascension name matching**: New `search_by_name()` and `resolve_wowhead_items()` functions.
- **New categories**: offhand, tabard, shirt, drink, arrows, bullets, misc_weapon
- **Ascension custom items**: vanity, mounts, currency, bundles, mystic_scrolls, appearances, heirlooms

## [3.4.15] - 2025-12-18
### Fixed
- Fixed critical `NameError` in `lua_writer.py` when verifying group existence.
- Corrected version display in GUI.

## [3.4.14] - 2025-12-18
### Fixed
- Fixed critical bug where `cleanup_ui_state` was wiping newly added `groupTreeStatus` entries.
- Added missing profile keys (`groupTreeCollapsedStatus`, `isBankui`, `moveImportedItems`) for TSM 2.8 structural integrity.
- Updated default group operation to `"AlwaysUndercut"` for better out-of-the-box functionality.
- Improved profile replenishment logic for fresh TSM profiles.

## [3.4.13] - 2025-12-18
### Fixed
- Improved `groupTreeStatus` handling for Ascension TSM (TSM 2.8).
- Added `_ensure_group_tree_status_ascension` to ensure groups are visible in the sidebar.
- Fixed regex bug in `ensure_group_exists` that failed on paths with backticks.
- Fixed malformed Lua formatting in `_ensure_group_exists_ascension`.
- Updated GUI to accurately check group existence against loaded TSM data instead of UI registry.
