"""
Ascension Database Scraper for Project Ascension items.

This scraper is specifically for Project Ascension (db.ascension.gg) - a custom
WoW 3.3.5a private server. Their database has a lot of custom items that won't
be found on Wowhead, so we need a dedicated scraper for them.

How it works:
- Fetches category pages like db.ascension.gg/?items=2.7 (weapon.swords)
- Extracts item IDs from the HTML using regex
- Caches results to avoid hammering their servers
- Maps items to TSM group paths for easy import

URL Patterns:
  Items list: https://db.ascension.gg/?items=CLASS.SUBCLASS
  Single item: https://db.ascension.gg/?item=ITEMID
  
The class/subclass numbers are based on WoW's internal item classification:
  - Class 2 = Weapon, Class 4 = Armor, Class 0 = Consumable, etc.
  - Subclasses vary by class (e.g., for weapons: 7=Sword 1H, 8=Sword 2H)
"""

import re
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# These are required for web scraping - install with: pip install requests beautifulsoup4
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Please install required packages: pip install requests beautifulsoup4")
    raise


@dataclass
class AscensionItem:
    """
    Container for item data from Ascension's database.
    
    Pretty simple - just holds the basic info we need to categorize
    items for TSM import.
    """
    id: int
    name: str
    item_class: str = ""      # Weapon, Armor, Consumable, etc.
    item_subclass: str = ""   # Sword, Axe, Cloth, etc.
    slot: str = ""            # Head, Chest, One-Hand, etc.
    quality: int = 0          # Item rarity (0-5)
    
    def to_dict(self) -> dict:
        """Convert to a dict for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'item_class': self.item_class,
            'item_subclass': self.item_subclass,
            'slot': self.slot,
            'quality': self.quality
        }


class AscensionDBScraper:
    """
    The main scraper for Ascension's item database.
    
    This is the workhorse for scraping items from db.ascension.gg.
    It knows all the category mappings and can generate TSM group paths.
    """
    
    BASE_URL = "https://db.ascension.gg"
    
    # Item class IDs
    CLASS_WEAPON = 2
    CLASS_ARMOR = 4
    CLASS_CONTAINER = 1
    CLASS_CONSUMABLE = 0
    CLASS_GEM = 3
    CLASS_TRADE_GOODS = 7
    CLASS_RECIPE = 9
    CLASS_PROJECTILE = 6
    CLASS_QUEST = 12
    CLASS_MISC = 15
    
    # Weapon subclass IDs
    WEAPON_SUBCLASSES = {
        "axe_1h": 0, "axe_2h": 1,
        "bow": 2, "gun": 3,
        "mace_1h": 4, "mace_2h": 5,
        "polearm": 6,
        "sword_1h": 7, "sword_2h": 8,
        "staff": 10,
        "fist": 13,
        "dagger": 15,
        "thrown": 16,
        "crossbow": 18,
        "wand": 19,
        "fishing_pole": 20
    }
    
    # Armor subclass IDs  
    ARMOR_SUBCLASSES = {
        "misc": 0,
        "cloth": 1,
        "leather": 2,
        "mail": 3,
        "plate": 4,
        "shield": 6
    }
    
    # Consumable subclass IDs (class=0)
    CONSUMABLE_SUBCLASSES = {
        "consumable": 0,
        "potion": 1,
        "elixir": 2,
        "flask": 3,
        "scroll": 4,
        "food": 5,
        "bandage": 7
    }
    
    # Trade Goods subclass IDs (class=7)
    TRADE_GOODS_SUBCLASSES = {
        "trade_goods": 0,
        "parts": 1,
        "explosives": 2,
        "devices": 3,
        "jewelcrafting": 4,
        "cloth": 5,
        "leather": 6,
        "metal_stone": 7,
        "meat": 8,
        "herb": 9,
        "elemental": 10,
        "enchanting": 12,
        "materials": 13,
        "armor_enchantment": 14,
        "weapon_enchantment": 15
    }
    
    # Recipe subclass IDs (class=9)
    RECIPE_SUBCLASSES = {
        "book": 0,
        "leatherworking": 1,
        "tailoring": 2,
        "engineering": 3,
        "blacksmithing": 4,
        "cooking": 5,
        "alchemy": 6,
        "first_aid": 7,
        "enchanting": 8,
        "fishing": 9,
        "jewelcrafting": 10,
        "inscription": 11
    }
    
    # Gem subclass IDs (class=3)
    GEM_SUBCLASSES = {
        "red": 0,
        "blue": 1,
        "yellow": 2,
        "purple": 3,
        "green": 4,
        "orange": 5,
        "meta": 6,
        "simple": 7,
        "prismatic": 8
    }
    
    # Container subclass IDs (class=1)
    CONTAINER_SUBCLASSES = {
        "bag": 0,
        "soul_bag": 1,
        "herb_bag": 2,
        "enchanting_bag": 3,
        "engineering_bag": 4,
        "gem_bag": 5,
        "mining_bag": 6,
        "leatherworking_bag": 7,
        "inscription_bag": 8
    }
    
    # TSM group mappings
    WEAPON_TO_GROUP = {
        "axe_1h": "Transmog`Axes`One Hand",
        "axe_2h": "Transmog`Axes`Two Hand",
        "bow": "Transmog`Bows",
        "gun": "Transmog`Guns",
        "mace_1h": "Transmog`Maces`One Hand",
        "mace_2h": "Transmog`Maces`Two Hand",
        "polearm": "Transmog`Polearms",
        "sword_1h": "Transmog`Swords`One Hand",
        "sword_2h": "Transmog`Swords`Two Hand",
        "staff": "Transmog`Staves",
        "fist": "Transmog`Fist",
        "dagger": "Transmog`Daggers",
        "thrown": "Transmog`Throwing",
        "crossbow": "Transmog`Crossbow",
        "wand": "Transmog`Wands",
        "fishing_pole": "Tradeskills`Fishing`Rods"
    }
    
    CONSUMABLE_TO_GROUP = {
        "potion": "Tradeskills`Alchemy`Potions",
        "elixir": "Tradeskills`Alchemy`Elixirs",
        "flask": "Tradeskills`Alchemy`Flasks",
        "scroll": "Scrolls",
        "food": "Tradeskills`Cooking`Eadibles",
        "bandage": "Tradeskills`FirstAid`Bandages"
    }
    
    TRADE_GOODS_TO_GROUP = {
        "cloth": "Tradeskills`Tailoring`Cloth",
        "leather": "Tradeskills`Materials`Skinning",
        "metal_stone": "Tradeskills`Materials`Mining",
        "herb": "Tradeskills`Materials`Herbalism",
        "meat": "Tradeskills`Cooking`Meats",
        "enchanting": "Tradeskills`Enchanting`Reagents",
        "jewelcrafting": "Tradeskills`Jewelcrafting`Reagents",
        "elemental": "Tradeskills`Materials`Elemental"
    }
    
    RECIPE_TO_GROUP = {
        "alchemy": "Patterns`Alchemy",
        "blacksmithing": "Patterns`Blacksmithing",
        "cooking": "Patterns`Cooking",
        "enchanting": "Patterns`Enchanting",
        "engineering": "Patterns`Engineering",
        "first_aid": "Patterns`First Aid",
        "jewelcrafting": "Patterns`Jewelcrafting",
        "leatherworking": "Patterns`Leatherworking",
        "tailoring": "Patterns`Tailoring"
    }
    
    # Armor slot IDs for URL filtering
    ARMOR_SLOT_IDS = {
        "helm": 1, "shoulders": 3, "chest": 5, "waist": 6,
        "legs": 7, "feet": 8, "wrists": 9, "hands": 10, "back": 16
    }
    
    # Complete category list for quick_import
    ALL_CATEGORIES = {
        # Weapons
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
        
        # Armor - Cloth (with slots)
        "cloth_helm": ("armor", "1.1", "Transmog`Cloth`Helm"),
        "cloth_shoulders": ("armor", "1.3", "Transmog`Cloth`Shoulders"),
        "cloth_chest": ("armor", "1.5", "Transmog`Cloth`Chest"),
        "cloth_waist": ("armor", "1.6", "Transmog`Cloth`Waist"),
        "cloth_legs": ("armor", "1.7", "Transmog`Cloth`Legs"),
        "cloth_feet": ("armor", "1.8", "Transmog`Cloth`Feet"),
        "cloth_wrists": ("armor", "1.9", "Transmog`Cloth`Wrists"),
        "cloth_hands": ("armor", "1.10", "Transmog`Cloth`Hands"),
        
        # Armor - Leather (with slots)
        "leather_helm": ("armor", "2.1", "Transmog`Leather`Helm"),
        "leather_shoulders": ("armor", "2.3", "Transmog`Leather`Shoulders"),
        "leather_chest": ("armor", "2.5", "Transmog`Leather`Chest"),
        "leather_waist": ("armor", "2.6", "Transmog`Leather`Waist"),
        "leather_legs": ("armor", "2.7", "Transmog`Leather`Legs"),
        "leather_feet": ("armor", "2.8", "Transmog`Leather`Feet"),
        "leather_wrists": ("armor", "2.9", "Transmog`Leather`Wrists"),
        "leather_hands": ("armor", "2.10", "Transmog`Leather`Hands"),
        
        # Armor - Mail (with slots)
        "mail_helm": ("armor", "3.1", "Transmog`Mail`Helm"),
        "mail_shoulders": ("armor", "3.3", "Transmog`Mail`Shoulders"),
        "mail_chest": ("armor", "3.5", "Transmog`Mail`Chest"),
        "mail_waist": ("armor", "3.6", "Transmog`Mail`Waist"),
        "mail_legs": ("armor", "3.7", "Transmog`Mail`Legs"),
        "mail_feet": ("armor", "3.8", "Transmog`Mail`Feet"),
        "mail_wrists": ("armor", "3.9", "Transmog`Mail`Wrists"),
        "mail_hands": ("armor", "3.10", "Transmog`Mail`Hands"),
        
        # Armor - Plate (with slots)
        "plate_helm": ("armor", "4.1", "Transmog`Plate`Helm"),
        "plate_shoulders": ("armor", "4.3", "Transmog`Plate`Shoulders"),
        "plate_chest": ("armor", "4.5", "Transmog`Plate`Chest"),
        "plate_waist": ("armor", "4.6", "Transmog`Plate`Waist"),
        "plate_legs": ("armor", "4.7", "Transmog`Plate`Legs"),
        "plate_feet": ("armor", "4.8", "Transmog`Plate`Feet"),
        "plate_wrists": ("armor", "4.9", "Transmog`Plate`Wrists"),
        "plate_hands": ("armor", "4.10", "Transmog`Plate`Hands"),
        
        # Armor - Other
        "shield": ("armor", 6, "Transmog`Shields"),
        "back": ("armor", "0.16", "Transmog`Cloaks"),
        
        # Consumables
        "potion": ("consumable", 1, "Tradeskills`Alchemy`Potions"),
        "elixir": ("consumable", 2, "Tradeskills`Alchemy`Elixirs"),
        "flask": ("consumable", 3, "Tradeskills`Alchemy`Flasks"),
        "scroll": ("consumable", 4, "Scrolls"),
        "food": ("consumable", 5, "Tradeskills`Cooking`Eadibles"),
        "bandage": ("consumable", 7, "Tradeskills`FirstAid`Bandages"),
        # Trade Goods
        "trade_cloth": ("trade_goods", 5, "Tradeskills`Tailoring`Cloth"),
        "trade_leather": ("trade_goods", 6, "Tradeskills`Materials`Skinning"),
        "metal_stone": ("trade_goods", 7, "Tradeskills`Materials`Mining"),
        "herb": ("trade_goods", 9, "Tradeskills`Materials`Herbalism"),
        "meat": ("trade_goods", 8, "Tradeskills`Cooking`Meats"),
        "enchanting_mats": ("trade_goods", 12, "Tradeskills`Enchanting`Reagents"),
        "jc_mats": ("trade_goods", 4, "Tradeskills`Jewelcrafting`Reagents"),
        "elemental": ("trade_goods", 10, "Tradeskills`Materials`Elemental"),
        # Recipes
        "recipe_alchemy": ("recipe", 6, "Patterns`Alchemy"),
        "recipe_blacksmithing": ("recipe", 4, "Patterns`Blacksmithing"),
        "recipe_cooking": ("recipe", 5, "Patterns`Cooking"),
        "recipe_enchanting": ("recipe", 8, "Patterns`Enchanting"),
        "recipe_engineering": ("recipe", 3, "Patterns`Engineering"),
        "recipe_first_aid": ("recipe", 7, "Patterns`First Aid"),
        "recipe_jewelcrafting": ("recipe", 10, "Patterns`Jewelcrafting"),
        "recipe_leatherworking": ("recipe", 1, "Patterns`Leatherworking"),
        "recipe_tailoring": ("recipe", 2, "Patterns`Tailoring"),
        # Gems
        "gem": ("gem", None, "Tradeskills`Jewelcrafting`Gems"),
        # Containers
        "bag": ("container", 0, "Tradeskills`Tailoring`Bags"),
        # Projectile
        "ammo": ("projectile", None, "Ammo"),
    }
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent.parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.rate_limit_delay = 0.5
        
    def _get_cache_path(self, cache_key: str) -> Path:
        safe_key = re.sub(r'[^\w\-]', '_', cache_key)
        return self.cache_dir / f"ascension_{safe_key}.json"
    
    def _load_cache(self, cache_key: str) -> Optional[dict]:
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def _save_cache(self, cache_key: str, data: dict):
        cache_path = self._get_cache_path(cache_key)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def scrape_item_ids_from_page(self, url: str) -> List[int]:
        """
        Scrape item IDs from a db.ascension.gg item list page.
        
        The page uses JavaScript to load data, but item IDs are often
        embedded in the page source as links.
        """
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url)
            
            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code}")
                return []
            
            # Find item IDs in the page
            # Pattern: ?item=XXXXX or item=XXXXX
            item_ids = []
            seen = set()
            
            # Look for item links
            matches = re.findall(r'\?item=(\d+)', response.text)
            for match in matches:
                item_id = int(match)
                if item_id not in seen:
                    seen.add(item_id)
                    item_ids.append(item_id)
            
            # Also look for listview data that might contain IDs
            # Pattern: "id":XXXXX
            data_matches = re.findall(r'"id"\s*:\s*(\d+)', response.text)
            for match in data_matches:
                item_id = int(match)
                if item_id not in seen and item_id > 100:  # Filter out small numbers
                    seen.add(item_id)
                    item_ids.append(item_id)
            
            return item_ids
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return []
    
    def scrape_weapons(self, weapon_type: str, limit: int = 1000) -> List[int]:
        """
        Scrape weapon item IDs from Ascension DB.
        
        weapon_type: axe_1h, axe_2h, sword_1h, sword_2h, dagger, staff, etc.
        """
        subclass = self.WEAPON_SUBCLASSES.get(weapon_type.lower())
        if subclass is None:
            print(f"Unknown weapon type: {weapon_type}")
            print(f"Available types: {', '.join(self.WEAPON_SUBCLASSES.keys())}")
            return []
        
        cache_key = f"weapon_{weapon_type}"
        cached = self._load_cache(cache_key)
        if cached:
            return cached.get('item_ids', [])[:limit]
        
        url = f"{self.BASE_URL}/?items={self.CLASS_WEAPON}.{subclass}"
        print(f"Scraping: {url}")
        
        item_ids = self.scrape_item_ids_from_page(url)
        
        # Cache results
        self._save_cache(cache_key, {'item_ids': item_ids})
        
        return item_ids[:limit]
    
    def scrape_armor(self, armor_type: str, slot: Optional[str] = None, limit: int = 1000) -> List[int]:
        """
        Scrape armor item IDs from Ascension DB.
        
        armor_type: cloth, leather, mail, plate, shield
        slot: head, chest, legs, etc. (optional filter)
        """
        subclass = self.ARMOR_SUBCLASSES.get(armor_type.lower())
        if subclass is None:
            print(f"Unknown armor type: {armor_type}")
            print(f"Available types: {', '.join(self.ARMOR_SUBCLASSES.keys())}")
            return []
        
        cache_key = f"armor_{armor_type}"
        if slot:
            cache_key += f"_{slot}"
            
        cached = self._load_cache(cache_key)
        if cached:
            return cached.get('item_ids', [])[:limit]
        
        url = f"{self.BASE_URL}/?items={self.CLASS_ARMOR}.{subclass}"
        print(f"Scraping: {url}")
        
        item_ids = self.scrape_item_ids_from_page(url)
        
        self._save_cache(cache_key, {'item_ids': item_ids})
        
        return item_ids[:limit]
    
    def get_item(self, item_id: int) -> Optional[AscensionItem]:
        """Get a single item by ID from Ascension DB."""
        cache_key = f"item_{item_id}"
        cached = self._load_cache(cache_key)
        if cached:
            return AscensionItem(**cached)
        
        url = f"{self.BASE_URL}/?item={item_id}"
        try:
            time.sleep(0.5)  # Be polite
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            name = None
            
            # Ascension DB puts name in title: "Name - Item - Ascension Database"
            if soup.title:
                title_text = soup.title.string
                if " - Item -" in title_text:
                    name = title_text.split(" - Item -")[0]
            
            if not name:
                # Fallback to headers
                for class_name in ['name', 'heading_1']:
                    elem = soup.find(class_=class_name)
                    if elem:
                        name = elem.get_text(strip=True)
                        break
            
            if not name:
                return None

            # Create item object
            item = AscensionItem(
                id=item_id,
                name=name,
                item_class="Unknown",  # Harder to parse from just page HTML without complex logic
                item_subclass="Unknown",
                quality=1
            )
            
            self._save_cache(cache_key, item.to_dict())
            return item
            
        except Exception as e:
            print(f"Error fetching item {item_id}: {e}")
            return None

    def get_tsm_group_for_weapon(self, weapon_type: str) -> str:
        """Get the TSM group path for a weapon type."""
        return self.WEAPON_TO_GROUP.get(weapon_type.lower(), "Transmog`Other")
    
    def get_tsm_group_for_armor(self, armor_type: str, slot: str) -> str:
        """Get the TSM group path for an armor type and slot."""
        armor_type = armor_type.capitalize()
        slot = slot.capitalize()
        return f"Transmog`{armor_type}`{slot}"
    
    def list_available_categories(self):
        """Print available weapon and armor categories."""
        print("\nWeapon Types:")
        for wtype, subclass in self.WEAPON_SUBCLASSES.items():
            group = self.WEAPON_TO_GROUP.get(wtype, "Other")
            print(f"  {wtype:15} -> {group}")
        
        print("\nArmor Types:")
        for atype, subclass in self.ARMOR_SUBCLASSES.items():
            print(f"  {atype}")
        
        print("\nArmor Slots:")
        for slot_id, slot_name in self.ARMOR_SLOTS.items():
            print(f"  {slot_name}")


def main():
    """Test the Ascension DB scraper."""
    scraper = AscensionDBScraper()
    
    print("Ascension DB Scraper")
    print("=" * 50)
    
    scraper.list_available_categories()
    
    print("\n\nTesting dagger scrape...")
    daggers = scraper.scrape_weapons("dagger", limit=20)
    print(f"Found {len(daggers)} daggers")
    if daggers:
        print(f"Sample IDs: {daggers[:10]}")
        print(f"TSM Group: {scraper.get_tsm_group_for_weapon('dagger')}")


if __name__ == "__main__":
    main()
