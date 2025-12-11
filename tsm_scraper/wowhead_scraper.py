"""
Wowhead Scraper for WoW items (Retail, WotLK, TBC, Classic, Cata, MoP).

Hey! This is the main scraper that talks to Wowhead's website to grab item data.
We need this because Wowhead has the most complete database of WoW items across 
all game versions - way better than trying to extract it from game files.

What this does:
- Fetches item IDs from category pages
- Grabs item details (name, type, slot, etc.)
- Caches results so we don't hammer their servers
- Works with retail, classic, and all the expansion-specific sites

The scraper is polite - it waits between requests to avoid getting rate limited.
"""

import re
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Literal
from dataclasses import dataclass

# We need requests to fetch web pages and BeautifulSoup to parse the HTML
# If you don't have these, run: pip install requests beautifulsoup4
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Please install required packages: pip install requests beautifulsoup4")
    raise


# Type hints help catch bugs - this says "only these strings are valid"
GameVersion = Literal['retail', 'wotlk', 'tbc', 'classic', 'cata', 'mop']


@dataclass
class WowItem:
    """
    A simple container for WoW item data.
    
    Using a dataclass here because it's cleaner than a dict and gives us
    nice features like automatic __repr__ and type hints.
    """
    id: int
    name: str
    item_class: str = ""      # The main category: Weapon, Armor, Consumable, etc.
    item_subclass: str = ""   # More specific: Sword, Axe, Cloth, Leather, etc.
    slot: str = ""            # Where it goes: Head, Chest, One-Hand, etc.
    quality: int = 0          # Rarity: 0=Poor(gray), 1=Common(white), 2=Uncommon(green), 
                              #         3=Rare(blue), 4=Epic(purple), 5=Legendary(orange)
    level: int = 0            # Required level to use the item
    
    def to_dict(self) -> dict:
        """Convert to a plain dict for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'item_class': self.item_class,
            'item_subclass': self.item_subclass,
            'slot': self.slot,
            'quality': self.quality,
            'level': self.level
        }


class WowheadScraper:
    """
    The main scraper class that handles all the Wowhead interaction.
    
    Each game version has its own subdomain/path on Wowhead, so we configure
    those dynamically based on what version the user wants to scrape.
    """
    
    # Each game version has different URLs - retail is just wowhead.com,
    # but classic is wowhead.com/classic, wotlk is wowhead.com/wotlk, etc.
    # The item_link_pattern helps us find item links in the HTML
    GAME_VERSIONS: Dict[str, Dict[str, str]] = {
        'retail': {
            'base_url': 'https://www.wowhead.com',
            'item_path': '/item=',
            'items_path': '/items',
            'item_link_pattern': r'/item=(\d+)',  # Retail doesn't have a prefix
        },
        'wotlk': {
            'base_url': 'https://www.wowhead.com/wotlk',
            'item_path': '/item=',
            'items_path': '/items',
            'item_link_pattern': r'/wotlk/item=(\d+)',
        },
        'tbc': {
            'base_url': 'https://www.wowhead.com/tbc',
            'item_path': '/item=',
            'items_path': '/items',
            'item_link_pattern': r'/tbc/item=(\d+)',
        },
        'classic': {
            'base_url': 'https://www.wowhead.com/classic',
            'item_path': '/item=',
            'items_path': '/items',
            'item_link_pattern': r'/classic/item=(\d+)',
        },
        'cata': {
            'base_url': 'https://www.wowhead.com/cata',
            'item_path': '/item=',
            'items_path': '/items',
            'item_link_pattern': r'/cata/item=(\d+)',
        },
        'mop': {
            'base_url': 'https://www.wowhead.com/mop-classic',
            'item_path': '/item=',
            'items_path': '/items',
            'item_link_pattern': r'/mop-classic/item=(\d+)',
        },
    }
    
    # Wowhead uses numeric IDs for item classes internally
    # These map to the human-readable names we all know
    ITEM_CLASSES = {
        0: "Consumable",
        1: "Container",
        2: "Weapon",
        3: "Gem",
        4: "Armor",
        5: "Reagent",
        6: "Projectile",
        7: "Trade Goods",
        8: "Generic",
        9: "Recipe",
        10: "Currency",
        11: "Quest",
        12: "Key",
        13: "Junk",
        14: "Glyph",
        15: "Misc"
    }
    
    # Weapon subclass IDs
    WEAPON_SUBCLASSES = {
        0: "Axe (1H)",
        1: "Axe (2H)",
        2: "Bow",
        3: "Gun",
        4: "Mace (1H)",
        5: "Mace (2H)",
        6: "Polearm",
        7: "Sword (1H)",
        8: "Sword (2H)",
        10: "Staff",
        13: "Fist Weapon",
        14: "Miscellaneous",
        15: "Dagger",
        16: "Thrown",
        17: "Spear",
        18: "Crossbow",
        19: "Wand",
        20: "Fishing Pole"
    }
    
    # Armor subclass IDs
    ARMOR_SUBCLASSES = {
        0: "Miscellaneous",
        1: "Cloth",
        2: "Leather",
        3: "Mail",
        4: "Plate",
        5: "Buckler",
        6: "Shield",
        7: "Libram",
        8: "Idol",
        9: "Totem",
        10: "Sigil"
    }
    
    # Inventory slot IDs
    INVENTORY_SLOTS = {
        1: "Head",
        2: "Neck",
        3: "Shoulder",
        4: "Shirt",
        5: "Chest",
        6: "Waist",
        7: "Legs",
        8: "Feet",
        9: "Wrists",
        10: "Hands",
        11: "Finger",
        12: "Trinket",
        13: "One-Hand",
        14: "Off Hand",
        15: "Ranged",
        16: "Back",
        17: "Two-Hand",
        18: "Bag",
        19: "Tabard",
        20: "Robe",
        21: "Main Hand",
        22: "Off Hand",
        23: "Held In Off-hand",
        24: "Ammo",
        25: "Thrown",
        26: "Ranged",
        28: "Relic"
    }
    
    def __init__(self, game_version: GameVersion = 'wotlk', cache_dir: Optional[str] = None):
        """
        Initialize the Wowhead scraper.
        
        Args:
            game_version: Which WoW version to scrape ('retail', 'wotlk', 'classic')
            cache_dir: Optional custom cache directory path
        """
        self.game_version = game_version
        self._version_config = self.GAME_VERSIONS.get(game_version, self.GAME_VERSIONS['wotlk'])
        self.base_url = self._version_config['base_url']
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent.parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.rate_limit_delay = 1.0  # Seconds between requests
        
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get path for cached data."""
        safe_key = re.sub(r'[^\w\-]', '_', cache_key)
        return self.cache_dir / f"{safe_key}.json"
    
    def _load_cache(self, cache_key: str) -> Optional[dict]:
        """Load cached data if available."""
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def _save_cache(self, cache_key: str, data: dict):
        """Save data to cache."""
        cache_path = self._get_cache_path(cache_key)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def get_item(self, item_id: int) -> Optional[WowItem]:
        """Get a single item by ID."""
        cache_key = f"{self.game_version}_item_{item_id}"
        cached = self._load_cache(cache_key)
        if cached:
            return WowItem(**cached)
        
        url = f"{self.base_url}/item={item_id}"
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract item name
            title_elem = soup.find('h1', class_='heading-size-1')
            if not title_elem:
                return None
            name = title_elem.get_text(strip=True)
            
            # Extract item data from page script
            item = WowItem(id=item_id, name=name)
            
            # Try to find tooltip data
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and 'WH.Gatherer' in script.string:
                    # Extract class/subclass info
                    if match := re.search(r'"classs":(\d+)', script.string):
                        item.item_class = self.ITEM_CLASSES.get(int(match.group(1)), "Unknown")
                    if match := re.search(r'"subclass":(\d+)', script.string):
                        if item.item_class == "Weapon":
                            item.item_subclass = self.WEAPON_SUBCLASSES.get(int(match.group(1)), "Unknown")
                        elif item.item_class == "Armor":
                            item.item_subclass = self.ARMOR_SUBCLASSES.get(int(match.group(1)), "Unknown")
                    if match := re.search(r'"slot":(\d+)', script.string):
                        item.slot = self.INVENTORY_SLOTS.get(int(match.group(1)), "Unknown")
                    if match := re.search(r'"quality":(\d+)', script.string):
                        item.quality = int(match.group(1))
                    break
            
            self._save_cache(cache_key, item.to_dict())
            return item
            
        except Exception as e:
            print(f"Error fetching item {item_id}: {e}")
            return None
    
    def scrape_category(
        self, 
        item_class: int, 
        item_subclass: Optional[int] = None,
        slot: Optional[int] = None,
        min_level: int = 0,
        max_level: int = 80,
        min_quality: int = 0,
        max_quality: int = 5,
        limit: int = 100
    ) -> List[WowItem]:
        """
        Scrape items from a category.
        
        Uses Wowhead's item list filtering.
        """
        # Build filter URL
        filters = [f"cr=151;crs={item_class};crv=0"]  # Item class filter
        
        if item_subclass is not None:
            filters.append(f"cr=152;crs={item_subclass};crv=0")
        
        if slot is not None:
            filters.append(f"cr=154;crs={slot};crv=0")
        
        filter_str = ";".join(filters)
        
        cache_key = f"{self.game_version}_category_{item_class}_{item_subclass}_{slot}_{min_level}_{max_level}"
        cached = self._load_cache(cache_key)
        if cached:
            items = [WowItem(**item_data) for item_data in cached.get('items', [])]
            return items[:limit]
        
        url = f"{self.base_url}/items?filter={filter_str}"
        
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url)
            
            # Parse the listview data from the page
            items = []
            
            # Look for the listview data in the page's JavaScript
            match = re.search(r'new Listview\(\{[^}]*data:\s*(\[[^\]]+\])', response.text, re.DOTALL)
            if match:
                # This is simplified - real parsing would need to handle the JS object
                # For now, we'll use a different approach
                pass
            
            # Alternative: parse the HTML table
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find item links in the page using version-aware pattern
            item_link_pattern = self._version_config['item_link_pattern']
            item_links = soup.find_all('a', href=re.compile(item_link_pattern))
            seen_ids = set()
            
            for link in item_links[:limit * 2]:  # Get extra since some might be duplicates
                href = link.get('href', '')
                match = re.search(r'/item=(\d+)', href)
                if match:
                    item_id = int(match.group(1))
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)
                    
                    # Get the item name from the link text
                    name = link.get_text(strip=True)
                    if not name or len(name) < 2:
                        continue
                    
                    item = WowItem(
                        id=item_id,
                        name=name,
                        item_class=self.ITEM_CLASSES.get(item_class, "Unknown"),
                        item_subclass=self.WEAPON_SUBCLASSES.get(item_subclass, "") if item_class == 2 
                                     else self.ARMOR_SUBCLASSES.get(item_subclass, "") if item_class == 4 
                                     else "",
                        slot=self.INVENTORY_SLOTS.get(slot, "") if slot else ""
                    )
                    items.append(item)
                    
                    if len(items) >= limit:
                        break
            
            # Cache the results
            self._save_cache(cache_key, {'items': [item.to_dict() for item in items]})
            
            return items
            
        except Exception as e:
            print(f"Error scraping category: {e}")
            return []
    
    def scrape_weapons(self, weapon_type: str, limit: int = 100) -> List[WowItem]:
        """
        Convenience method to scrape weapon categories.
        
        weapon_type: "sword_1h", "sword_2h", "axe_1h", "axe_2h", "mace_1h", "mace_2h",
                     "dagger", "staff", "polearm", "bow", "gun", "crossbow", "wand", etc.
        """
        weapon_map = {
            "sword_1h": 7, "sword_2h": 8,
            "axe_1h": 0, "axe_2h": 1,
            "mace_1h": 4, "mace_2h": 5,
            "dagger": 15, "staff": 10, "polearm": 6,
            "bow": 2, "gun": 3, "crossbow": 18, "wand": 19,
            "fist": 13, "thrown": 16
        }
        
        subclass = weapon_map.get(weapon_type.lower())
        if subclass is None:
            print(f"Unknown weapon type: {weapon_type}")
            return []
        
        return self.scrape_category(item_class=2, item_subclass=subclass, limit=limit)
    
    def scrape_armor(self, armor_type: str, slot: str, limit: int = 100) -> List[WowItem]:
        """
        Convenience method to scrape armor categories.
        
        armor_type: "cloth", "leather", "mail", "plate", "shield"
        slot: "head", "shoulder", "chest", "waist", "legs", "feet", "wrists", "hands", "back"
        """
        armor_map = {"cloth": 1, "leather": 2, "mail": 3, "plate": 4, "shield": 6}
        slot_map = {
            "head": 1, "neck": 2, "shoulder": 3, "chest": 5, "waist": 6,
            "legs": 7, "feet": 8, "wrists": 9, "hands": 10, "back": 16,
            "finger": 11, "trinket": 12, "offhand": 23, "tabard": 19
        }
        
        armor_subclass = armor_map.get(armor_type.lower())
        slot_id = slot_map.get(slot.lower())
        
        if armor_subclass is None:
            print(f"Unknown armor type: {armor_type}")
            return []
        
        return self.scrape_category(
            item_class=4, 
            item_subclass=armor_subclass,
            slot=slot_id,
            limit=limit
        )
    
    def scrape_item_list(self, url: str) -> List[int]:
        """
        Scrape item IDs from any Wowhead item list URL.
        
        Useful for custom filtered lists.
        Returns list of item IDs.
        """
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url)
            
            # Find all item references
            item_ids = []
            matches = re.findall(r'/item=(\d+)', response.text)
            seen = set()
            
            for match in matches:
                item_id = int(match)
                if item_id not in seen:
                    seen.add(item_id)
                    item_ids.append(item_id)
            
            return item_ids
            
        except Exception as e:
            print(f"Error scraping URL: {e}")
            return []


def main():
    """Test the scraper with multiple game versions."""
    import sys
    
    # Determine which version to test
    if len(sys.argv) > 1:
        version = sys.argv[1].lower()
    else:
        version = 'wotlk'
    
    if version not in ('retail', 'wotlk', 'classic'):
        print(f"Unknown version: {version}. Use 'retail', 'wotlk', or 'classic'")
        return
    
    print(f"=== Testing {version.upper()} Wowhead Scraper ===\n")
    scraper = WowheadScraper(game_version=version)
    print(f"Base URL: {scraper.base_url}")
    
    # Test single item lookup
    print("\nTesting single item lookup...")
    test_items = {
        'wotlk': 22589,    # Atiesh
        'classic': 12640,  # Lionheart Helm
        'retail': 220140,  # Random retail item
    }
    item_id = test_items.get(version, 22589)
    item = scraper.get_item(item_id)
    if item:
        print(f"  Found: {item.name} (ID: {item.id})")
        print(f"  Class: {item.item_class}, Subclass: {item.item_subclass}, Slot: {item.slot}")
    else:
        print(f"  Could not find item {item_id}")
    
    # Test weapon category scrape
    print("\nTesting weapon category scrape (daggers, limit=5)...")
    daggers = scraper.scrape_weapons("dagger", limit=5)
    for dagger in daggers:
        print(f"  {dagger.id}: {dagger.name}")
    
    if not daggers:
        print("  No daggers found (this may be expected for retail due to different URL structure)")


if __name__ == "__main__":
    main()
