"""
Turtle WoW Database Scraper (database.turtle-wow.org)

Scrapes item data from Turtle WoW's database for TSM integration.
Similar structure to Ascension DB with ?item=ID pattern.

Note: TSM support on Turtle WoW is being backported.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class TurtleItem:
    """Represents an item from Turtle WoW database."""
    id: int
    name: str = ""
    item_class: str = ""
    item_subclass: str = ""
    slot: str = ""
    quality: int = 0
    level: int = 0
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'item_class': self.item_class,
            'item_subclass': self.item_subclass,
            'slot': self.slot,
            'quality': self.quality,
            'level': self.level
        }


class TurtleWoWScraper:
    """Scraper for Turtle WoW item database."""
    
    BASE_URL = "https://database.turtle-wow.org"
    
    # Item class IDs (Classic-style)
    CLASS_WEAPON = 2
    CLASS_ARMOR = 4
    CLASS_CONSUMABLE = 0
    CLASS_CONTAINER = 1
    CLASS_TRADE_GOODS = 7
    CLASS_RECIPE = 9
    CLASS_GEM = 3
    CLASS_PROJECTILE = 6
    
    # Category definitions similar to Ascension
    ALL_CATEGORIES = {
        # Weapons
        "sword_1h": ("weapon", 7, "Transmog`Swords`One Hand"),
        "sword_2h": ("weapon", 8, "Transmog`Swords`Two Hand"),
        "axe_1h": ("weapon", 0, "Transmog`Axes`One Hand"),
        "axe_2h": ("weapon", 1, "Transmog`Axes`Two Hand"),
        "mace_1h": ("weapon", 4, "Transmog`Maces`One Hand"),
        "mace_2h": ("weapon", 5, "Transmog`Maces`Two Hand"),
        "dagger": ("weapon", 15, "Transmog`Daggers"),
        "fist": ("weapon", 13, "Transmog`Fist Weapons"),
        "polearm": ("weapon", 6, "Transmog`Polearms"),
        "staff": ("weapon", 10, "Transmog`Staves"),
        "bow": ("weapon", 2, "Transmog`Bows"),
        "crossbow": ("weapon", 18, "Transmog`Crossbows"),
        "gun": ("weapon", 3, "Transmog`Guns"),
        "wand": ("weapon", 19, "Transmog`Wands"),
        "thrown": ("weapon", 16, "Transmog`Thrown"),
        
        # Armor - Cloth
        "cloth_head": ("armor", 1, "Transmog`Cloth`Head"),
        "cloth_shoulder": ("armor", 1, "Transmog`Cloth`Shoulder"),
        "cloth_chest": ("armor", 1, "Transmog`Cloth`Chest"),
        "cloth_waist": ("armor", 1, "Transmog`Cloth`Waist"),
        "cloth_legs": ("armor", 1, "Transmog`Cloth`Legs"),
        "cloth_feet": ("armor", 1, "Transmog`Cloth`Feet"),
        "cloth_wrist": ("armor", 1, "Transmog`Cloth`Wrist"),
        "cloth_hands": ("armor", 1, "Transmog`Cloth`Hands"),
        
        # Armor - Leather
        "leather_head": ("armor", 2, "Transmog`Leather`Head"),
        "leather_shoulder": ("armor", 2, "Transmog`Leather`Shoulder"),
        "leather_chest": ("armor", 2, "Transmog`Leather`Chest"),
        "leather_waist": ("armor", 2, "Transmog`Leather`Waist"),
        "leather_legs": ("armor", 2, "Transmog`Leather`Legs"),
        "leather_feet": ("armor", 2, "Transmog`Leather`Feet"),
        "leather_wrist": ("armor", 2, "Transmog`Leather`Wrist"),
        "leather_hands": ("armor", 2, "Transmog`Leather`Hands"),
        
        # Armor - Mail
        "mail_head": ("armor", 3, "Transmog`Mail`Head"),
        "mail_shoulder": ("armor", 3, "Transmog`Mail`Shoulder"),
        "mail_chest": ("armor", 3, "Transmog`Mail`Chest"),
        "mail_waist": ("armor", 3, "Transmog`Mail`Waist"),
        "mail_legs": ("armor", 3, "Transmog`Mail`Legs"),
        "mail_feet": ("armor", 3, "Transmog`Mail`Feet"),
        "mail_wrist": ("armor", 3, "Transmog`Mail`Wrist"),
        "mail_hands": ("armor", 3, "Transmog`Mail`Hands"),
        
        # Armor - Plate
        "plate_head": ("armor", 4, "Transmog`Plate`Head"),
        "plate_shoulder": ("armor", 4, "Transmog`Plate`Shoulder"),
        "plate_chest": ("armor", 4, "Transmog`Plate`Chest"),
        "plate_waist": ("armor", 4, "Transmog`Plate`Waist"),
        "plate_legs": ("armor", 4, "Transmog`Plate`Legs"),
        "plate_feet": ("armor", 4, "Transmog`Plate`Feet"),
        "plate_wrist": ("armor", 4, "Transmog`Plate`Wrist"),
        "plate_hands": ("armor", 4, "Transmog`Plate`Hands"),
        
        # Other Armor
        "shield": ("armor", 6, "Transmog`Shields"),
        "offhand": ("armor", 0, "Transmog`Off-Hand"),
        "cloak": ("armor", 1, "Transmog`Cloaks"),
    }
    
    def __init__(self, cache_dir: str = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.rate_limit_delay = 1.0
    
    def scrape_item_ids_from_page(self, url: str) -> List[int]:
        """Scrape item IDs from a category page."""
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url)
            
            if response.status_code != 200:
                print(f"Error fetching {url}: {response.status_code}")
                return []
            
            # Parse item IDs from links
            item_ids = []
            pattern = r'\?item=(\d+)'
            matches = re.findall(pattern, response.text)
            
            seen = set()
            for match in matches:
                item_id = int(match)
                if item_id not in seen:
                    seen.add(item_id)
                    item_ids.append(item_id)
            
            return item_ids
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return []
    
    def get_item(self, item_id: int) -> Optional[TurtleItem]:
        """Get item details by ID."""
        url = f"{self.BASE_URL}/?item={item_id}"
        
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract item name from title
            title = soup.find('title')
            if title:
                name = title.get_text().split(' - ')[0].strip()
            else:
                name = f"Item {item_id}"
            
            return TurtleItem(id=item_id, name=name)
            
        except Exception as e:
            print(f"Error fetching item {item_id}: {e}")
            return None


def main():
    """Test the Turtle WoW scraper."""
    scraper = TurtleWoWScraper()
    
    print("=== Testing Turtle WoW Scraper ===\n")
    print(f"Base URL: {scraper.BASE_URL}")
    
    # Test single item lookup
    print("\nTesting item lookup (Lionheart Helm)...")
    item = scraper.get_item(12640)
    if item:
        print(f"  Found: {item.name} (ID: {item.id})")
    else:
        print("  Item not found")


if __name__ == "__main__":
    main()
