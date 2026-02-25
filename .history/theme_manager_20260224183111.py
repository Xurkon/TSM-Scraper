"""
TSM-Scraper - Theme Manager

Manages application themes with support for built-in and custom themes.
Provides live color updates and persistence.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Callable, Optional, Any


@dataclass
class Theme:
    """Complete theme definition with all color properties."""
    
    name: str = "Custom Theme"
    builtin: bool = False
    
    # Backgrounds
    bg_darkest: str = "#0d0d0d"
    bg_dark: str = "#1a1a1a"
    bg_medium: str = "#242428"
    bg_light: str = "#2d2d32"
    bg_hover: str = "#3a3a40"
    bg_selected: str = "#404048"
    
    # Borders
    border_dark: str = "#333338"
    border_light: str = "#454550"
    
    # Text
    text_white: str = "#ffffff"
    text_light: str = "#e0e0e0"
    text_gray: str = "#888890"
    text_dark: str = "#666670"
    
    # Accents
    accent_primary: str = "#00ccff"      # Cyan - headers, links
    accent_primary_dark: str = "#0099cc"
    accent_secondary: str = "#ffd100"    # Gold - TSM branding
    accent_secondary_dark: str = "#cc9900"
    accent_gold: str = "#ffd100"          # Gold for group headers
    
    # Status colors
    color_success: str = "#00ff00"
    color_success_dark: str = "#00cc00"
    color_warning: str = "#ff8800"
    color_error: str = "#ff4444"
    
    # Item quality colors (WoW style)
    quality_epic: str = "#cc66ff"
    quality_rare: str = "#0088ff"
    quality_uncommon: str = "#00ff00"
    quality_common: str = "#ffffff"
    
    # Font sizes
    font_size_header: int = 14
    font_size_label: int = 12
    font_size_body: int = 11
    font_size_small: int = 10
    font_size_tiny: int = 9
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert theme to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Theme':
        """Create theme from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def copy(self) -> 'Theme':
        """Create a copy of this theme."""
        return Theme.from_dict(self.to_dict())


# =============================================================================
# Built-in Themes
# =============================================================================

BUILTIN_THEMES = {
    "tsm_dark": Theme(
        name="TSM Dark",
        builtin=True,
        # Dark blue-tinted backgrounds (matching TSM)
        bg_darkest="#0a0a10",
        bg_dark="#12141a",
        bg_medium="#1a1c24",
        bg_light="#24262e",
        bg_hover="#2e3038",
        bg_selected="#383a44",
        # Subtle blue-gray borders
        border_dark="#2a2c36",
        border_light="#3a3c48",
        # Text colors
        text_white="#ffffff",
        text_light="#d4d4dc",
        text_gray="#8888a0",
        text_dark="#606078",
        # Cyan primary accent (links/headers)
        accent_primary="#2090c0",
        accent_primary_dark="#186890",
        # Gold/yellow secondary accent (TSM branding)
        accent_secondary="#e8b400",
        accent_secondary_dark="#b88c00",
        # Maroon/red tertiary for tab bar highlights
        color_success="#00cc66",
        color_success_dark="#00994d",
        color_warning="#e08000",
        color_error="#cc3333",
        # WoW item quality colors
        quality_epic="#a335ee",
        quality_rare="#0070dd",
        quality_uncommon="#1eff00",
        quality_common="#ffffff",
    ),
    
    "midnight_blue": Theme(
        name="Midnight Blue",
        builtin=True,
        bg_darkest="#0a0a14",
        bg_dark="#12121f",
        bg_medium="#1a1a2e",
        bg_light="#25253d",
        bg_hover="#32324a",
        bg_selected="#3f3f58",
        border_dark="#2a2a42",
        border_light="#3d3d55",
        text_white="#ffffff",
        text_light="#d8d8e8",
        text_gray="#8888a0",
        text_dark="#606078",
        accent_primary="#7b68ee",
        accent_primary_dark="#5d4ec2",
        accent_secondary="#ff6b9d",
        accent_secondary_dark="#cc4477",
        color_success="#50fa7b",
        color_success_dark="#40c862",
        color_warning="#ffb86c",
        color_error="#ff5555",
        quality_epic="#bd93f9",
        quality_rare="#8be9fd",
        quality_uncommon="#50fa7b",
        quality_common="#f8f8f2",
    ),
    
    "forest": Theme(
        name="Forest",
        builtin=True,
        bg_darkest="#0a100d",
        bg_dark="#121a14",
        bg_medium="#1a251c",
        bg_light="#223024",
        bg_hover="#2d402f",
        bg_selected="#385038",
        border_dark="#2a3a2c",
        border_light="#3d503f",
        text_white="#ffffff",
        text_light="#d8e8da",
        text_gray="#88a08a",
        text_dark="#608062",
        accent_primary="#7cb342",
        accent_primary_dark="#5c8c32",
        accent_secondary="#ffc107",
        accent_secondary_dark="#cc9a00",
        color_success="#4caf50",
        color_success_dark="#388e3c",
        color_warning="#ff9800",
        color_error="#f44336",
        quality_epic="#ce93d8",
        quality_rare="#64b5f6",
        quality_uncommon="#81c784",
        quality_common="#e0e0e0",
    ),
    
    "light": Theme(
        name="Light",
        builtin=True,
        bg_darkest="#ffffff",
        bg_dark="#f5f5f5",
        bg_medium="#ececec",
        bg_light="#e0e0e0",
        bg_hover="#d5d5d5",
        bg_selected="#c8c8c8",
        border_dark="#cccccc",
        border_light="#b0b0b0",
        text_white="#1a1a1a",
        text_light="#333333",
        text_gray="#666666",
        text_dark="#999999",
        accent_primary="#0077cc",
        accent_primary_dark="#005599",
        accent_secondary="#cc8800",
        accent_secondary_dark="#996600",
        color_success="#228b22",
        color_success_dark="#196919",
        color_warning="#cc6600",
        color_error="#cc2222",
        quality_epic="#9932cc",
        quality_rare="#0066cc",
        quality_uncommon="#228b22",
        quality_common="#333333",
    ),
}


# =============================================================================
# Theme Manager
# =============================================================================

class ThemeManager:
    """
    Manages application themes with persistence and live updates.
    
    Usage:
        manager = ThemeManager()
        manager.load()
        
        # Get current color
        bg = manager.get('bg_dark')
        
        # Switch theme
        manager.set_theme('midnight_blue')
        
        # Register for updates
        manager.on_change(my_callback)
    """
    
    CONFIG_PATH = Path(__file__).parent / "config" / "themes.json"
    
    def __init__(self):
        self.themes: Dict[str, Theme] = {}
        self.active_theme_id: str = "tsm_dark"
        self._callbacks: List[Callable[[], None]] = []
        
        # Load built-in themes
        for theme_id, theme in BUILTIN_THEMES.items():
            self.themes[theme_id] = theme.copy()
    
    @property
    def current(self) -> Theme:
        """Get the currently active theme."""
        return self.themes.get(self.active_theme_id, BUILTIN_THEMES["tsm_dark"])
    
    def get(self, color_name: str) -> str:
        """Get a color value from the current theme."""
        return getattr(self.current, color_name, "#ff00ff")  # Magenta for missing
    
    def set_color(self, color_name: str, value: str):
        """Set a color in the current theme."""
        if hasattr(self.current, color_name):
            setattr(self.current, color_name, value)
            self._notify()
    
    def get_theme_list(self) -> List[tuple]:
        """Get list of (id, name, builtin) for all themes."""
        return [(tid, t.name, t.builtin) for tid, t in self.themes.items()]
    
    def set_theme(self, theme_id: str):
        """Switch to a different theme."""
        if theme_id in self.themes:
            self.active_theme_id = theme_id
            self._notify()
            self.save()
    
    def create_custom_theme(self, name: str, base_theme_id: str = None) -> str:
        """Create a new custom theme, optionally based on existing theme."""
        base = self.themes.get(base_theme_id, self.current)
        new_theme = base.copy()
        new_theme.name = name
        new_theme.builtin = False
        
        # Generate unique ID
        theme_id = name.lower().replace(" ", "_")
        counter = 1
        while theme_id in self.themes:
            theme_id = f"{name.lower().replace(' ', '_')}_{counter}"
            counter += 1
        
        self.themes[theme_id] = new_theme
        self.save()
        return theme_id
    
    def delete_theme(self, theme_id: str) -> bool:
        """Delete a custom theme. Cannot delete built-in themes."""
        if theme_id in self.themes and not self.themes[theme_id].builtin:
            del self.themes[theme_id]
            if self.active_theme_id == theme_id:
                self.active_theme_id = "tsm_dark"
            self.save()
            self._notify()
            return True
        return False
    
    def reset_theme(self, theme_id: str = None):
        """Reset a theme to its default values."""
        theme_id = theme_id or self.active_theme_id
        if theme_id in BUILTIN_THEMES:
            self.themes[theme_id] = BUILTIN_THEMES[theme_id].copy()
            self._notify()
            self.save()
    
    def on_change(self, callback: Callable[[], None]):
        """Register a callback to be called when theme changes."""
        self._callbacks.append(callback)
    
    def off_change(self, callback: Callable[[], None]):
        """Unregister a change callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify(self):
        """Notify all registered callbacks of theme change."""
        for callback in self._callbacks:
            try:
                callback()
            except Exception:
                pass
    
    def load(self):
        """Load themes from config file."""
        try:
            if self.CONFIG_PATH.exists():
                with open(self.CONFIG_PATH, 'r') as f:
                    data = json.load(f)
                
                self.active_theme_id = data.get("active_theme", "tsm_dark")
                
                # Load custom themes
                for theme_id, theme_data in data.get("themes", {}).items():
                    self.themes[theme_id] = Theme.from_dict(theme_data)
                
                # Load overrides for built-in themes
                for theme_id, override_data in data.get("builtin_overrides", {}).items():
                    if theme_id in self.themes:
                        # Apply overrides to built-in theme
                        for key, value in override_data.items():
                            if hasattr(self.themes[theme_id], key):
                                setattr(self.themes[theme_id], key, value)
        except Exception as e:
            pass
    
    def save(self):
        """Save themes to config file."""
        try:
            self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "active_theme": self.active_theme_id,
                "themes": {},
                "builtin_overrides": {}
            }
            
            for theme_id, theme in self.themes.items():
                if not theme.builtin:
                    # Save full custom themes
                    data["themes"][theme_id] = theme.to_dict()
                else:
                    # For built-in themes, save only what differs from defaults
                    default = BUILTIN_THEMES.get(theme_id)
                    if default:
                        overrides = {}
                        for field_name in Theme.__dataclass_fields__:
                            if field_name in ('name', 'builtin'):
                                continue
                            current_val = getattr(theme, field_name)
                            default_val = getattr(default, field_name)
                            if current_val != default_val:
                                overrides[field_name] = current_val
                        if overrides:
                            data["builtin_overrides"][theme_id] = overrides
            
            with open(self.CONFIG_PATH, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            pass
    
    def export_theme(self, theme_id: str, path: Path) -> bool:
        """Export a theme to a JSON file."""
        try:
            if theme_id in self.themes:
                with open(path, 'w') as f:
                    json.dump(self.themes[theme_id].to_dict(), f, indent=2)
                return True
        except Exception:
            pass
        return False
    
    def import_theme(self, path: Path) -> Optional[str]:
        """Import a theme from a JSON file. Returns the new theme ID."""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            theme = Theme.from_dict(data)
            theme.builtin = False
            
            theme_id = theme.name.lower().replace(" ", "_")
            counter = 1
            while theme_id in self.themes:
                theme_id = f"{theme.name.lower().replace(' ', '_')}_{counter}"
                counter += 1
            
            self.themes[theme_id] = theme
            self.save()
            return theme_id
        except Exception:
            return None


# =============================================================================
# Color Property Metadata (for UI)
# =============================================================================

COLOR_CATEGORIES = {
    "Backgrounds": [
        ("bg_darkest", "Darkest Background"),
        ("bg_dark", "Dark Background"),
        ("bg_medium", "Medium Background"),
        ("bg_light", "Light Background"),
        ("bg_hover", "Hover State"),
        ("bg_selected", "Selected Item"),
    ],
    "Borders": [
        ("border_dark", "Dark Border"),
        ("border_light", "Light Border"),
    ],
    "Text": [
        ("text_white", "White Text"),
        ("text_light", "Light Text"),
        ("text_gray", "Gray Text"),
        ("text_dark", "Dark Text"),
    ],
    "Accents": [
        ("accent_primary", "Primary Accent"),
        ("accent_primary_dark", "Primary Dark"),
        ("accent_secondary", "Secondary Accent"),
        ("accent_secondary_dark", "Secondary Dark"),
    ],
    "Status": [
        ("color_success", "Success"),
        ("color_success_dark", "Success Dark"),
        ("color_warning", "Warning"),
        ("color_error", "Error"),
    ],
    "Item Quality": [
        ("quality_epic", "Epic"),
        ("quality_rare", "Rare"),
        ("quality_uncommon", "Uncommon"),
        ("quality_common", "Common"),
    ],
}


# Global theme manager instance
theme_manager = ThemeManager()
