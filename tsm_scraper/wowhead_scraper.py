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
    
    # Categories for GUI - same format as AscensionDBScraper
    ALL_CATEGORIES = {
        # Weapons - (cat_type, subclass, tsm_group)
        "sword_1h": ("weapon", 7, "Transmog`Swords`One Hand"),
        "sword_2h": ("weapon", 8, "Transmog`Swords`Two Hand"),
        "axe_1h": ("weapon", 0, "Transmog`Axes`One Hand"),
        "axe_2h": ("weapon", 1, "Transmog`Axes`Two Hand"),
        "mace_1h": ("weapon", 4, "Transmog`Maces`One Hand"),
        "mace_2h": ("weapon", 5, "Transmog`Maces`Two Hand"),
        "dagger": ("weapon", 15, "Transmog`Daggers"),
        "staff": ("weapon", 10, "Transmog`Staves"),
        "polearm": ("weapon", 6, "Transmog`Polearms"),
        "bow": ("weapon", 2, "Transmog`Bows"),
        "gun": ("weapon", 3, "Transmog`Guns"),
        "crossbow": ("weapon", 18, "Transmog`Crossbow"),
        "wand": ("weapon", 19, "Transmog`Wands"),
        "fist": ("weapon", 13, "Transmog`Fist"),
        "thrown": ("weapon", 16, "Transmog`Throwing"),
        "fishing_pole": ("weapon", 20, "Tradeskills`Fishing`Rods"),
        # Armor
        "cloth_helm": ("armor", "1.1", "Transmog`Cloth`Helm"),
        "cloth_shoulders": ("armor", "1.3", "Transmog`Cloth`Shoulders"),
        "cloth_chest": ("armor", "1.5", "Transmog`Cloth`Chest"),
        "leather_helm": ("armor", "2.1", "Transmog`Leather`Helm"),
        "leather_chest": ("armor", "2.5", "Transmog`Leather`Chest"),
        "mail_helm": ("armor", "3.1", "Transmog`Mail`Helm"),
        "mail_chest": ("armor", "3.5", "Transmog`Mail`Chest"),
        "plate_helm": ("armor", "4.1", "Transmog`Plate`Helm"),
        "plate_chest": ("armor", "4.5", "Transmog`Plate`Chest"),
        "shield": ("armor", 6, "Transmog`Shields"),
        "back": ("armor", "0.16", "Transmog`Cloaks"),
        # Consumables
        "potion": ("consumable", 1, "Tradeskills`Alchemy`Potions"),
        "elixir": ("consumable", 2, "Tradeskills`Alchemy`Elixirs"),
        "flask": ("consumable", 3, "Tradeskills`Alchemy`Flasks"),
        "food": ("consumable", 5, "Tradeskills`Cooking`Eadibles"),
        # Trade Goods
        "herb": ("trade_goods", 9, "Tradeskills`Materials`Herbalism"),
        "metal_stone": ("trade_goods", 7, "Tradeskills`Materials`Mining"),
        "trade_cloth": ("trade_goods", 5, "Tradeskills`Tailoring`Cloth"),
        "enchanting_mats": ("trade_goods", 12, "Tradeskills`Enchanting`Reagents"),
        # Gems
        "gem": ("gem", None, "Tradeskills`Jewelcrafting`Gems"),
        # Recipes
        "recipe_alchemy": ("recipe", 6, "Tradeskills`Alchemy`Recipes"),
        "recipe_blacksmithing": ("recipe", 4, "Tradeskills`Blacksmithing`Recipes"),
        "recipe_cooking": ("recipe", 5, "Tradeskills`Cooking`Recipes"),
        "recipe_enchanting": ("recipe", 8, "Tradeskills`Enchanting`Recipes"),
        "recipe_engineering": ("recipe", 3, "Tradeskills`Engineering`Recipes"),
        "recipe_first_aid": ("recipe", 7, "Tradeskills`First Aid`Recipes"),
        "recipe_jewelcrafting": ("recipe", 10, "Tradeskills`Jewelcrafting`Recipes"),
        "recipe_leatherworking": ("recipe", 1, "Tradeskills`Leatherworking`Recipes"),
        "recipe_tailoring": ("recipe", 2, "Tradeskills`Tailoring`Recipes"),
        # Consumables - extra
        "bandage": ("consumable", 7, "Tradeskills`First Aid`Bandages"),
        "scroll": ("consumable", 4, "Consumables`Scrolls"),
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
            # Retail/Cata/MoP/Classic often use wh-heading-responsive, older pages might use heading-size-1
            title_elem = soup.find('h1', class_=['heading-size-1', 'wh-heading-responsive'])
            if not title_elem:
                title_elem = soup.find('h1') # Fallback to any H1
            
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
    
    def _scrape_category_url(self, url: str, limit: int = 10000) -> List[WowItem]:
        """
        Scrape items from a Wowhead category URL using the pretty URL format.
        This works better than the filter URL format as Wowhead properly pre-filters items.
        """
        cache_key = f"{self.game_version}_url_{url.split('/')[-1]}"
        cached = self._load_cache(cache_key)
        if cached:
            items = [WowItem(**item_data) for item_data in cached.get('items', [])]
            return items[:limit]
        
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url)
            items = []
            
            # Find arrays containing item data (500+ chars to catch small categories like first-aid)
            large_arrays = re.findall(r'=\s*(\[.{500,}?\]);', response.text, re.DOTALL)
            
            for arr_str in large_arrays:
                # Check if this looks like item data
                id_count = len(re.findall(r'"id":\s*\d+', arr_str))
                if id_count > 10:  # Found a large item array
                    try:
                        data_list = json.loads(arr_str)
                        for d in data_list:
                            if 'id' in d and 'name' in d:
                                item = WowItem(
                                    id=int(d['id']),
                                    name=d['name'],
                                    item_class=d.get('classs', 0),
                                    item_subclass="",
                                    slot="",
                                    quality=d.get('quality', 0),
                                    level=d.get('level', 0)
                                )
                                items.append(item)
                                if len(items) >= limit:
                                    break
                    except Exception as e:
                        # Fallback: regex extraction
                        for id_match in re.finditer(r'"id":\s*(\d+).*?"name":\s*"([^"]+)"', arr_str):
                            try:
                                item_id = int(id_match.group(1))
                                name = id_match.group(2)
                                item = WowItem(
                                    id=item_id,
                                    name=name,
                                    item_class="",
                                    item_subclass="",
                                    slot=""
                                )
                                items.append(item)
                                if len(items) >= limit:
                                    break
                            except:
                                continue
                    if items:
                        break
            
            # Cache the results
            self._save_cache(cache_key, {'items': [item.to_dict() for item in items]})
            return items
            
        except Exception as e:
            print(f"Error scraping URL {url}: {e}")
            return []
    
    def scrape_category(
        self, 
        item_class: int, 
        item_subclass: Optional[int] = None,
        slot: Optional[int] = None,
        min_level: int = 0,
        max_level: int = 80,
        min_quality: int = 0,
        max_quality: int = 5,
        limit: int = 10000
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
            # Parse the listview data from the page
            items = []
            
            # Strategy 1: Find large arrays containing item data
            # Wowhead embeds all items in a large JS array, we need to find it
            # Look for arrays with "id": and "name": that contain many items
            large_arrays = re.findall(r'=\s*(\[.{500,}?\]);', response.text, re.DOTALL)
            
            for arr_str in large_arrays:
                # Check if this looks like item data
                id_count = len(re.findall(r'"id":\s*\d+', arr_str))
                if id_count > 10:  # Found a large item array
                    try:
                        data_list = json.loads(arr_str)
                        
                        for d in data_list:
                            if 'id' in d and 'name' in d:
                                item = WowItem(
                                    id=int(d['id']),
                                    name=d['name'],
                                    item_class=self.ITEM_CLASSES.get(item_class, "Unknown"),
                                    item_subclass=self.WEAPON_SUBCLASSES.get(item_subclass, "") if item_class == 2 
                                                 else self.ARMOR_SUBCLASSES.get(item_subclass, "") if item_class == 4 
                                                 else "",
                                    slot=self.INVENTORY_SLOTS.get(slot, "") if slot else "",
                                    quality=d.get('quality', 0),
                                    level=d.get('level', 0)
                                )
                                items.append(item)
                                if len(items) >= limit:
                                    break
                    except Exception as e:
                        print(f"Error parsing JSON: {e}. Falling back to regex.")
                        # Fallback: regex extraction
                        for id_match in re.finditer(r'"id":\s*(\d+).*?"name":\s*"([^"]+)"', arr_str):
                            try:
                                item_id = int(id_match.group(1))
                                name = id_match.group(2)
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
                            except:
                                continue
                    # Found items, break out of array search loop
                    if items:
                        break
            
            # Strategy 2: Fallback to HTML parsing (legacy)
            if not items:
                soup = BeautifulSoup(response.text, 'html.parser')
                item_link_pattern = self._version_config['item_link_pattern']
                item_links = soup.find_all('a', href=re.compile(item_link_pattern))
                seen_ids = set()
                
                for link in item_links[:limit * 2]:
                    href = link.get('href', '')
                    match = re.search(r'/item=(\d+)', href)
                    if match:
                        item_id = int(match.group(1))
                        if item_id in seen_ids:
                            continue
                        seen_ids.add(item_id)
                        
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
    
    def scrape_weapons(self, weapon_type: str, limit: int = 10000) -> List[WowItem]:
        """
        Scrape weapon categories using Wowhead's pretty URLs for proper filtering.
        
        weapon_type: "sword_1h", "sword_2h", "axe_1h", "axe_2h", "mace_1h", "mace_2h",
                     "dagger", "staff", "polearm", "bow", "gun", "crossbow", "wand", etc.
        """
        # Map weapon types to their Wowhead URL paths
        url_map = {
            "axe_1h": "items/weapons/one-handed-axes",
            "axe_2h": "items/weapons/two-handed-axes",
            "sword_1h": "items/weapons/one-handed-swords",
            "sword_2h": "items/weapons/two-handed-swords",
            "mace_1h": "items/weapons/one-handed-maces",
            "mace_2h": "items/weapons/two-handed-maces",
            "dagger": "items/weapons/daggers",
            "staff": "items/weapons/staves",
            "polearm": "items/weapons/polearms",
            "bow": "items/weapons/bows",
            "gun": "items/weapons/guns",
            "crossbow": "items/weapons/crossbows",
            "wand": "items/weapons/wands",
            "fist": "items/weapons/fist-weapons",
            "thrown": "items/weapons/thrown",
            "fishing_pole": "items/weapons/fishing-poles",
        }
        
        url_path = url_map.get(weapon_type.lower())
        if url_path is None:
            print(f"Unknown weapon type: {weapon_type}")
            return []
        
        return self._scrape_category_url(f"{self.base_url}/{url_path}", limit=limit)
    
    # Comprehensive mapping of all category names to Wowhead pretty URLs
    CATEGORY_URL_MAP = {
        # Weapons
        "axe_1h": "items/weapons/one-handed-axes",
        "axe_2h": "items/weapons/two-handed-axes",
        "sword_1h": "items/weapons/one-handed-swords",
        "sword_2h": "items/weapons/two-handed-swords",
        "mace_1h": "items/weapons/one-handed-maces",
        "mace_2h": "items/weapons/two-handed-maces",
        "dagger": "items/weapons/daggers",
        "staff": "items/weapons/staves",
        "polearm": "items/weapons/polearms",
        "bow": "items/weapons/bows",
        "gun": "items/weapons/guns",
        "crossbow": "items/weapons/crossbows",
        "wand": "items/weapons/wands",
        "fist": "items/weapons/fist-weapons",
        "thrown": "items/weapons/thrown",
        "fishing_pole": "items/weapons/fishing-poles",
        # Consumables
        "potion": "items/consumables/potions",
        "elixir": "items/consumables/elixirs",
        "flask": "items/consumables/flasks",
        "food": "items/consumables/food-and-drinks",
        "bandage": "items/consumables/bandages",
        "scroll": "items/consumables/scrolls",
        # Trade Goods
        "herb": "items/trade-goods/herb",
        "metal_stone": "items/trade-goods/metal-and-stone",
        "trade_cloth": "items/trade-goods/cloth",
        "trade_leather": "items/trade-goods/leather",
        "enchanting_mats": "items/trade-goods/enchanting",
        "jc_mats": "items/trade-goods/jewelcrafting",
        "elemental": "items/trade-goods/elemental",
        "meat": "items/trade-goods/meat",
        # Armor
        "cloth_helm": "items/armor/cloth/slot:1",
        "cloth_shoulders": "items/armor/cloth/slot:3",
        "cloth_chest": "items/armor/cloth/slot:5",
        "cloth_waist": "items/armor/cloth/slot:6",
        "cloth_legs": "items/armor/cloth/slot:7",
        "cloth_feet": "items/armor/cloth/slot:8",
        "cloth_wrists": "items/armor/cloth/slot:9",
        "cloth_hands": "items/armor/cloth/slot:10",
        "leather_helm": "items/armor/leather/slot:1",
        "leather_shoulders": "items/armor/leather/slot:3",
        "leather_chest": "items/armor/leather/slot:5",
        "leather_waist": "items/armor/leather/slot:6",
        "leather_legs": "items/armor/leather/slot:7",
        "leather_feet": "items/armor/leather/slot:8",
        "leather_wrists": "items/armor/leather/slot:9",
        "leather_hands": "items/armor/leather/slot:10",
        "mail_helm": "items/armor/mail/slot:1",
        "mail_shoulders": "items/armor/mail/slot:3",
        "mail_chest": "items/armor/mail/slot:5",
        "mail_waist": "items/armor/mail/slot:6",
        "mail_legs": "items/armor/mail/slot:7",
        "mail_feet": "items/armor/mail/slot:8",
        "mail_wrists": "items/armor/mail/slot:9",
        "mail_hands": "items/armor/mail/slot:10",
        "plate_helm": "items/armor/plate/slot:1",
        "plate_shoulders": "items/armor/plate/slot:3",
        "plate_chest": "items/armor/plate/slot:5",
        "plate_waist": "items/armor/plate/slot:6",
        "plate_legs": "items/armor/plate/slot:7",
        "plate_feet": "items/armor/plate/slot:8",
        "plate_wrists": "items/armor/plate/slot:9",
        "plate_hands": "items/armor/plate/slot:10",
        "shield": "items/armor/shields",
        "back": "items/armor/back",
        # Gems
        "gem": "items/gems",
        # Containers
        "bag": "items/containers",
        # Recipes (use filter URLs as there's no good pretty URL)
        "recipe_alchemy": "items/recipes/alchemy",
        "recipe_blacksmithing": "items/recipes/blacksmithing",
        "recipe_cooking": "items/recipes/cooking",
        "recipe_enchanting": "items/recipes/enchanting",
        "recipe_engineering": "items/recipes/engineering",
        "recipe_first_aid": "items/recipes/first-aid",
        "recipe_jewelcrafting": "items/recipes/jewelcrafting",
        "recipe_leatherworking": "items/recipes/leatherworking",
        "recipe_tailoring": "items/recipes/tailoring",
    }
    
    def scrape_by_name(self, category_name: str, limit: int = 10000) -> List[WowItem]:
        """
        Scrape any category by its name using pretty URLs.
        This is the recommended method for all category scraping as it ensures proper filtering.
        """
        url_path = self.CATEGORY_URL_MAP.get(category_name.lower())
        if url_path is None:
            print(f"Unknown category: {category_name}")
            return []
        
        return self._scrape_category_url(f"{self.base_url}/{url_path}", limit=limit)
    
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
