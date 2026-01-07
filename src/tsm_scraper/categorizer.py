"""
Categorizer for mapping items to TSM groups.

Uses rules from config file and item metadata to determine
the appropriate TSM group path for each item.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass 
class CategoryRule:
    """A rule for categorizing items."""
    item_class: str
    item_subclass: Optional[str] = None
    slot: Optional[str] = None
    group_path: str = ""
    priority: int = 0  # Higher priority rules are checked first


class ItemCategorizer:
    """Maps items to TSM group paths based on rules."""
    
    # Default category mappings
    DEFAULT_MAPPINGS = {
        # Weapons - Transmog category
        "weapon_mappings": {
            "Sword (1H)": "Transmog`Swords`One Hand",
            "Sword (2H)": "Transmog`Swords`Two Hand",
            "Axe (1H)": "Transmog`Axes`One Hand",
            "Axe (2H)": "Transmog`Axes`Two Hand",
            "Mace (1H)": "Transmog`Maces`One Hand",
            "Mace (2H)": "Transmog`Maces`Two Hand",
            "Dagger": "Transmog`Daggers",
            "Staff": "Transmog`Staves",
            "Polearm": "Transmog`Polearms",
            "Bow": "Transmog`Bows",
            "Gun": "Transmog`Guns",
            "Crossbow": "Transmog`Crossbow",
            "Wand": "Transmog`Wands",
            "Thrown": "Transmog`Throwing",
            "Fist Weapon": "Transmog`Fist Weapons",
            "Fishing Pole": "Tradeskills`Fishing`Rods"
        },
        
        # Armor by type and slot
        "armor_mappings": {
            "Cloth": {
                "Head": "Transmog`Cloth`Helm",
                "Shoulder": "Transmog`Cloth`Shoulders",
                "Chest": "Transmog`Cloth`Chest",
                "Robe": "Transmog`Cloth`Chest",
                "Waist": "Transmog`Cloth`Waist",
                "Legs": "Transmog`Cloth`Legs",
                "Feet": "Transmog`Cloth`Feet",
                "Wrists": "Transmog`Cloth`Wrists",
                "Hands": "Transmog`Cloth`Hands",
                "Back": "Transmog`Cloth`Back"
            },
            "Leather": {
                "Head": "Transmog`Leather`Helm",
                "Shoulder": "Transmog`Leather`Shoulders",
                "Chest": "Transmog`Leather`Chest",
                "Waist": "Transmog`Leather`Waist",
                "Legs": "Transmog`Leather`Legs",
                "Feet": "Transmog`Leather`Feet",
                "Wrists": "Transmog`Leather`Wrists",
                "Hands": "Transmog`Leather`Hands"
            },
            "Mail": {
                "Head": "Transmog`Mail`Helm",
                "Shoulder": "Transmog`Mail`Shoulders",
                "Chest": "Transmog`Mail`Chest",
                "Waist": "Transmog`Mail`Waist",
                "Legs": "Transmog`Mail`Legs",
                "Feet": "Transmog`Mail`Feet",
                "Wrists": "Transmog`Mail`Wrists",
                "Hands": "Transmog`Mail`Hands"
            },
            "Plate": {
                "Head": "Transmog`Plate`Helm",
                "Shoulder": "Transmog`Plate`Shoulders",
                "Chest": "Transmog`Plate`Chest",
                "Waist": "Transmog`Plate`Waist",
                "Legs": "Transmog`Plate`Legs",
                "Feet": "Transmog`Plate`Feet",
                "Wrists": "Transmog`Plate`Wrists",
                "Hands": "Transmog`Plate`Hands"
            },
            "Shield": "Transmog`Offhand",
            "Miscellaneous": {
                "Off Hand": "Transmog`Offhand",
                "Held In Off-hand": "Transmog`Offhand",
                "Tabard": "Transmog`Tabards",
                "Shirt": "Transmog`Cloth`Shirts"
            }
        },
        
        # Consumables
        "consumable_mappings": {
            "Potion": "Tradeskills`Alchemy`Potions",
            "Elixir": "Tradeskills`Alchemy`Elixirs",
            "Flask": "Tradeskills`Alchemy`Flasks",
            "Food": "Tradeskills`Cooking`Eadibles",
            "Drink": "Tradeskills`Cooking`Drinks",
            "Bandage": "Tradeskills`FirstAid`Bandages",
            "Scroll": "Scrolls"
        },
        
        # Trade Goods
        "trade_goods_mappings": {
            "Metal & Stone": "Tradeskills`Materials`Mining",
            "Herb": "Tradeskills`Materials`Herbalism",
            "Leather": "Tradeskills`Materials`Skinning",
            "Cloth": "Tradeskills`Tailoring`Cloth",
            "Meat": "Tradeskills`Cooking`Meats",
            "Elemental": "Tradeskills`Materials`Elemental",
            "Enchanting": "Tradeskills`Enchanting`Reagents",
            "Jewelcrafting": "Tradeskills`Jewelcrafting`Reagents",
            "Engineering": "Tradeskills`Engineering`Reagents"
        },
        
        # Recipes
        "recipe_mappings": {
            "Alchemy": "Patterns`Alchemy",
            "Blacksmithing": "Patterns`Blacksmithing",
            "Cooking": "Patterns`Cooking",
            "Enchanting": "Patterns`Enchanting",
            "Engineering": "Patterns`Engineering",
            "First Aid": "Patterns`First Aid",
            "Jewelcrafting": "Patterns`Jewelcrafting",
            "Leatherworking": "Patterns`Leatherworking",
            "Tailoring": "Patterns`Tailoring"
        },
        
        # Gems
        "gem_mappings": {
            "Red": "Tradeskills`Jewelcrafting`Gems",
            "Blue": "Tradeskills`Jewelcrafting`Gems",
            "Yellow": "Tradeskills`Jewelcrafting`Gems",
            "Purple": "Tradeskills`Jewelcrafting`Gems",
            "Green": "Tradeskills`Jewelcrafting`Gems",
            "Orange": "Tradeskills`Jewelcrafting`Gems",
            "Meta": "Tradeskills`Jewelcrafting`Gems",
            "Simple": "Tradeskills`Jewelcrafting`Gems",
            "Prismatic": "Tradeskills`Jewelcrafting`Gems"
        },
        
        # Containers
        "container_mappings": {
            "Bag": "Tradeskills`Tailoring`Bags",
            "Soul Bag": "Tradeskills`Tailoring`Bags",
            "Herb Bag": "Tradeskills`Tailoring`Bags",
            "Enchanting Bag": "Tradeskills`Tailoring`Bags",
            "Engineering Bag": "Tradeskills`Tailoring`Bags",
            "Gem Bag": "Tradeskills`Tailoring`Bags",
            "Mining Bag": "Tradeskills`Tailoring`Bags",
            "Leatherworking Bag": "Tradeskills`Tailoring`Bags",
            "Inscription Bag": "Tradeskills`Tailoring`Bags",
            "Tackle Box": "Tradeskills`Tailoring`Bags"
        }
    }
    
    UNCATEGORIZED_GROUP = "Other"
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else None
        self.mappings = self.DEFAULT_MAPPINGS.copy()
        
        if self.config_path and self.config_path.exists():
            self._load_config()
    
    def _load_config(self):
        """Load custom mappings from config file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                custom = json.load(f)
                # Merge custom mappings with defaults
                for key, value in custom.items():
                    if key in self.mappings and isinstance(value, dict):
                        self.mappings[key].update(value)
                    else:
                        self.mappings[key] = value
        except Exception as e:
            print(f"Warning: Could not load custom config: {e}")
    
    def save_config(self, path: Optional[str] = None):
        """Save current mappings to config file."""
        save_path = Path(path) if path else self.config_path
        if save_path:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, indent=2)
    
    def categorize(
        self, 
        item_class: str, 
        item_subclass: str = "", 
        slot: str = "",
        name: str = ""
    ) -> str:
        """
        Determine the TSM group path for an item.
        
        Args:
            item_class: Main item class (Weapon, Armor, Consumable, etc.)
            item_subclass: Item subclass (Sword, Cloth, Potion, etc.)
            slot: Equipment slot (Head, Chest, One-Hand, etc.)
            name: Item name (for fallback pattern matching)
            
        Returns:
            TSM group path string
        """
        # Weapons
        if item_class == "Weapon":
            weapons = self.mappings.get("weapon_mappings", {})
            if item_subclass in weapons:
                return weapons[item_subclass]
        
        # Armor
        if item_class == "Armor":
            armor = self.mappings.get("armor_mappings", {})
            if item_subclass in armor:
                subclass_map = armor[item_subclass]
                if isinstance(subclass_map, dict):
                    if slot in subclass_map:
                        return subclass_map[slot]
                    # Try without exact slot match
                    for slot_key, group in subclass_map.items():
                        if slot_key.lower() in slot.lower():
                            return group
                else:
                    return subclass_map
        
        # Consumables
        if item_class == "Consumable":
            consumables = self.mappings.get("consumable_mappings", {})
            if item_subclass in consumables:
                return consumables[item_subclass]
            # Try name-based matching
            name_lower = name.lower()
            if "potion" in name_lower:
                return consumables.get("Potion", self.UNCATEGORIZED_GROUP)
            if "elixir" in name_lower:
                return consumables.get("Elixir", self.UNCATEGORIZED_GROUP)
            if "flask" in name_lower:
                return consumables.get("Flask", self.UNCATEGORIZED_GROUP)
            if "scroll" in name_lower:
                return consumables.get("Scroll", self.UNCATEGORIZED_GROUP)
        
        # Trade Goods
        if item_class == "Trade Goods":
            trade = self.mappings.get("trade_goods_mappings", {})
            if item_subclass in trade:
                return trade[item_subclass]
        
        # Recipes
        if item_class == "Recipe":
            recipes = self.mappings.get("recipe_mappings", {})
            if item_subclass in recipes:
                return recipes[item_subclass]
        
        # Gems
        if item_class == "Gem":
            gems = self.mappings.get("gem_mappings", {})
            if item_subclass in gems:
                return gems[item_subclass]
            return "Tradeskills`Jewelcrafting`Gems"
        
        # Containers
        if item_class == "Container":
            containers = self.mappings.get("container_mappings", {})
            if item_subclass in containers:
                return containers[item_subclass]
            return "Tradeskills`Tailoring`Bags"
        
        # Projectile (Ammo)
        if item_class == "Projectile":
            return "Ammo"
        
        # Quest items
        if item_class == "Quest":
            return "Quest"
        
        # Junk
        if item_class == "Junk":
            return "Trash"
        
        # Default to uncategorized
        return self.UNCATEGORIZED_GROUP
    
    def categorize_batch(
        self, 
        items: List[dict]
    ) -> Dict[str, List[int]]:
        """
        Categorize multiple items.
        
        Args:
            items: List of dicts with 'id', 'item_class', 'item_subclass', 'slot', 'name'
            
        Returns:
            Dict mapping group paths to lists of item IDs
        """
        result: Dict[str, List[int]] = {}
        
        for item in items:
            group = self.categorize(
                item_class=item.get('item_class', ''),
                item_subclass=item.get('item_subclass', ''),
                slot=item.get('slot', ''),
                name=item.get('name', '')
            )
            
            if group not in result:
                result[group] = []
            result[group].append(item['id'])
        
        return result
    
    def get_available_groups(self) -> List[str]:
        """Get list of all known TSM groups from mappings."""
        groups: Set[str] = set()
        
        def extract_groups(obj):
            if isinstance(obj, str):
                groups.add(obj)
            elif isinstance(obj, dict):
                for value in obj.values():
                    extract_groups(value)
        
        for mapping in self.mappings.values():
            extract_groups(mapping)
        
        return sorted(groups)
    
    def add_custom_mapping(
        self, 
        item_class: str, 
        group_path: str,
        item_subclass: Optional[str] = None,
        slot: Optional[str] = None
    ):
        """Add a custom mapping rule."""
        # Determine which mapping dict to use
        if item_class == "Weapon":
            mapping_key = "weapon_mappings"
            key = item_subclass or item_class
        elif item_class == "Armor":
            mapping_key = "armor_mappings"
            if item_subclass:
                if item_subclass not in self.mappings[mapping_key]:
                    self.mappings[mapping_key][item_subclass] = {}
                if slot:
                    self.mappings[mapping_key][item_subclass][slot] = group_path
                else:
                    self.mappings[mapping_key][item_subclass] = group_path
                return
            key = item_class
        elif item_class == "Consumable":
            mapping_key = "consumable_mappings"
            key = item_subclass or item_class
        else:
            # Create custom mapping category
            mapping_key = "custom_mappings"
            if mapping_key not in self.mappings:
                self.mappings[mapping_key] = {}
            key = f"{item_class}:{item_subclass or ''}"
        
        if mapping_key not in self.mappings:
            self.mappings[mapping_key] = {}
        self.mappings[mapping_key][key] = group_path


def main():
    """Test the categorizer."""
    categorizer = ItemCategorizer()
    
    test_items = [
        {"item_class": "Weapon", "item_subclass": "Sword (1H)", "name": "Test Sword"},
        {"item_class": "Armor", "item_subclass": "Cloth", "slot": "Head", "name": "Test Hat"},
        {"item_class": "Consumable", "item_subclass": "Potion", "name": "Healing Potion"},
        {"item_class": "Unknown", "item_subclass": "Unknown", "name": "Mystery Item"}
    ]
    
    for item in test_items:
        group = categorizer.categorize(
            item.get("item_class", ""),
            item.get("item_subclass", ""),
            item.get("slot", ""),
            item.get("name", "")
        )
        print(f"{item['name']}: {group}")
    
    print("\nAvailable groups:")
    for group in categorizer.get_available_groups()[:10]:
        print(f"  {group}")


if __name__ == "__main__":
    main()
