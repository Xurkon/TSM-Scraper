"""
TSM Item Scraper GUI

A modern graphical interface matching the in-game TSM addon style.
Features dark theme with cyan headers and gold accents.
"""

import sys
import json
import threading
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, colorchooser
except ImportError:
    print("tkinter is required but not available")
    sys.exit(1)

from tsm_scraper.ascension_scraper import AscensionDBScraper
from tsm_scraper.lua_parser import TSMLuaParser
from tsm_scraper.lua_writer import TSMLuaWriter
from theme_manager import theme_manager, Theme, COLOR_CATEGORIES


# ============================================================================
# TSM Color Scheme (dynamic from theme manager)
# ============================================================================

# Load saved theme on startup
theme_manager.load()


class Colors:
    """Dynamic color accessor that pulls from the active theme."""
    
    @staticmethod
    def get(name: str) -> str:
        return theme_manager.get(name)
    
    # Backgrounds - dynamic properties
    @property
    def BG_DARKEST(self): return theme_manager.get('bg_darkest')
    @property
    def BG_DARK(self): return theme_manager.get('bg_dark')
    @property
    def BG_MEDIUM(self): return theme_manager.get('bg_medium')
    @property
    def BG_LIGHT(self): return theme_manager.get('bg_light')
    @property
    def BG_HOVER(self): return theme_manager.get('bg_hover')
    @property
    def BG_SELECTED(self): return theme_manager.get('bg_selected')
    
    # Borders
    @property
    def BORDER_DARK(self): return theme_manager.get('border_dark')
    @property
    def BORDER_LIGHT(self): return theme_manager.get('border_light')
    
    # Text
    @property
    def TEXT_WHITE(self): return theme_manager.get('text_white')
    @property
    def TEXT_LIGHT(self): return theme_manager.get('text_light')
    @property
    def TEXT_GRAY(self): return theme_manager.get('text_gray')
    @property
    def TEXT_DARK(self): return theme_manager.get('text_dark')
    
    # Accents
    @property
    def CYAN(self): return theme_manager.get('accent_primary')
    @property
    def CYAN_DARK(self): return theme_manager.get('accent_primary_dark')
    @property
    def GOLD(self): return theme_manager.get('accent_secondary')
    @property
    def GOLD_DARK(self): return theme_manager.get('accent_secondary_dark')
    
    # Status colors
    @property
    def ORANGE(self): return theme_manager.get('color_warning')
    @property
    def GREEN(self): return theme_manager.get('color_success')
    @property
    def GREEN_DARK(self): return theme_manager.get('color_success_dark')
    @property
    def RED(self): return theme_manager.get('color_error')
    
    # Item quality
    @property
    def PURPLE(self): return theme_manager.get('quality_epic')
    @property
    def BLUE(self): return theme_manager.get('quality_rare')


# Create a singleton instance for backward compatibility
_colors = Colors()


class ColorsCompat:
    """Static-like access to Colors for backward compatibility."""
    BG_DARKEST = property(lambda self: _colors.BG_DARKEST)
    BG_DARK = property(lambda self: _colors.BG_DARK)
    BG_MEDIUM = property(lambda self: _colors.BG_MEDIUM)
    BG_LIGHT = property(lambda self: _colors.BG_LIGHT)
    BG_HOVER = property(lambda self: _colors.BG_HOVER)
    BG_SELECTED = property(lambda self: _colors.BG_SELECTED)
    BORDER_DARK = property(lambda self: _colors.BORDER_DARK)
    BORDER_LIGHT = property(lambda self: _colors.BORDER_LIGHT)
    TEXT_WHITE = property(lambda self: _colors.TEXT_WHITE)
    TEXT_LIGHT = property(lambda self: _colors.TEXT_LIGHT)
    TEXT_GRAY = property(lambda self: _colors.TEXT_GRAY)
    TEXT_DARK = property(lambda self: _colors.TEXT_DARK)
    CYAN = property(lambda self: _colors.CYAN)
    CYAN_DARK = property(lambda self: _colors.CYAN_DARK)
    GOLD = property(lambda self: _colors.GOLD)
    GOLD_DARK = property(lambda self: _colors.GOLD_DARK)
    ORANGE = property(lambda self: _colors.ORANGE)
    GREEN = property(lambda self: _colors.GREEN)
    GREEN_DARK = property(lambda self: _colors.GREEN_DARK)
    RED = property(lambda self: _colors.RED)
    PURPLE = property(lambda self: _colors.PURPLE)
    BLUE = property(lambda self: _colors.BLUE)


# For backward compatibility, use static-like access
Colors = type('Colors', (), {
    'BG_DARKEST': theme_manager.get('bg_darkest'),
    'BG_DARK': theme_manager.get('bg_dark'),
    'BG_MEDIUM': theme_manager.get('bg_medium'),
    'BG_LIGHT': theme_manager.get('bg_light'),
    'BG_HOVER': theme_manager.get('bg_hover'),
    'BG_SELECTED': theme_manager.get('bg_selected'),
    'BORDER_DARK': theme_manager.get('border_dark'),
    'BORDER_LIGHT': theme_manager.get('border_light'),
    'TEXT_WHITE': theme_manager.get('text_white'),
    'TEXT_LIGHT': theme_manager.get('text_light'),
    'TEXT_GRAY': theme_manager.get('text_gray'),
    'TEXT_DARK': theme_manager.get('text_dark'),
    'CYAN': theme_manager.get('accent_primary'),
    'CYAN_DARK': theme_manager.get('accent_primary_dark'),
    'GOLD': theme_manager.get('accent_secondary'),
    'GOLD_DARK': theme_manager.get('accent_secondary_dark'),
    'ORANGE': theme_manager.get('color_warning'),
    'GREEN': theme_manager.get('color_success'),
    'GREEN_DARK': theme_manager.get('color_success_dark'),
    'RED': theme_manager.get('color_error'),
    'PURPLE': theme_manager.get('quality_epic'),
    'BLUE': theme_manager.get('quality_rare'),
})()


# ============================================================================
# Custom Widgets
# ============================================================================

class ModernFrame(tk.Frame):
    """A modern styled frame with optional border."""
    def __init__(self, parent, border=False, **kwargs):
        bg = kwargs.pop('bg', Colors.BG_MEDIUM)
        super().__init__(parent, bg=bg, **kwargs)
        
        if border:
            self.configure(
                highlightbackground=Colors.BORDER_DARK,
                highlightthickness=1
            )


class ModernLabel(tk.Label):
    """A styled label."""
    def __init__(self, parent, style='normal', **kwargs):
        styles = {
            'normal': {'fg': Colors.TEXT_LIGHT, 'font': ('Segoe UI', 10)},
            'header': {'fg': Colors.CYAN, 'font': ('Segoe UI', 14, 'bold')},
            'subheader': {'fg': Colors.CYAN, 'font': ('Segoe UI', 11, 'bold')},
            'gold': {'fg': Colors.GOLD, 'font': ('Segoe UI', 10, 'bold')},
            'success': {'fg': Colors.GREEN, 'font': ('Segoe UI', 10)},
            'error': {'fg': Colors.RED, 'font': ('Segoe UI', 10)},
            'muted': {'fg': Colors.TEXT_GRAY, 'font': ('Segoe UI', 9)},
        }
        
        style_config = styles.get(style, styles['normal'])
        bg = kwargs.pop('bg', Colors.BG_MEDIUM)
        
        super().__init__(parent, bg=bg, **style_config, **kwargs)


class ModernButton(tk.Button):
    """A modern styled button with hover effects."""
    def __init__(self, parent, style='normal', **kwargs):
        self.style_type = style
        
        if style == 'accent':
            bg = Colors.CYAN_DARK
            fg = Colors.TEXT_WHITE
            hover_bg = Colors.CYAN
            active_bg = Colors.GOLD
        elif style == 'gold':
            bg = Colors.GOLD_DARK
            fg = Colors.BG_DARK
            hover_bg = Colors.GOLD
            active_bg = Colors.ORANGE
        else:
            bg = Colors.BG_LIGHT
            fg = Colors.TEXT_LIGHT
            hover_bg = Colors.BG_HOVER
            active_bg = Colors.CYAN_DARK
        
        self.normal_bg = bg
        self.hover_bg = hover_bg
        self.active_bg = active_bg
        
        super().__init__(
            parent,
            bg=bg,
            fg=fg,
            font=('Segoe UI', 10),
            relief='flat',
            cursor='hand2',
            activebackground=active_bg,
            activeforeground=fg,
            borderwidth=0,
            padx=15,
            pady=6,
            **kwargs
        )
        
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
    
    def _on_enter(self, e):
        if self['state'] != 'disabled':
            self.configure(bg=self.hover_bg)
    
    def _on_leave(self, e):
        if self['state'] != 'disabled':
            self.configure(bg=self.normal_bg)


class ModernEntry(tk.Entry):
    """A styled entry field."""
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=Colors.BG_LIGHT,
            fg=Colors.TEXT_LIGHT,
            insertbackground=Colors.CYAN,
            font=('Consolas', 10),
            relief='flat',
            borderwidth=0,
            **kwargs
        )


class ModernCheckbox(tk.Checkbutton):
    """A styled checkbox."""
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=Colors.BG_LIGHT,
            fg=Colors.TEXT_LIGHT,
            selectcolor=Colors.BG_DARK,
            activebackground=Colors.BG_HOVER,
            activeforeground=Colors.TEXT_WHITE,
            font=('Segoe UI', 9),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            **kwargs
        )


class ModernScrollbar(tk.Scrollbar):
    """A styled scrollbar."""
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=Colors.BG_LIGHT,
            troughcolor=Colors.BG_DARK,
            activebackground=Colors.BG_HOVER,
            relief='flat',
            borderwidth=0,
            width=12,
            **kwargs
        )


# ============================================================================
# Main Application
# ============================================================================

DEFAULT_TSM_PATH = r"c:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\TradeSkillMaster.lua"
CONFIG_PATH = Path(__file__).parent / "config" / "gui_config.json"


class TSMScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TSM Item Scraper")
        self.root.geometry("950x700")
        self.root.minsize(850, 600)
        self.root.configure(bg=Colors.BG_DARKEST)
        
        # Remove default window decorations for custom title bar (optional)
        # self.root.overrideredirect(True)
        
        # Configuration
        self.config = self.load_config()
        self.tsm_path = self.config.get("tsm_path", DEFAULT_TSM_PATH)
        
        # Components
        self.scraper = AscensionDBScraper()
        self.category_vars: Dict[str, tk.BooleanVar] = {}
        self.scrape_results: Dict[str, dict] = {}
        self.existing_ids: set = set()
        
        # Build UI
        self.create_widgets()
        self.load_tsm_info()
    
    def load_config(self) -> dict:
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def save_config(self):
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, 'w') as f:
                json.dump({"tsm_path": self.tsm_path}, f, indent=2)
        except:
            pass
    
    def create_widgets(self):
        """Build the main UI."""
        # Main container with padding
        main = ModernFrame(self.root, bg=Colors.BG_DARKEST)
        main.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Header bar
        self.create_header(main)
        
        # Content area with sidebar and main panel
        content = ModernFrame(main, bg=Colors.BG_DARKEST)
        content.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Left sidebar (TSM file info + categories)
        self.create_sidebar(content)
        
        # Right panel (results + log)
        self.create_main_panel(content)
    
    def create_header(self, parent):
        """Create the header bar with TSM branding."""
        header = ModernFrame(parent, bg=Colors.BG_DARK, border=True)
        header.pack(fill=tk.X)
        
        # Inner padding
        inner = ModernFrame(header, bg=Colors.BG_DARK)
        inner.pack(fill=tk.X, padx=15, pady=10)
        
        # TSM Logo/Title
        title_frame = ModernFrame(inner, bg=Colors.BG_DARK)
        title_frame.pack(side=tk.LEFT)
        
        # Gold "TSM" text
        tsm_label = tk.Label(
            title_frame, text="TSM", 
            bg=Colors.BG_DARK, fg=Colors.GOLD,
            font=('Segoe UI', 18, 'bold')
        )
        tsm_label.pack(side=tk.LEFT)
        
        # Cyan "Item Scraper" text
        scraper_label = tk.Label(
            title_frame, text=" Item Scraper",
            bg=Colors.BG_DARK, fg=Colors.CYAN,
            font=('Segoe UI', 18)
        )
        scraper_label.pack(side=tk.LEFT)
        
        # Right side - settings and status
        status_frame = ModernFrame(inner, bg=Colors.BG_DARK)
        status_frame.pack(side=tk.RIGHT)
        
        # Settings button
        settings_btn = ModernButton(
            status_frame, text="⚙ Settings",
            command=self.open_settings
        )
        settings_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.status_label = ModernLabel(
            status_frame, text="Ready", 
            style='muted', bg=Colors.BG_DARK
        )
        self.status_label.pack(side=tk.RIGHT)
    
    def create_sidebar(self, parent):
        """Create the left sidebar with file info and categories."""
        sidebar = ModernFrame(parent, bg=Colors.BG_MEDIUM, border=True)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar.configure(width=280)
        sidebar.pack_propagate(False)
        
        # TSM File Section
        file_section = ModernFrame(sidebar, bg=Colors.BG_MEDIUM)
        file_section.pack(fill=tk.X, padx=10, pady=10)
        
        ModernLabel(
            file_section, text="TSM SavedVariables",
            style='subheader', bg=Colors.BG_MEDIUM
        ).pack(anchor=tk.W)
        
        # File path
        self.tsm_path_var = tk.StringVar(value=Path(self.tsm_path).name)
        path_frame = ModernFrame(file_section, bg=Colors.BG_MEDIUM)
        path_frame.pack(fill=tk.X, pady=(5, 0))
        
        path_entry = ModernEntry(path_frame, textvariable=self.tsm_path_var, width=25)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_btn = ModernButton(path_frame, text="...", command=self.browse_tsm_file)
        browse_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # TSM Info
        self.tsm_info = ModernLabel(
            file_section, text="Loading...",
            style='muted', bg=Colors.BG_MEDIUM
        )
        self.tsm_info.pack(anchor=tk.W, pady=(5, 0))
        
        # Separator
        sep = ModernFrame(sidebar, bg=Colors.BORDER_DARK, height=1)
        sep.pack(fill=tk.X, padx=10, pady=10)
        
        # Categories Section
        cat_header = ModernFrame(sidebar, bg=Colors.BG_MEDIUM)
        cat_header.pack(fill=tk.X, padx=10)
        
        ModernLabel(
            cat_header, text="Categories",
            style='subheader', bg=Colors.BG_MEDIUM
        ).pack(side=tk.LEFT)
        
        # Quick select buttons
        quick_frame = ModernFrame(sidebar, bg=Colors.BG_MEDIUM)
        quick_frame.pack(fill=tk.X, padx=10, pady=5)
        
        for text, cmd in [("All", self.select_all), ("None", self.deselect_all)]:
            btn = ModernButton(quick_frame, text=text, command=cmd)
            btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Category list with scrollbar
        cat_container = ModernFrame(sidebar, bg=Colors.BG_LIGHT)
        cat_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        canvas = tk.Canvas(
            cat_container, bg=Colors.BG_LIGHT,
            highlightthickness=0, borderwidth=0
        )
        scrollbar = ModernScrollbar(cat_container, command=canvas.yview)
        self.cat_frame = ModernFrame(canvas, bg=Colors.BG_LIGHT)
        
        self.cat_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.cat_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mouse wheel
        def on_wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_wheel)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.create_category_list()
        
        # Action buttons at bottom
        action_frame = ModernFrame(sidebar, bg=Colors.BG_MEDIUM)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.scrape_btn = ModernButton(
            action_frame, text="🔍 Scrape", 
            style='accent', command=self.start_scrape
        )
        self.scrape_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.import_btn = ModernButton(
            action_frame, text="📥 Import to TSM",
            style='gold', command=self.start_import, state='disabled'
        )
        self.import_btn.pack(fill=tk.X)
    
    def create_main_panel(self, parent):
        """Create the main content panel on the right."""
        panel = ModernFrame(parent, bg=Colors.BG_MEDIUM, border=True)
        panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Results header
        header = ModernFrame(panel, bg=Colors.BG_MEDIUM)
        header.pack(fill=tk.X, padx=15, pady=10)
        
        ModernLabel(
            header, text="Scrape Results",
            style='subheader', bg=Colors.BG_MEDIUM
        ).pack(side=tk.LEFT)
        
        self.results_summary = ModernLabel(
            header, text="Select categories and click Scrape",
            style='muted', bg=Colors.BG_MEDIUM
        )
        self.results_summary.pack(side=tk.RIGHT)
        
        # Results list
        results_container = ModernFrame(panel, bg=Colors.BG_LIGHT)
        results_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        # Create treeview with custom style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Custom.Treeview",
            background=Colors.BG_LIGHT,
            foreground=Colors.TEXT_LIGHT,
            fieldbackground=Colors.BG_LIGHT,
            borderwidth=0,
            font=('Segoe UI', 9)
        )
        style.configure("Custom.Treeview.Heading",
            background=Colors.BG_DARK,
            foreground=Colors.CYAN,
            borderwidth=0,
            font=('Segoe UI', 9, 'bold')
        )
        style.map("Custom.Treeview",
            background=[('selected', Colors.BG_SELECTED)],
            foreground=[('selected', Colors.GOLD)]
        )
        
        columns = ('category', 'group', 'found', 'new', 'status')
        self.results_tree = ttk.Treeview(
            results_container, columns=columns, 
            show='headings', style='Custom.Treeview'
        )
        
        self.results_tree.heading('category', text='Category')
        self.results_tree.heading('group', text='TSM Group')
        self.results_tree.heading('found', text='Found')
        self.results_tree.heading('new', text='New')
        self.results_tree.heading('status', text='Status')
        
        self.results_tree.column('category', width=120)
        self.results_tree.column('group', width=200)
        self.results_tree.column('found', width=60, anchor='center')
        self.results_tree.column('new', width=60, anchor='center')
        self.results_tree.column('status', width=80, anchor='center')
        
        tree_scroll = ModernScrollbar(results_container, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Separator
        sep = ModernFrame(panel, bg=Colors.BORDER_DARK, height=1)
        sep.pack(fill=tk.X, padx=15)
        
        # Log section
        log_header = ModernFrame(panel, bg=Colors.BG_MEDIUM)
        log_header.pack(fill=tk.X, padx=15, pady=5)
        
        ModernLabel(
            log_header, text="Log",
            style='muted', bg=Colors.BG_MEDIUM
        ).pack(side=tk.LEFT)
        
        # Log text
        log_container = ModernFrame(panel, bg=Colors.BG_DARKEST)
        log_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        self.log_text = tk.Text(
            log_container,
            bg=Colors.BG_DARKEST,
            fg=Colors.TEXT_GRAY,
            font=('Consolas', 9),
            relief='flat',
            borderwidth=0,
            height=8,
            state='disabled',
            wrap='word'
        )
        
        log_scroll = ModernScrollbar(log_container, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure log text tags for colors
        self.log_text.tag_configure('info', foreground=Colors.TEXT_GRAY)
        self.log_text.tag_configure('success', foreground=Colors.GREEN)
        self.log_text.tag_configure('warning', foreground=Colors.ORANGE)
        self.log_text.tag_configure('error', foreground=Colors.RED)
        self.log_text.tag_configure('cyan', foreground=Colors.CYAN)
        
        # Progress bar (hidden by default)
        self.progress_frame = ModernFrame(panel, bg=Colors.BG_MEDIUM)
        self.progress_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        style.configure("Custom.Horizontal.TProgressbar",
            background=Colors.CYAN,
            troughcolor=Colors.BG_DARK,
            borderwidth=0,
            thickness=4
        )
        
        self.progress = ttk.Progressbar(
            self.progress_frame, 
            mode='indeterminate',
            style='Custom.Horizontal.TProgressbar'
        )
        self.progress.pack(fill=tk.X)
        self.progress_frame.pack_forget()  # Hide initially
    
    def create_category_list(self):
        """Create category checkboxes grouped by type."""
        groups = {
            "⚔ Weapons": [],
            "🛡 Armor": [],
            "⚗ Consumables": [],
            "📦 Trade Goods": [],
            "📜 Recipes": [],
            "💎 Other": []
        }
        
        for cat_name, (cat_type, _, tsm_group) in self.scraper.ALL_CATEGORIES.items():
            group_map = {
                "weapon": "⚔ Weapons",
                "armor": "🛡 Armor", 
                "consumable": "⚗ Consumables",
                "trade_goods": "📦 Trade Goods",
                "recipe": "📜 Recipes"
            }
            group = group_map.get(cat_type, "💎 Other")
            groups[group].append((cat_name, tsm_group))
        
        for group_name, items in groups.items():
            if not items:
                continue
            
            # Group header
            header = tk.Label(
                self.cat_frame, text=group_name,
                bg=Colors.BG_LIGHT, fg=Colors.CYAN,
                font=('Segoe UI', 9, 'bold'),
                anchor='w'
            )
            header.pack(fill=tk.X, pady=(8, 2), padx=5)
            
            # Items
            for cat_name, _ in sorted(items):
                var = tk.BooleanVar()
                self.category_vars[cat_name] = var
                
                display = cat_name.replace('_', ' ').title()
                cb = ModernCheckbox(self.cat_frame, text=display, variable=var)
                cb.pack(fill=tk.X, padx=15)
    
    def log(self, message, level='info'):
        """Add a log message with color."""
        self.log_text.configure(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] ", 'info')
        self.log_text.insert('end', f"{message}\n", level)
        self.log_text.see('end')
        self.log_text.configure(state='disabled')
    
    def load_tsm_info(self):
        """Load TSM file information."""
        try:
            parser = TSMLuaParser(self.tsm_path)
            if parser.load():
                parser.parse_items()
                parser.parse_groups()
                self.existing_ids = parser.get_existing_item_ids()
                
                self.tsm_info.configure(
                    text=f"✓ {len(parser.items):,} items • {len(parser.groups)} groups",
                    fg=Colors.GREEN
                )
                self.log(f"Loaded: {len(parser.items):,} items, {len(parser.groups)} groups", 'success')
            else:
                self.tsm_info.configure(text="⚠ Could not load file", fg=Colors.RED)
                self.log("Failed to load TSM file", 'error')
        except Exception as e:
            self.tsm_info.configure(text=f"⚠ Error", fg=Colors.RED)
            self.log(f"Error: {e}", 'error')
    
    def browse_tsm_file(self):
        """Browse for TSM file."""
        path = filedialog.askopenfilename(
            title="Select TradeSkillMaster.lua",
            filetypes=[("Lua files", "*.lua"), ("All files", "*.*")],
            initialdir=Path(self.tsm_path).parent
        )
        if path:
            self.tsm_path = path
            self.tsm_path_var.set(Path(path).name)
            self.save_config()
            self.load_tsm_info()
    
    def select_all(self):
        for v in self.category_vars.values():
            v.set(True)
    
    def deselect_all(self):
        for v in self.category_vars.values():
            v.set(False)
    
    def start_scrape(self):
        """Start scraping selected categories."""
        selected = [c for c, v in self.category_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one category.")
            return
        
        self.scrape_btn.configure(state='disabled')
        self.import_btn.configure(state='disabled')
        self.progress_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        self.progress.start(10)
        self.scrape_results.clear()
        
        # Clear results tree
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        threading.Thread(target=self.run_scrape, args=(selected,), daemon=True).start()
    
    def run_scrape(self, categories):
        """Run scraping in background."""
        try:
            # Refresh existing IDs
            parser = TSMLuaParser(self.tsm_path)
            if parser.load():
                parser.parse_items()
                self.existing_ids = parser.get_existing_item_ids()
            
            total_found = 0
            total_new = 0
            
            for cat_name in categories:
                cat_info = self.scraper.ALL_CATEGORIES.get(cat_name)
                if not cat_info:
                    continue
                
                cat_type, subclass, tsm_group = cat_info
                
                self.log(f"Scraping {cat_name}...", 'cyan')
                self.root.after(0, lambda: self.status_label.configure(
                    text=f"Scraping {cat_name}...", fg=Colors.CYAN
                ))
                
                # Build URL
                class_map = {
                    "weapon": self.scraper.CLASS_WEAPON,
                    "armor": self.scraper.CLASS_ARMOR,
                    "consumable": self.scraper.CLASS_CONSUMABLE,
                    "trade_goods": self.scraper.CLASS_TRADE_GOODS,
                    "recipe": self.scraper.CLASS_RECIPE,
                    "gem": self.scraper.CLASS_GEM,
                    "container": self.scraper.CLASS_CONTAINER,
                    "projectile": self.scraper.CLASS_PROJECTILE,
                }
                class_id = class_map.get(cat_type)
                if class_id is None:
                    continue
                
                url = f"{self.scraper.BASE_URL}/?items={class_id}"
                if subclass is not None:
                    url += f".{subclass}"
                
                item_ids = self.scraper.scrape_item_ids_from_page(url)
                new_ids = [i for i in item_ids if i not in self.existing_ids]
                
                self.scrape_results[cat_name] = {
                    'tsm_group': tsm_group,
                    'found': len(item_ids),
                    'new_ids': new_ids
                }
                
                total_found += len(item_ids)
                total_new += len(new_ids)
                
                # Update tree
                display = cat_name.replace('_', ' ').title()
                status = "✓ Ready" if new_ids else "Up to date"
                self.root.after(0, lambda d=display, g=tsm_group, f=len(item_ids), n=len(new_ids), s=status:
                    self.results_tree.insert('', 'end', values=(d, g, f, n, s))
                )
            
            self.log(f"Complete: {total_found:,} found, {total_new:,} new", 'success')
            
            # Update UI
            self.root.after(0, lambda: self.results_summary.configure(
                text=f"{total_found:,} items found • {total_new:,} new"
            ))
            self.root.after(0, lambda: self.status_label.configure(
                text="Scrape complete", fg=Colors.GREEN
            ))
            
            if total_new > 0:
                self.root.after(0, lambda: self.import_btn.configure(state='normal'))
            
        except Exception as e:
            self.log(f"Error: {e}", 'error')
        finally:
            self.root.after(0, lambda: self.scrape_btn.configure(state='normal'))
            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.progress_frame.pack_forget())
    
    def start_import(self):
        """Start importing to TSM."""
        if not self.scrape_results:
            return
        
        total_new = sum(len(d['new_ids']) for d in self.scrape_results.values())
        if total_new == 0:
            messagebox.showinfo("Nothing to Import", "All items are already in TSM!")
            return
        
        if not messagebox.askyesno("Confirm", f"Import {total_new:,} new items to TSM?"):
            return
        
        self.import_btn.configure(state='disabled')
        self.progress_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        self.progress.start(10)
        
        threading.Thread(target=self.run_import, daemon=True).start()
    
    def run_import(self):
        """Run import in background."""
        try:
            writer = TSMLuaWriter(self.tsm_path)
            total_added = 0
            
            for cat_name, data in self.scrape_results.items():
                new_ids = data['new_ids']
                if not new_ids:
                    continue
                
                items_dict = {i: data['tsm_group'] for i in new_ids}
                result = writer.add_items(items_dict, dry_run=False)
                total_added += result['added']
                
                self.log(f"Imported {result['added']} → {data['tsm_group']}", 'success')
            
            self.log(f"✓ Import complete: {total_added:,} items added", 'success')
            self.root.after(0, lambda: self.status_label.configure(
                text=f"Imported {total_added:,} items", fg=Colors.GOLD
            ))
            
            self.root.after(0, self.load_tsm_info)
            messagebox.showinfo("Success", f"Imported {total_added:,} items!\n\nUse /reload in WoW to see changes.")
            
        except Exception as e:
            self.log(f"Error: {e}", 'error')
        finally:
            self.root.after(0, lambda: self.import_btn.configure(state='normal'))
            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.progress_frame.pack_forget())
    
    def open_settings(self):
        """Open the settings/theme editor dialog."""
        ThemeEditorDialog(self.root, self)


# ============================================================================
# Theme Editor Dialog
# ============================================================================

class ThemeEditorDialog:
    """Modal dialog for editing themes with color pickers for every element."""
    
    def __init__(self, parent, app):
        self.app = app
        self.parent = parent
        
        # Create modal dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings - Theme Editor")
        self.dialog.geometry("700x650")
        self.dialog.minsize(600, 500)
        self.dialog.configure(bg=Colors.BG_DARK)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 700) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 650) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        # Track color entries for updates
        self.color_entries: Dict[str, tk.Entry] = {}
        self.color_swatches: Dict[str, tk.Label] = {}
        
        # Build UI
        self.create_widgets()
        
        # Center dialog
        self.dialog.focus_set()
    
    def create_widgets(self):
        """Build the theme editor UI."""
        # Header
        header = ModernFrame(self.dialog, bg=Colors.BG_MEDIUM)
        header.pack(fill=tk.X, padx=10, pady=10)
        
        ModernLabel(
            header, text="⚙ Theme Editor",
            style='header', bg=Colors.BG_MEDIUM
        ).pack(side=tk.LEFT, padx=10)
        
        ModernLabel(
            header, text="Customize every color in the application",
            style='muted', bg=Colors.BG_MEDIUM
        ).pack(side=tk.LEFT, padx=20)
        
        # Theme selection row
        theme_row = ModernFrame(self.dialog, bg=Colors.BG_DARK)
        theme_row.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ModernLabel(
            theme_row, text="Theme:", 
            style='normal', bg=Colors.BG_DARK
        ).pack(side=tk.LEFT, padx=(10, 5))
        
        # Theme dropdown
        self.theme_var = tk.StringVar(value=theme_manager.active_theme_id)
        theme_list = theme_manager.get_theme_list()
        theme_names = {tid: name for tid, name, _ in theme_list}
        
        self.theme_combo = ttk.Combobox(
            theme_row, 
            textvariable=self.theme_var,
            values=[f"{name} ({tid})" for tid, name, _ in theme_list],
            state='readonly',
            width=25
        )
        self.theme_combo.set(f"{theme_names.get(theme_manager.active_theme_id, 'Custom')} ({theme_manager.active_theme_id})")
        self.theme_combo.pack(side=tk.LEFT, padx=5)
        self.theme_combo.bind('<<ComboboxSelected>>', self.on_theme_selected)
        
        # Theme action buttons
        ModernButton(
            theme_row, text="Save As...",
            command=self.save_theme_as
        ).pack(side=tk.LEFT, padx=5)
        
        ModernButton(
            theme_row, text="Reset",
            command=self.reset_theme
        ).pack(side=tk.LEFT, padx=5)
        
        ModernButton(
            theme_row, text="Export",
            command=self.export_theme
        ).pack(side=tk.LEFT, padx=5)
        
        ModernButton(
            theme_row, text="Import",
            command=self.import_theme
        ).pack(side=tk.LEFT, padx=5)
        
        # Main content area with scrollable color editors
        content_frame = ModernFrame(self.dialog, bg=Colors.BG_MEDIUM, border=True)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Canvas for scrolling
        canvas = tk.Canvas(
            content_frame, 
            bg=Colors.BG_MEDIUM,
            highlightthickness=0, 
            borderwidth=0
        )
        scrollbar = ModernScrollbar(content_frame, command=canvas.yview)
        self.colors_frame = ModernFrame(canvas, bg=Colors.BG_MEDIUM)
        
        self.colors_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.colors_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mouse wheel scrolling
        def on_wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_wheel)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create color editors grouped by category
        self.create_color_editors()
        
        # Bottom buttons
        button_frame = ModernFrame(self.dialog, bg=Colors.BG_DARK)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ModernButton(
            button_frame, text="Apply & Restart",
            style='gold',
            command=self.apply_and_close
        ).pack(side=tk.RIGHT, padx=5)
        
        ModernButton(
            button_frame, text="Close",
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        ModernLabel(
            button_frame, 
            text="Note: Restart app to see full theme changes",
            style='muted', bg=Colors.BG_DARK
        ).pack(side=tk.LEFT, padx=10)
    
    def create_color_editors(self):
        """Create color picker for each color property."""
        row = 0
        
        for category, colors in COLOR_CATEGORIES.items():
            # Category header
            header = tk.Label(
                self.colors_frame, 
                text=f"━━ {category} ━━",
                bg=Colors.BG_MEDIUM, 
                fg=Colors.CYAN,
                font=('Segoe UI', 11, 'bold')
            )
            header.grid(row=row, column=0, columnspan=3, sticky='w', pady=(15, 8), padx=10)
            row += 1
            
            for prop_name, display_name in colors:
                # Get current color value
                current_color = theme_manager.get(prop_name)
                
                # Label
                label = tk.Label(
                    self.colors_frame,
                    text=display_name,
                    bg=Colors.BG_MEDIUM,
                    fg=Colors.TEXT_LIGHT,
                    font=('Segoe UI', 10),
                    width=20,
                    anchor='w'
                )
                label.grid(row=row, column=0, sticky='w', padx=(20, 10), pady=3)
                
                # Color entry
                entry = tk.Entry(
                    self.colors_frame,
                    bg=Colors.BG_LIGHT,
                    fg=Colors.TEXT_LIGHT,
                    insertbackground=Colors.CYAN,
                    font=('Consolas', 10),
                    relief='flat',
                    width=10
                )
                entry.insert(0, current_color)
                entry.grid(row=row, column=1, sticky='w', padx=5, pady=3)
                entry.bind('<KeyRelease>', lambda e, n=prop_name: self.on_color_entry_change(n))
                self.color_entries[prop_name] = entry
                
                # Color swatch (clickable)
                swatch = tk.Label(
                    self.colors_frame,
                    bg=current_color,
                    width=4,
                    height=1,
                    relief='solid',
                    borderwidth=1,
                    cursor='hand2'
                )
                swatch.grid(row=row, column=2, sticky='w', padx=5, pady=3)
                swatch.bind('<Button-1>', lambda e, n=prop_name: self.pick_color(n))
                self.color_swatches[prop_name] = swatch
                
                row += 1
    
    def on_color_entry_change(self, prop_name: str):
        """Handle manual color entry changes."""
        entry = self.color_entries[prop_name]
        value = entry.get().strip()
        
        # Validate hex color
        if self.is_valid_hex(value):
            # Update swatch
            self.color_swatches[prop_name].configure(bg=value)
            # Update theme
            theme_manager.set_color(prop_name, value)
    
    def pick_color(self, prop_name: str):
        """Open color picker for a property."""
        current = self.color_entries[prop_name].get()
        
        # Open color chooser
        result = colorchooser.askcolor(
            color=current, 
            title=f"Choose color for {prop_name}",
            parent=self.dialog
        )
        
        if result[1]:  # User selected a color
            hex_color = result[1]
            # Update entry
            entry = self.color_entries[prop_name]
            entry.delete(0, tk.END)
            entry.insert(0, hex_color)
            # Update swatch
            self.color_swatches[prop_name].configure(bg=hex_color)
            # Update theme
            theme_manager.set_color(prop_name, hex_color)
    
    def is_valid_hex(self, value: str) -> bool:
        """Check if value is a valid hex color."""
        if not value.startswith('#'):
            return False
        if len(value) not in (4, 7):  # #RGB or #RRGGBB
            return False
        try:
            int(value[1:], 16)
            return True
        except ValueError:
            return False
    
    def on_theme_selected(self, event):
        """Handle theme selection from dropdown."""
        selection = self.theme_combo.get()
        # Extract theme ID from "Name (id)" format
        if '(' in selection and ')' in selection:
            theme_id = selection.split('(')[-1].rstrip(')')
            theme_manager.set_theme(theme_id)
            # Refresh color entries
            self.refresh_color_entries()
    
    def refresh_color_entries(self):
        """Refresh all color entries from current theme."""
        for prop_name, entry in self.color_entries.items():
            current = theme_manager.get(prop_name)
            entry.delete(0, tk.END)
            entry.insert(0, current)
            self.color_swatches[prop_name].configure(bg=current)
    
    def save_theme_as(self):
        """Save current colors as a new named theme."""
        # Simple dialog for theme name
        name = tk.simpledialog.askstring(
            "Save Theme",
            "Enter a name for your theme:",
            parent=self.dialog
        )
        
        if name:
            theme_id = theme_manager.create_custom_theme(name, theme_manager.active_theme_id)
            theme_manager.set_theme(theme_id)
            # Refresh dropdown
            self.refresh_theme_dropdown()
            messagebox.showinfo("Saved", f"Theme '{name}' saved successfully!")
    
    def reset_theme(self):
        """Reset current theme to default values."""
        if messagebox.askyesno("Reset Theme", "Reset this theme to default values?"):
            theme_manager.reset_theme()
            self.refresh_color_entries()
    
    def export_theme(self):
        """Export current theme to a JSON file."""
        path = filedialog.asksaveasfilename(
            title="Export Theme",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            parent=self.dialog
        )
        if path:
            if theme_manager.export_theme(theme_manager.active_theme_id, Path(path)):
                messagebox.showinfo("Exported", f"Theme exported to {path}")
            else:
                messagebox.showerror("Error", "Failed to export theme")
    
    def import_theme(self):
        """Import a theme from a JSON file."""
        path = filedialog.askopenfilename(
            title="Import Theme",
            filetypes=[("JSON files", "*.json")],
            parent=self.dialog
        )
        if path:
            theme_id = theme_manager.import_theme(Path(path))
            if theme_id:
                theme_manager.set_theme(theme_id)
                self.refresh_theme_dropdown()
                self.refresh_color_entries()
                messagebox.showinfo("Imported", f"Theme imported successfully!")
            else:
                messagebox.showerror("Error", "Failed to import theme")
    
    def refresh_theme_dropdown(self):
        """Refresh the theme dropdown with current themes."""
        theme_list = theme_manager.get_theme_list()
        self.theme_combo['values'] = [f"{name} ({tid})" for tid, name, _ in theme_list]
        current = theme_manager.current
        self.theme_combo.set(f"{current.name} ({theme_manager.active_theme_id})")
    
    def apply_and_close(self):
        """Save theme and close, prompting for restart."""
        theme_manager.save()
        if messagebox.askyesno(
            "Restart Required",
            "Theme saved! Restart the application now to see all changes?"
        ):
            self.dialog.destroy()
            self.parent.destroy()
            # Relaunch
            import subprocess
            subprocess.Popen([sys.executable, __file__])
        else:
            self.dialog.destroy()


# Need to import simpledialog for save theme dialog
try:
    from tkinter import simpledialog
    tk.simpledialog = simpledialog
except ImportError:
    pass


def main():
    root = tk.Tk()
    
    # Try to set window icon (if available)
    try:
        root.iconbitmap(Path(__file__).parent / "icon.ico")
    except:
        pass
    
    app = TSMScraperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
