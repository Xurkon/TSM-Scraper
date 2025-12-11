"""
TSM Item Scraper GUI - Modern Edition

A sleek, modern graphical interface using CustomTkinter.
Features rounded corners, smooth animations, and a techy dark theme.
"""

import sys
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

# Try CustomTkinter first, fall back to tkinter
try:
    import customtkinter as ctk
    from tkinter import messagebox, filedialog, colorchooser
    HAS_CTK = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, colorchooser
    ctk = None
    HAS_CTK = False
    print("CustomTkinter not found. Install with: pip install customtkinter")
    print("Using standard tkinter (less modern look)")

from tsm_scraper.ascension_scraper import AscensionDBScraper
from tsm_scraper.wowhead_scraper import WowheadScraper
from tsm_scraper.lua_parser import TSMLuaParser
from tsm_scraper.lua_writer import TSMLuaWriter
from theme_manager import theme_manager, Theme, COLOR_CATEGORIES

# Load saved theme on startup
theme_manager.load()


# ============================================================================
# Theme Configuration for CustomTkinter
# ============================================================================

def apply_ctk_theme():
    """Apply the current theme to CustomTkinter."""
    if not HAS_CTK:
        return
    
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")


def get_color(name: str) -> str:
    """Get color from theme manager."""
    return theme_manager.get(name)


# ============================================================================
# Constants
# ============================================================================

DEFAULT_TSM_PATH = r"c:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\TradeSkillMaster.lua"
CONFIG_PATH = Path(__file__).parent / "config" / "gui_config.json"


# ============================================================================
# Themed Message Dialogs
# ============================================================================

class ThemedMessageBox(ctk.CTkToplevel if HAS_CTK else object):
    """A themed message box using CustomTkinter."""
    
    def __init__(self, parent, title: str, message: str, icon: str = "info", 
                 buttons: list = None, default_button: str = None):
        super().__init__(parent)
        self.result = None
        
        self.title(title)
        
        # Calculate height based on message length - bigger for more content
        # Base height + extra for each ~50 chars of message
        lines = message.count('\n') + 1
        char_lines = len(message) // 40  # Rough estimate of wrapped lines
        extra_height = max(lines, char_lines) * 18
        height = min(500, max(220, 180 + extra_height))  # Clamp between 220-500
        
        self.geometry(f"420x{height}")
        self.resizable(False, False)
        self.configure(fg_color=get_color('bg_dark'))
        
        # Center on parent
        self.transient(parent)
        self.grab_set()
        
        # Icon and message
        icon_map = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "question": "❓"}
        
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Icon
        ctk.CTkLabel(
            content,
            text=icon_map.get(icon, "ℹ️"),
            font=ctk.CTkFont(size=32),
            text_color=get_color('accent_primary')
        ).pack(pady=(0, 8))
        
        # Message - use scrollable frame for very long messages
        msg_label = ctk.CTkLabel(
            content,
            text=message,
            font=ctk.CTkFont(size=11),
            text_color=get_color('text_light'),
            wraplength=380,
            justify="center"
        )
        msg_label.pack(pady=(0, 15), fill="x")
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack()
        
        if buttons is None:
            buttons = ["OK"]
        
        for btn_text in buttons:
            is_primary = (btn_text == default_button) or (len(buttons) == 1)
            btn = ctk.CTkButton(
                btn_frame,
                text=btn_text,
                width=80,
                height=32,
                corner_radius=6,
                fg_color=get_color('accent_primary_dark') if is_primary else get_color('bg_light'),
                hover_color=get_color('accent_primary') if is_primary else get_color('bg_hover'),
                text_color=get_color('text_white') if is_primary else get_color('text_light'),
                command=lambda t=btn_text: self._on_button(t)
            )
            btn.pack(side="left", padx=5)
        
        # Handle close button
        self.protocol("WM_DELETE_WINDOW", lambda: self._on_button(None))
        
        # Wait for dialog
        self.wait_window()
    
    def _on_button(self, value):
        self.result = value
        self.destroy()


def themed_askquestion(parent, title: str, message: str) -> bool:
    """Show a themed Yes/No dialog. Returns True for Yes, False for No."""
    dialog = ThemedMessageBox(
        parent, title, message, 
        icon="question", 
        buttons=["Yes", "No"],
        default_button="Yes"
    )
    return dialog.result == "Yes"


def themed_showinfo(parent, title: str, message: str):
    """Show a themed info dialog."""
    ThemedMessageBox(parent, title, message, icon="info", buttons=["OK"])


def themed_showerror(parent, title: str, message: str):
    """Show a themed error dialog."""
    ThemedMessageBox(parent, title, message, icon="error", buttons=["OK"])


# ============================================================================
# Main Application (CustomTkinter)
# ============================================================================

class TSMScraperApp(ctk.CTk if HAS_CTK else object):
    """Modern TSM Item Scraper GUI using CustomTkinter."""
    
    def __init__(self):
        super().__init__()
        
        apply_ctk_theme()
        
        self.title("TSM Item Scraper")
        self.geometry("1000x750")
        self.minsize(900, 650)
        
        # Configure colors from theme
        self.configure(fg_color=get_color('bg_darkest'))
        
        # Configuration
        self.config = self.load_config()
        self.tsm_path = self.config.get("tsm_path", DEFAULT_TSM_PATH)
        
        # Components
        self.current_server = "Project Ascension"
        self.current_tsm_format = "classic"  # 'classic' or 'retail'
        self.scraper = AscensionDBScraper()
        self.wowhead_scraper = None  # Lazy init when needed
        self.category_vars: Dict[str, ctk.BooleanVar] = {}
        self.scrape_results: Dict[str, dict] = {}
        self.existing_ids: set = set()
        self.group_buttons_registry: Dict[str, ctk.CTkButton] = {}
        
        # Build UI
        self.create_layout()
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
    
    def bind_mousewheel_to_scrollable(self, scrollable_frame):
        """
        Bind mouse wheel events to a CTkScrollableFrame so users can scroll with their mouse.
        
        CustomTkinter's scrollable frames don't handle mouse wheel by default when
        hovering over child widgets, so we need to manually bind the events.
        """
        def on_mousewheel(event):
            # Windows uses event.delta, Linux uses event.num
            if event.delta:
                scrollable_frame._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:  # Linux scroll up
                scrollable_frame._parent_canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # Linux scroll down
                scrollable_frame._parent_canvas.yview_scroll(1, "units")
        
        def bind_to_widget(widget):
            """Recursively bind mousewheel to widget and all children."""
            widget.bind("<MouseWheel>", on_mousewheel, add="+")  # Windows
            widget.bind("<Button-4>", on_mousewheel, add="+")    # Linux scroll up
            widget.bind("<Button-5>", on_mousewheel, add="+")    # Linux scroll down
            for child in widget.winfo_children():
                bind_to_widget(child)
        
        # Bind to the scrollable frame and all its children
        bind_to_widget(scrollable_frame)
        
        # Also bind to the internal canvas
        if hasattr(scrollable_frame, '_parent_canvas'):
            scrollable_frame._parent_canvas.bind("<MouseWheel>", on_mousewheel, add="+")
            scrollable_frame._parent_canvas.bind("<Button-4>", on_mousewheel, add="+")
            scrollable_frame._parent_canvas.bind("<Button-5>", on_mousewheel, add="+")
    
    def create_layout(self):
        """Create the main UI layout with left and right sidebars."""
        # Configure grid - 3 columns: left sidebar, center, right sidebar
        self.grid_columnconfigure(0, weight=0, minsize=260)  # Left sidebar
        self.grid_columnconfigure(1, weight=1)               # Center panel
        self.grid_columnconfigure(2, weight=0, minsize=260)  # Right sidebar
        self.grid_rowconfigure(1, weight=1)
        
        # Header bar (spans all 3 columns)
        self.create_header()
        
        # Left sidebar - Scraper categories
        self.create_left_sidebar()
        
        # Center - Results/log (smaller)
        self.create_center_panel()
        
        # Right sidebar - TSM Groups
        self.create_right_sidebar()
    
    def create_header(self):
        """Create the sleek header bar."""
        header = ctk.CTkFrame(self, fg_color=get_color('bg_dark'), corner_radius=0)
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(1, weight=1)
        
        # Logo section
        logo_frame = ctk.CTkFrame(header, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # TSM gold text
        tsm_label = ctk.CTkLabel(
            logo_frame,
            text="TSM",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=get_color('accent_secondary')
        )
        tsm_label.pack(side="left")
        
        # Item Scraper cyan text
        scraper_label = ctk.CTkLabel(
            logo_frame,
            text=" Item Scraper",
            font=ctk.CTkFont(family="Segoe UI", size=24),
            text_color=get_color('accent_primary')
        )
        scraper_label.pack(side="left")
        
        # Right section - Settings button + status
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.grid(row=0, column=1, padx=20, pady=15, sticky="e")
        
        # Settings button with gear icon
        self.settings_btn = ctk.CTkButton(
            right_frame,
            text="🎨 Themes",
            width=100,
            height=32,
            corner_radius=8,
            fg_color=get_color('bg_light'),
            hover_color=get_color('bg_hover'),
            text_color=get_color('text_light'),
            command=self.open_settings
        )
        self.settings_btn.pack(side="right", padx=(10, 0))
        
        # Status label
        self.status_label = ctk.CTkLabel(
            right_frame,
            text="● Ready",
            font=ctk.CTkFont(size=12),
            text_color=get_color('color_success')
        )
        self.status_label.pack(side="right", padx=10)
    
    def create_left_sidebar(self):
        """Create the left sidebar with server selection, file info and scrape categories."""
        sidebar = ctk.CTkFrame(
            self,
            width=260,
            fg_color=get_color('bg_medium'),
            corner_radius=0
        )
        sidebar.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(6, weight=1)  # Categories section
        
        # Server Selection Section
        server_section = ctk.CTkFrame(sidebar, fg_color="transparent")
        server_section.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        
        ctk.CTkLabel(
            server_section,
            text="🌐 Database Server",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=get_color('accent_primary')
        ).pack(anchor="w")
        
        # Server dropdown
        self.server_var = ctk.StringVar(value="Project Ascension")
        self.server_combo = ctk.CTkComboBox(
            server_section,
            variable=self.server_var,
            values=[
                "Project Ascension",
                "Turtle WoW",
                "Wowhead (WotLK)",
                "Wowhead (TBC)",
                "Wowhead (Classic Era)",
                "Wowhead (Cata)",
                "Wowhead (MoP Classic)",
                "Wowhead (Retail)",
            ],
            height=28,
            corner_radius=6,
            fg_color=get_color('bg_light'),
            border_color=get_color('border_dark'),
            button_color=get_color('accent_primary_dark'),
            button_hover_color=get_color('accent_primary'),
            dropdown_fg_color=get_color('bg_medium'),
            dropdown_hover_color=get_color('bg_hover'),
            font=ctk.CTkFont(size=10),
            command=self.on_server_changed
        )
        self.server_combo.pack(fill="x", pady=(6, 0))
        
        # TSM Format Selection
        format_section = ctk.CTkFrame(server_section, fg_color="transparent")
        format_section.pack(fill="x", pady=(8, 0))
        
        ctk.CTkLabel(
            format_section,
            text="📝 TSM Format",
            font=ctk.CTkFont(size=11),
            text_color=get_color('text_light')
        ).pack(anchor="w")
        
        self.tsm_format_var = ctk.StringVar(value="WotLK 3.3.5a")
        self.format_combo = ctk.CTkComboBox(
            format_section,
            variable=self.tsm_format_var,
            values=[
                "WotLK 3.3.5a",
                "Retail (Official TSM)",
            ],
            height=26,
            corner_radius=6,
            fg_color=get_color('bg_light'),
            border_color=get_color('border_dark'),
            button_color=get_color('accent_primary_dark'),
            button_hover_color=get_color('accent_primary'),
            dropdown_fg_color=get_color('bg_medium'),
            dropdown_hover_color=get_color('bg_hover'),
            font=ctk.CTkFont(size=10),
            command=self.on_format_changed
        )
        self.format_combo.pack(fill="x", pady=(4, 0))
        
        # Format info label
        self.format_info = ctk.CTkLabel(
            format_section,
            text="item:ID:... format",
            font=ctk.CTkFont(size=9),
            text_color=get_color('text_gray')
        )
        self.format_info.pack(anchor="w", pady=(2, 0))
        
        # Separator
        sep0 = ctk.CTkFrame(sidebar, height=2, fg_color=get_color('border_dark'))
        sep0.grid(row=1, column=0, sticky="ew", padx=12, pady=8)
        
        # TSM File Section
        file_section = ctk.CTkFrame(sidebar, fg_color="transparent")
        file_section.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        
        ctk.CTkLabel(
            file_section,
            text="📁 TSM SavedVariables",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=get_color('accent_primary')
        ).pack(anchor="w")
        
        # File path row
        path_frame = ctk.CTkFrame(file_section, fg_color="transparent")
        path_frame.pack(fill="x", pady=(6, 0))
        
        self.tsm_path_var = ctk.StringVar(value=Path(self.tsm_path).name)
        path_entry = ctk.CTkEntry(
            path_frame,
            textvariable=self.tsm_path_var,
            height=28,
            corner_radius=6,
            fg_color=get_color('bg_light'),
            border_color=get_color('border_dark'),
            text_color=get_color('text_light'),
            font=ctk.CTkFont(size=10)
        )
        path_entry.pack(side="left", fill="x", expand=True)
        
        browse_btn = ctk.CTkButton(
            path_frame, text="...", width=36, height=28,
            corner_radius=6,
            fg_color=get_color('bg_light'),
            hover_color=get_color('bg_hover'),
            command=self.browse_tsm_file
        )
        browse_btn.pack(side="right", padx=(4, 0))
        
        # TSM Info label
        self.tsm_info = ctk.CTkLabel(
            file_section,
            text="Loading...",
            font=ctk.CTkFont(size=10),
            text_color=get_color('text_gray')
        )
        self.tsm_info.pack(anchor="w", pady=(4, 0))
        
        # Separator
        sep1 = ctk.CTkFrame(sidebar, height=2, fg_color=get_color('border_dark'))
        sep1.grid(row=3, column=0, sticky="ew", padx=12, pady=8)
        
        # Categories header
        cat_header = ctk.CTkFrame(sidebar, fg_color="transparent")
        cat_header.grid(row=4, column=0, sticky="ew", padx=12)
        
        ctk.CTkLabel(
            cat_header,
            text="📋 Scrape Categories",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=get_color('accent_primary')
        ).pack(side="left")
        
        # Quick select buttons
        quick_frame = ctk.CTkFrame(cat_header, fg_color="transparent")
        quick_frame.pack(side="right")
        
        ctk.CTkButton(
            quick_frame, text="All", width=32, height=20,
            corner_radius=4, font=ctk.CTkFont(size=9),
            fg_color=get_color('bg_light'),
            hover_color=get_color('bg_hover'),
            command=self.select_all
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            quick_frame, text="None", width=38, height=20,
            corner_radius=4, font=ctk.CTkFont(size=9),
            fg_color=get_color('bg_light'),
            hover_color=get_color('bg_hover'),
            command=self.deselect_all
        ).pack(side="left", padx=2)
        
        # Scrollable category list
        self.cat_scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color=get_color('bg_light'),
            corner_radius=8
        )
        self.cat_scroll.grid(row=6, column=0, sticky="nsew", padx=12, pady=(8, 0))
        
        self.create_category_list()
        
        # Enable mouse wheel scrolling in the category list
        self.bind_mousewheel_to_scrollable(self.cat_scroll)
        
        # Scrape button at bottom
        action_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        action_frame.grid(row=7, column=0, sticky="ew", padx=12, pady=12)
        
        self.scrape_btn = ctk.CTkButton(
            action_frame,
            text="🔍 Scrape Items",
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=get_color('accent_primary_dark'),
            hover_color=get_color('accent_primary'),
            command=self.start_scrape
        )
        self.scrape_btn.pack(fill="x")
    
    def create_center_panel(self):
        """Create the compact center panel with results and log."""
        center = ctk.CTkFrame(self, fg_color=get_color('bg_medium'), corner_radius=0)
        center.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(1, weight=1)
        center.grid_rowconfigure(3, weight=0)
        
        # Results header
        header = ctk.CTkFrame(center, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(
            header,
            text="📊 Scrape Results",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=get_color('accent_primary')
        ).pack(side="left")
        
        self.results_summary = ctk.CTkLabel(
            header,
            text="Select categories and click Scrape",
            font=ctk.CTkFont(size=10),
            text_color=get_color('text_gray')
        )
        self.results_summary.pack(side="right")
        
        # Results display - scrollable frame with checkboxes
        self.results_scroll = ctk.CTkScrollableFrame(
            center,
            corner_radius=6,
            fg_color=get_color('bg_light'),
            height=150
        )
        self.results_scroll.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 8))
        
        # Initialize results checkbox storage
        self.results_checkboxes: Dict[str, ctk.BooleanVar] = {}
        
        # Enable mouse wheel scrolling in results list
        self.bind_mousewheel_to_scrollable(self.results_scroll)
        
        # Log header
        log_header = ctk.CTkFrame(center, fg_color="transparent")
        log_header.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 3))
        
        ctk.CTkLabel(
            log_header,
            text="📜 Log",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=get_color('text_gray')
        ).pack(side="left")
        
        # Log text (compact)
        self.log_text = ctk.CTkTextbox(
            center,
            height=80,
            corner_radius=6,
            fg_color=get_color('bg_darkest'),
            text_color=get_color('text_gray'),
            font=ctk.CTkFont(family="Consolas", size=9)
        )
        self.log_text.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.log_text.configure(state="disabled")
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(
            center,
            height=4,
            corner_radius=2,
            fg_color=get_color('bg_dark'),
            progress_color=get_color('accent_primary')
        )
        self.progress.set(0)
    
    def create_right_sidebar(self):
        """Create the right sidebar with TSM groups for import target selection."""
        sidebar = ctk.CTkFrame(
            self,
            width=260,
            fg_color=get_color('bg_medium'),
            corner_radius=0
        )
        sidebar.grid(row=1, column=2, sticky="nsew", padx=0, pady=0)
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(2, weight=1)  # Groups list
        
        # Header
        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        
        ctk.CTkLabel(
            header,
            text="📁 Import Target Group",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=get_color('accent_primary')
        ).pack(side="left")
        
        self.groups_count_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=9),
            text_color=get_color('text_gray')
        )
        self.groups_count_label.pack(side="right")
        
        # Instructions
        ctk.CTkLabel(
            sidebar,
            text="Click a group to select it as import target:",
            font=ctk.CTkFont(size=9),
            text_color=get_color('text_gray')
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 4))
        
        # Groups list (scrollable, clickable)
        self.groups_scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color=get_color('bg_light'),
            corner_radius=8
        )
        self.groups_scroll.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        
        # Enable mouse wheel scrolling in groups list
        self.bind_mousewheel_to_scrollable(self.groups_scroll)
        
        # Selected group display
        selected_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        selected_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        
        ctk.CTkLabel(
            selected_frame,
            text="Selected:",
            font=ctk.CTkFont(size=10),
            text_color=get_color('text_gray')
        ).pack(anchor="w")
        
        self.selected_group_var = ctk.StringVar(value="(Use default from scraper)")
        self.selected_group_label = ctk.CTkLabel(
            selected_frame,
            textvariable=self.selected_group_var,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=get_color('accent_secondary'),
            wraplength=230
        )
        self.selected_group_label.pack(anchor="w")
        
        # Import button at bottom
        action_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        action_frame.grid(row=4, column=0, sticky="ew", padx=12, pady=12)
        
        self.import_btn = ctk.CTkButton(
            action_frame,
            text="📥 Import to TSM",
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=get_color('accent_secondary_dark'),
            hover_color=get_color('accent_secondary'),
            text_color=get_color('bg_dark'),
            command=self.start_import,
            state="disabled"
        )
        self.import_btn.pack(fill="x")
    
    def refresh_groups_panel(self):
        """Refresh the TSM groups display in the right sidebar."""
        # Clear existing widgets
        for widget in self.groups_scroll.winfo_children():
            widget.destroy()
        
        # Reset group button registry
        self.group_buttons_registry = {}
        
        try:
            parser = TSMLuaParser(self.tsm_path)
            if not parser.load():
                ctk.CTkLabel(
                    self.groups_scroll,
                    text="Load TSM file first",
                    font=ctk.CTkFont(size=10),
                    text_color=get_color('text_gray')
                ).pack(anchor="w", padx=5, pady=2)
                return
            
            parser.parse_items()
            parser.parse_groups()
            
            # Get hierarchy
            hierarchy = parser.get_group_hierarchy()
            
            # Count items per group
            group_item_counts = {}
            for group in parser.groups:
                count = len(parser.get_items_by_group(group))
                group_item_counts[group] = count
            
            # Display groups hierarchically as clickable buttons
            def add_group_button(group_path: str, indent: int = 0):
                parts = group_path.split('`')
                display_name = parts[-1] if parts else group_path
                item_count = group_item_counts.get(group_path, 0)
                count_str = f" ({item_count})" if item_count > 0 else ""
                
                prefix = "  " * indent + ("└ " if indent > 0 else "")
                text = f"{prefix}{display_name}{count_str}"
                
                btn = ctk.CTkButton(
                    self.groups_scroll,
                    text=text,
                    font=ctk.CTkFont(size=9),
                    text_color=get_color('text_light') if item_count > 0 else get_color('text_gray'),
                    fg_color="transparent",
                    hover_color=get_color('bg_hover'),
                    anchor="w",
                    height=22,
                    command=lambda g=group_path: self.select_import_group(g)
                )
                btn.pack(anchor="w", fill="x", padx=2, pady=1)
                
                # Register button for highlighting
                self.group_buttons_registry[group_path] = btn
                
                # Add children
                children = hierarchy.get(group_path, [])
                for child in sorted(children):
                    if child != group_path:
                        add_group_button(child, indent + 1)
            
            # Start with root groups
            root_groups = sorted(hierarchy.get('', []))
            for root in root_groups:
                add_group_button(root, 0)
            
            total_groups = len(parser.groups)
            self.groups_count_label.configure(text=f"{total_groups} groups")
            
        except Exception as e:
            ctk.CTkLabel(
                self.groups_scroll,
                text=f"Error: {e}",
                font=ctk.CTkFont(size=10),
                text_color=get_color('color_error')
            ).pack(anchor="w", padx=5, pady=2)
    
    def select_import_group(self, group_path: str):
        """Select a TSM group as the import target with visual highlighting."""
        # Update the selected group variable
        self.selected_group_var.set(group_path)
        self.log(f"Import target set to: {group_path}", 'cyan')
        
        # Highlight the selected button, unhighlight others
        self.highlight_group_button(group_path)
    
    def highlight_group_button(self, group_path: str):
        """Highlight the selected group button and unhighlight others."""
        if not hasattr(self, 'group_buttons_registry'):
            return
        
        for path, btn in self.group_buttons_registry.items():
            try:
                if path == group_path:
                    # Highlight selected
                    btn.configure(
                        fg_color=get_color('accent_primary_dark'),
                        text_color=get_color('text_white')
                    )
                    # Scroll to show this button
                    self.scroll_to_group_button(btn)
                else:
                    # Reset to normal
                    btn.configure(
                        fg_color="transparent",
                        text_color=get_color('text_light')
                    )
            except:
                pass  # Button may have been destroyed
    
    def scroll_to_group_button(self, button):
        """Scroll the groups panel to show the specified button."""
        try:
            # Find button index in registry
            buttons_list = list(self.group_buttons_registry.values())
            if button not in buttons_list:
                return
            
            btn_index = buttons_list.index(button)
            total_buttons = len(buttons_list)
            
            if total_buttons <= 1:
                return
            
            # Calculate approximate scroll position
            # We want the button to appear in the upper third of the view
            position = max(0, (btn_index - 2)) / max(1, total_buttons - 1)
            position = min(1.0, position)
            
            # Try to scroll using the internal canvas
            self.update_idletasks()
            
            # CTkScrollableFrame internal structure
            if hasattr(self.groups_scroll, '_parent_canvas'):
                self.groups_scroll._parent_canvas.yview_moveto(position)
            elif hasattr(self.groups_scroll, 'yview_moveto'):
                self.groups_scroll.yview_moveto(position)
            else:
                # Look for canvas child
                for widget in self.groups_scroll.winfo_children():
                    if hasattr(widget, 'yview_moveto'):
                        widget.yview_moveto(position)
                        break
        except Exception:
            pass  # Scrolling is optional
    
    def auto_select_scrape_group(self):
        """Auto-select the most relevant TSM group based on scrape results."""
        if not self.scrape_results:
            return
        
        # Count which groups have items (use found count, not just new)
        group_counts = {}
        for cat_name, data in self.scrape_results.items():
            tsm_group = data.get('tsm_group', '')
            found_count = data.get('found', 0)
            if found_count > 0 and tsm_group:
                group_counts[tsm_group] = group_counts.get(tsm_group, 0) + found_count
        
        if not group_counts:
            return
        
        # Find the group with most items
        best_group = max(group_counts, key=group_counts.get)
        
        # Find if there's a common parent group
        # e.g., if we scraped multiple weapon types, select "Weapons" parent
        unique_groups = list(group_counts.keys())
        if len(unique_groups) > 1:
            # Check for common parent
            parents = [g.rsplit('`', 1)[0] if '`' in g else '' for g in unique_groups]
            common_parent = parents[0] if len(set(parents)) == 1 and parents[0] else None
            if common_parent and common_parent in self.group_buttons_registry:
                best_group = common_parent
        
        # Select and highlight the group (if it exists in the registry)
        if best_group in self.group_buttons_registry:
            self.select_import_group(best_group)
            self.log(f"Auto-selected group: {best_group}", 'cyan')
        else:
            # Group doesn't exist yet, just set it as selected (will be created on import)
            self.selected_group_var.set(best_group)
            self.log(f"Target group (will be created): {best_group}", 'cyan')
    
    def get_user_groups_list(self) -> list:
        """Get list of user's existing TSM groups for dropdown selection."""
        try:
            parser = TSMLuaParser(self.tsm_path)
            if not parser.load():
                return []
            parser.parse_groups()
            return sorted(parser.groups)
        except Exception:
            return []
    
    def on_server_changed(self, selection: str):
        """Handle server/database selection change."""
        server_info = {
            "Project Ascension": {"url": "db.ascension.gg", "type": "ascension"},
            "Turtle WoW": {"url": "database.turtle-wow.org", "type": "turtlewow"},
            "Wowhead (WotLK)": {"url": "wowhead.com/wotlk", "type": "wowhead", "version": "wotlk"},
            "Wowhead (TBC)": {"url": "wowhead.com/tbc", "type": "wowhead", "version": "tbc"},
            "Wowhead (Classic Era)": {"url": "classic.wowhead.com", "type": "wowhead", "version": "classic"},
            "Wowhead (Cata)": {"url": "wowhead.com/cata", "type": "wowhead", "version": "cata"},
            "Wowhead (MoP Classic)": {"url": "wowhead.com/mop-classic", "type": "wowhead", "version": "mop"},
            "Wowhead (Retail)": {"url": "www.wowhead.com", "type": "wowhead", "version": "retail"},
        }
        
        info = server_info.get(selection, {"url": "Unknown", "type": "ascension"})
        self.log(f"Server changed to: {selection} ({info['url']})", 'cyan')
        
        # Store current selection
        self.current_server = selection
        
        # Switch scraper based on selection
        if info['type'] == 'ascension':
            # Use Ascension scraper
            self.scraper = AscensionDBScraper()
            self.log("Using Ascension DB scraper", 'cyan')
        elif info['type'] == 'turtlewow':
            # Use Turtle WoW scraper (similar to Ascension)
            from tsm_scraper.turtlewow_scraper import TurtleWoWScraper
            self.scraper = TurtleWoWScraper()
            self.log("Using Turtle WoW DB scraper (TSM backport coming soon)", 'cyan')
        else:
            # Use Wowhead scraper with appropriate version
            version = info.get('version', 'wotlk')
            self.wowhead_scraper = WowheadScraper(game_version=version)
            self.log(f"Using Wowhead scraper ({version})", 'cyan')
        
        # Update categories for the selected server
        self.update_categories_for_server()
    
    def update_categories_for_server(self):
        """Update available categories based on selected server."""
        # For now, keep the same categories - they're similar across versions
        # In the future, we could load different category sets per server
        pass
    
    def on_format_changed(self, selection: str):
        """Handle TSM format selection change."""
        format_info = {
            "WotLK 3.3.5a": {
                "format": "classic",
                "item_pattern": "item:ID:...",
                "description": "item:ID:... format"
            },
            "Retail (Official TSM)": {
                "format": "retail", 
                "item_pattern": "i:ID",
                "description": "i:ID format"
            },
        }
        
        info = format_info.get(selection, format_info["WotLK 3.3.5a"])
        self.current_tsm_format = info['format']
        
        # Update format info label
        self.format_info.configure(text=info['description'])
        self.log(f"TSM format set to: {selection} ({info['item_pattern']})", 'cyan')
    
    def create_category_list(self):
        """Create category checkboxes grouped by type with collapsible sections."""
        groups = {
            "⚔ Weapons": [],
            "👕 Cloth": [],
            "🦎 Leather": [],
            "⛓ Mail": [],
            "🛡 Plate": [],
            "🔰 Other Armor": [],
            "⚗ Consumables": [],
            "📦 Trade Goods": [],
            "📜 Recipes": [],
            "💎 Other": []
        }
        
        for cat_name, (cat_type, subclass, tsm_group) in self.scraper.ALL_CATEGORIES.items():
            if cat_type == "weapon":
                groups["⚔ Weapons"].append((cat_name, tsm_group))
            elif cat_type == "armor":
                # Separate armor by type
                if cat_name.startswith("cloth_"):
                    groups["👕 Cloth"].append((cat_name, tsm_group))
                elif cat_name.startswith("leather_"):
                    groups["🦎 Leather"].append((cat_name, tsm_group))
                elif cat_name.startswith("mail_"):
                    groups["⛓ Mail"].append((cat_name, tsm_group))
                elif cat_name.startswith("plate_"):
                    groups["🛡 Plate"].append((cat_name, tsm_group))
                else:
                    groups["🔰 Other Armor"].append((cat_name, tsm_group))
            elif cat_type == "consumable":
                groups["⚗ Consumables"].append((cat_name, tsm_group))
            elif cat_type == "trade_goods":
                groups["📦 Trade Goods"].append((cat_name, tsm_group))
            elif cat_type == "recipe":
                groups["📜 Recipes"].append((cat_name, tsm_group))
            else:
                groups["💎 Other"].append((cat_name, tsm_group))
        
        # Store group frames for collapse/expand
        self.group_frames: Dict[str, ctk.CTkFrame] = {}
        self.group_expanded: Dict[str, bool] = {}
        self.group_buttons: Dict[str, ctk.CTkButton] = {}
        
        for group_name, items in groups.items():
            if not items:
                continue
            
            # Expand/collapse indicator + group name
            self.group_expanded[group_name] = True  # Start expanded
            
            header_btn = ctk.CTkButton(
                self.cat_scroll,
                text=f"▼ {group_name} ({len(items)})",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=get_color('accent_primary'),
                fg_color="transparent",
                hover_color=get_color('bg_hover'),
                anchor="w",
                height=28,
                command=lambda g=group_name: self.toggle_group(g)
            )
            header_btn.pack(fill="x", pady=(8, 2), padx=5)
            self.group_buttons[group_name] = header_btn
            
            # Items container (collapsible)
            items_frame = ctk.CTkFrame(self.cat_scroll, fg_color="transparent")
            items_frame.pack(fill="x", padx=5)
            self.group_frames[group_name] = items_frame
            
            # Create checkboxes for this group
            for cat_name, _ in sorted(items):
                var = ctk.BooleanVar()
                self.category_vars[cat_name] = var
                
                display = cat_name.replace('_', ' ').title()
                cb = ctk.CTkCheckBox(
                    items_frame,
                    text=display,
                    variable=var,
                    font=ctk.CTkFont(size=11),
                    fg_color=get_color('accent_primary'),
                    hover_color=get_color('accent_primary_dark'),
                    text_color=get_color('text_light'),
                    corner_radius=4,
                    height=24
                )
                cb.pack(anchor="w", padx=12, pady=1)
    
    def toggle_group(self, group_name: str):
        """Toggle the collapse/expand state of a category group."""
        is_expanded = self.group_expanded.get(group_name, True)
        
        if is_expanded:
            # Collapse - hide the items frame
            self.group_frames[group_name].pack_forget()
            # Update button text to show collapsed state
            item_count = len([w for w in self.group_frames[group_name].winfo_children()])
            self.group_buttons[group_name].configure(text=f"▶ {group_name} ({item_count})")
        else:
            # Expand - show the items frame after the header button
            btn = self.group_buttons[group_name]
            self.group_frames[group_name].pack(fill="x", padx=5, after=btn)
            item_count = len([w for w in self.group_frames[group_name].winfo_children()])
            self.group_buttons[group_name].configure(text=f"▼ {group_name} ({item_count})")
        
        self.group_expanded[group_name] = not is_expanded
    
    def log(self, message: str, level: str = 'info'):
        """Add a log message."""
        self.log_text.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        color_map = {
            'info': get_color('text_gray'),
            'success': get_color('color_success'),
            'warning': get_color('color_warning'),
            'error': get_color('color_error'),
            'cyan': get_color('accent_primary')
        }
        
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
    
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
                    text_color=get_color('color_success')
                )
                self.log(f"Loaded: {len(parser.items):,} items, {len(parser.groups)} groups", 'success')
                
                # Refresh the groups panel in sidebar
                self.refresh_groups_panel()
            else:
                self.tsm_info.configure(
                    text="⚠ Could not load file",
                    text_color=get_color('color_error')
                )
                self.log("Failed to load TSM file", 'error')
        except Exception as e:
            self.tsm_info.configure(
                text="⚠ Error",
                text_color=get_color('color_error')
            )
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
        
        self.scrape_btn.configure(state="disabled")
        self.import_btn.configure(state="disabled")
        self.scrape_results.clear()
        
        # Clear results
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
        self.results_checkboxes.clear()
        ctk.CTkLabel(
            self.results_scroll,
            text="Scraping...",
            font=ctk.CTkFont(size=10),
            text_color=get_color('text_gray')
        ).pack(anchor="w", padx=10, pady=10)
        
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
            results_lines = []
            
            for cat_name in categories:
                cat_info = self.scraper.ALL_CATEGORIES.get(cat_name)
                if not cat_info:
                    continue
                
                cat_type, subclass, tsm_group = cat_info
                
                self.log(f"Scraping {cat_name}...", 'cyan')
                self.after(0, lambda c=cat_name: self.status_label.configure(
                    text=f"● Scraping {c}...",
                    text_color=get_color('accent_primary')
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
                
                # Format result line
                display = cat_name.replace('_', ' ').title()
                status = "✓" if new_ids else "—"
                results_lines.append(f"{status} {display:<25} Found: {len(item_ids):>5}   New: {len(new_ids):>5}   → {tsm_group}")
            
            # Update results display with checkboxes
            self.after(0, self.update_results_with_checkboxes)
            
            self.log(f"Complete: {total_found:,} found, {total_new:,} new", 'success')
            
            self.after(0, lambda: self.results_summary.configure(
                text=f"{total_found:,} items found • {total_new:,} new"
            ))
            self.after(0, lambda: self.status_label.configure(
                text="● Scrape complete",
                text_color=get_color('color_success')
            ))
            
            if total_new > 0:
                self.after(0, lambda: self.import_btn.configure(state="normal"))
            
            # Always auto-select the most relevant group based on what was scraped
            self.after(200, self.auto_select_scrape_group)
            
        except Exception as e:
            self.log(f"Error: {e}", 'error')
        finally:
            self.after(0, lambda: self.scrape_btn.configure(state="normal"))
    
    def update_results_display(self, lines):
        """Update the results text display."""
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        
        header = f"{'Status':<7} {'Category':<25} {'Found':>10} {'New':>8}   TSM Group\n"
        header += "─" * 90 + "\n"
        self.results_text.insert("end", header)
        
        for line in lines:
            self.results_text.insert("end", line + "\n")
        
        self.results_text.configure(state="disabled")
    
    def update_results_with_checkboxes(self):
        """Update the results display with checkboxes for each scraped category."""
        # Clear existing checkboxes
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
        self.results_checkboxes.clear()
        
        if not self.scrape_results:
            ctk.CTkLabel(
                self.results_scroll,
                text="No results yet. Select categories and click Scrape.",
                font=ctk.CTkFont(size=10),
                text_color=get_color('text_gray')
            ).pack(anchor="w", padx=10, pady=10)
            return
        
        # Header row
        header = ctk.CTkFrame(self.results_scroll, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=(5, 2))
        
        ctk.CTkLabel(header, text="✓", width=30, font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=get_color('text_gray')).pack(side="left")
        ctk.CTkLabel(header, text="Category", width=100, anchor="w", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=get_color('text_gray')).pack(side="left", padx=(5, 0))
        ctk.CTkLabel(header, text="Found", width=45, font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=get_color('text_gray')).pack(side="left")
        ctk.CTkLabel(header, text="New", width=45, font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=get_color('text_gray')).pack(side="left")
        ctk.CTkLabel(header, text="TSM Group", anchor="w", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=get_color('text_gray')).pack(side="left", fill="x", expand=True)
        
        # Create a row for each category
        for cat_name, data in self.scrape_results.items():
            found = data.get('found', 0)
            new_count = len(data.get('new_ids', []))
            tsm_group = data.get('tsm_group', '')
            
            row = ctk.CTkFrame(self.results_scroll, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=1)
            
            # Checkbox (checked by default if there are new items)
            var = ctk.BooleanVar(value=new_count > 0)
            self.results_checkboxes[cat_name] = var
            
            cb = ctk.CTkCheckBox(
                row, text="", variable=var, width=30,
                corner_radius=3, border_width=2,
                fg_color=get_color('accent_primary'),
                hover_color=get_color('accent_primary_dark'),
                border_color=get_color('border_light'),
                checkmark_color=get_color('text_white')
            )
            cb.pack(side="left")
            
            # Category name
            display = cat_name.replace('_', ' ').title()
            ctk.CTkLabel(row, text=display, width=100, anchor="w",
                        font=ctk.CTkFont(size=9),
                        text_color=get_color('text_light')).pack(side="left", padx=(5, 0))
            
            # Found count
            ctk.CTkLabel(row, text=str(found), width=45,
                        font=ctk.CTkFont(size=9),
                        text_color=get_color('text_light')).pack(side="left")
            
            # New count (highlighted if > 0)
            new_color = get_color('color_success') if new_count > 0 else get_color('text_gray')
            ctk.CTkLabel(row, text=str(new_count), width=45,
                        font=ctk.CTkFont(size=9, weight="bold" if new_count > 0 else "normal"),
                        text_color=new_color).pack(side="left")
            
            # TSM Group
            group_display = tsm_group.split('`')[-1] if tsm_group else ""
            ctk.CTkLabel(row, text=f"→ {group_display}", anchor="w",
                        font=ctk.CTkFont(size=8),
                        text_color=get_color('accent_secondary')).pack(side="left", fill="x", expand=True)
    
    def get_selected_import_categories(self) -> dict:
        """Get only the categories that are checked for import."""
        selected = {}
        for cat_name, var in self.results_checkboxes.items():
            if var.get() and cat_name in self.scrape_results:
                selected[cat_name] = self.scrape_results[cat_name]
        return selected
    
    def start_import(self):
        """Start importing to TSM."""
        if not self.scrape_results:
            themed_showinfo(
                self, 
                "No Scrape Results", 
                "Please scrape items first before importing.\n\n"
                "Select categories on the left and click 'Scrape Items'."
            )
            return
        
        # Get only checked categories
        selected_results = self.get_selected_import_categories()
        if not selected_results:
            themed_showinfo(self, "No Categories Selected", "Please check at least one category to import.")
            return
        
        total_new = sum(len(d['new_ids']) for d in selected_results.values())
        if total_new == 0:
            themed_showinfo(self, "Nothing to Import", "All items in selected categories are already in TSM!")
            return
        
        # Get selected target group
        selected_group = self.selected_group_var.get()
        
        # Check if selected results have multiple different target groups
        unique_groups = set(d.get('tsm_group', '') for d in selected_results.values())
        has_multiple_groups = len(unique_groups) > 1
        
        if selected_group == "(Use default from scraper)" or has_multiple_groups:
            # Multiple categories going to their respective groups
            group_list = "\n".join([f"• {cat.replace('_', ' ').title()} → {d['tsm_group'].split('`')[-1]}" 
                                   for cat, d in list(selected_results.items())[:5]])
            if len(selected_results) > 5:
                group_list += f"\n... and {len(selected_results) - 5} more"
            
            if not themed_askquestion(
                self,
                "Confirm Import", 
                f"Import {total_new:,} new items to their respective groups?\n\n{group_list}\n\nThis will update your TradeSkillMaster.lua file."
            ):
                return
            # Force use of default groups
            self.selected_group_var.set("(Use default from scraper)")
        else:
            # Single target group selected
            if not themed_askquestion(
                self,
                "Confirm Import", 
                f"Import {total_new:,} new items to '{selected_group}'?\n\nThis will update your TradeSkillMaster.lua file."
            ):
                return
        
        self.import_btn.configure(state="disabled")
        threading.Thread(target=self.run_import, daemon=True).start()
    
    def run_import(self):
        """Run import in background."""
        try:
            writer = TSMLuaWriter(self.tsm_path)
            total_added = 0
            
            # Get selected target group (if user picked one)
            selected_group = self.selected_group_var.get()
            use_custom_group = selected_group != "(Use default from scraper)"
            
            # Only import checked categories
            selected_results = self.get_selected_import_categories()
            
            for cat_name, data in selected_results.items():
                new_ids = data['new_ids']
                if not new_ids:
                    continue
                
                # Use selected group or default category group
                target_group = selected_group if use_custom_group else data['tsm_group']
                items_dict = {i: target_group for i in new_ids}
                result = writer.add_items(items_dict, dry_run=False)
                total_added += result['added']
                
                self.log(f"Imported {result['added']} → {target_group}", 'success')
            
            self.log(f"✓ Import complete: {total_added:,} items added", 'success')
            self.after(0, lambda: self.status_label.configure(
                text=f"● Imported {total_added:,} items",
                text_color=get_color('accent_secondary')
            ))
            
            self.after(0, self.load_tsm_info)
            self.after(0, lambda: themed_showinfo(self, "Success", f"Imported {total_added:,} items!\n\nIf WoW is running, restart it to see changes."))
            
        except Exception as e:
            self.log(f"Error: {e}", 'error')
        finally:
            self.after(0, lambda: self.import_btn.configure(state="normal"))
    
    def open_settings(self):
        """Open the settings/theme editor dialog."""
        ThemeEditorDialog(self)


# ============================================================================
# Theme Editor Dialog
# ============================================================================

class ThemeEditorDialog(ctk.CTkToplevel if HAS_CTK else object):
    """Modern theme editor dialog with color pickers for every element."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        
        self.title("🎨 Theme Editor")
        self.geometry("750x700")
        self.minsize(650, 550)
        self.configure(fg_color=get_color('bg_dark'))
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 750) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 700) // 2
        self.geometry(f"+{x}+{y}")
        
        # Track color entries
        self.color_entries: Dict[str, ctk.CTkEntry] = {}
        self.color_swatches: Dict[str, ctk.CTkButton] = {}
        
        # Build UI
        self.create_widgets()
        self.focus_set()
    
    def create_widgets(self):
        """Build the theme editor UI."""
        # Header
        header = ctk.CTkFrame(self, fg_color=get_color('bg_medium'), corner_radius=8)
        header.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(
            header,
            text="⚙ Theme Editor",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=get_color('accent_primary')
        ).pack(side="left", padx=15, pady=12)
        
        ctk.CTkLabel(
            header,
            text="Customize every color in the application",
            font=ctk.CTkFont(size=12),
            text_color=get_color('text_gray')
        ).pack(side="left", padx=10)
        
        # Theme selection row
        theme_row = ctk.CTkFrame(self, fg_color="transparent")
        theme_row.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(
            theme_row,
            text="Theme:",
            font=ctk.CTkFont(size=13),
            text_color=get_color('text_light')
        ).pack(side="left", padx=(5, 10))
        
        # Theme dropdown
        theme_list = theme_manager.get_theme_list()
        theme_names = [f"{name}" for _, name, _ in theme_list]
        
        self.theme_var = ctk.StringVar(value=theme_manager.current.name)
        self.theme_combo = ctk.CTkComboBox(
            theme_row,
            values=theme_names,
            variable=self.theme_var,
            width=200,
            height=32,
            corner_radius=6,
            fg_color=get_color('bg_light'),
            button_color=get_color('bg_hover'),
            dropdown_fg_color=get_color('bg_medium'),
            command=self.on_theme_selected
        )
        self.theme_combo.pack(side="left", padx=5)
        
        # Theme action buttons
        btn_style = {
            "height": 32,
            "corner_radius": 6,
            "fg_color": get_color('bg_light'),
            "hover_color": get_color('bg_hover'),
            "text_color": get_color('text_light'),
            "font": ctk.CTkFont(size=12)
        }
        
        ctk.CTkButton(
            theme_row, text="💾 Save As...",
            width=100, command=self.save_theme_as, **btn_style
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            theme_row, text="🔄 Reset",
            width=80, command=self.reset_theme, **btn_style
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            theme_row, text="📤 Export",
            width=80, command=self.export_theme, **btn_style
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            theme_row, text="📥 Import",
            width=80, command=self.import_theme, **btn_style
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            theme_row, text="🎲 Random",
            width=80, command=self.randomize_theme, **btn_style
        ).pack(side="left", padx=5)
        
        # Scrollable color editor
        self.colors_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=get_color('bg_medium'),
            corner_radius=8
        )
        self.colors_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        
        self.create_color_editors()
        self.create_font_editors()
        
        # Bottom buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(
            button_frame,
            text="💡 Restart app to apply all theme changes",
            font=ctk.CTkFont(size=11),
            text_color=get_color('text_gray')
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="Close",
            width=100,
            height=36,
            corner_radius=8,
            fg_color=get_color('bg_light'),
            hover_color=get_color('bg_hover'),
            command=self.destroy
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="✨ Apply & Restart",
            width=140,
            height=36,
            corner_radius=8,
            fg_color=get_color('accent_secondary_dark'),
            hover_color=get_color('accent_secondary'),
            text_color=get_color('bg_dark'),
            font=ctk.CTkFont(weight="bold"),
            command=self.apply_and_close
        ).pack(side="right", padx=5)
    
    def create_color_editors(self):
        """Create color pickers for each color property."""
        for category, colors in COLOR_CATEGORIES.items():
            # Category header
            header = ctk.CTkLabel(
                self.colors_scroll,
                text=f"━━ {category} ━━",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=get_color('accent_primary')
            )
            header.pack(anchor="w", pady=(15, 8), padx=10)
            
            for prop_name, display_name in colors:
                current_color = theme_manager.get(prop_name)
                
                row = ctk.CTkFrame(self.colors_scroll, fg_color="transparent")
                row.pack(fill="x", padx=15, pady=3)
                
                # Label
                ctk.CTkLabel(
                    row,
                    text=display_name,
                    width=180,
                    anchor="w",
                    font=ctk.CTkFont(size=12),
                    text_color=get_color('text_light')
                ).pack(side="left")
                
                # Color entry
                entry = ctk.CTkEntry(
                    row,
                    width=100,
                    height=28,
                    corner_radius=4,
                    fg_color=get_color('bg_light'),
                    border_color=get_color('border_dark'),
                    text_color=get_color('text_light'),
                    font=ctk.CTkFont(family="Consolas", size=11)
                )
                entry.insert(0, current_color)
                entry.pack(side="left", padx=5)
                entry.bind('<KeyRelease>', lambda e, n=prop_name: self.on_color_entry_change(n))
                self.color_entries[prop_name] = entry
                
                # Color swatch button (clickable)
                swatch = ctk.CTkButton(
                    row,
                    text="",
                    width=40,
                    height=28,
                    corner_radius=4,
                    fg_color=current_color,
                    hover_color=current_color,
                    border_width=2,
                    border_color=get_color('border_light'),
                    command=lambda n=prop_name: self.pick_color(n)
                )
                swatch.pack(side="left", padx=5)
                self.color_swatches[prop_name] = swatch
    
    def create_font_editors(self):
        """Create font size sliders for different UI elements."""
        # Font size categories
        font_sizes = [
            ("font_size_header", "Header Text", 10, 24),
            ("font_size_label", "Labels", 8, 20),
            ("font_size_body", "Body Text", 8, 18),
            ("font_size_small", "Small Text", 6, 16),
            ("font_size_tiny", "Tiny Text (Groups)", 6, 14),
        ]
        
        # Section header
        header = ctk.CTkLabel(
            self.colors_scroll,
            text="━━ Font Sizes ━━",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=get_color('accent_secondary')
        )
        header.pack(anchor="w", pady=(20, 10), padx=10)
        
        self.font_sliders = {}
        self.font_labels = {}
        
        for prop_name, display_name, min_val, max_val in font_sizes:
            current_size = theme_manager.get(prop_name)
            if current_size is None:
                current_size = 12  # Default
            
            row = ctk.CTkFrame(self.colors_scroll, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=4)
            
            # Label
            ctk.CTkLabel(
                row,
                text=display_name,
                width=140,
                anchor="w",
                font=ctk.CTkFont(size=12),
                text_color=get_color('text_light')
            ).pack(side="left")
            
            # Current value label
            value_label = ctk.CTkLabel(
                row,
                text=f"{current_size}px",
                width=50,
                anchor="e",
                font=ctk.CTkFont(size=11),
                text_color=get_color('accent_primary')
            )
            value_label.pack(side="right", padx=(10, 0))
            self.font_labels[prop_name] = value_label
            
            # Slider
            slider = ctk.CTkSlider(
                row,
                from_=min_val,
                to=max_val,
                number_of_steps=max_val - min_val,
                width=150,
                height=18,
                fg_color=get_color('bg_light'),
                progress_color=get_color('accent_primary_dark'),
                button_color=get_color('accent_primary'),
                button_hover_color=get_color('accent_secondary'),
                command=lambda v, n=prop_name: self.on_font_size_change(n, v)
            )
            slider.set(current_size)
            slider.pack(side="right", padx=5)
            self.font_sliders[prop_name] = slider
    
    def on_font_size_change(self, prop_name: str, value: float):
        """Handle font size slider changes."""
        size = int(value)
        self.font_labels[prop_name].configure(text=f"{size}px")
        theme_manager.set_color(prop_name, size)  # set_color works for any theme prop

    def on_color_entry_change(self, prop_name: str):
        """Handle manual color entry changes."""
        entry = self.color_entries[prop_name]
        value = entry.get().strip()
        
        if self.is_valid_hex(value):
            self.color_swatches[prop_name].configure(fg_color=value, hover_color=value)
            theme_manager.set_color(prop_name, value)
    
    def pick_color(self, prop_name: str):
        """Open color picker for a property."""
        current = self.color_entries[prop_name].get()
        
        result = colorchooser.askcolor(
            color=current,
            title=f"Choose color for {prop_name}",
            parent=self
        )
        
        if result[1]:
            hex_color = result[1]
            entry = self.color_entries[prop_name]
            entry.delete(0, "end")
            entry.insert(0, hex_color)
            self.color_swatches[prop_name].configure(fg_color=hex_color, hover_color=hex_color)
            theme_manager.set_color(prop_name, hex_color)
    
    def is_valid_hex(self, value: str) -> bool:
        """Check if value is a valid hex color."""
        if not value.startswith('#'):
            return False
        if len(value) not in (4, 7):
            return False
        try:
            int(value[1:], 16)
            return True
        except ValueError:
            return False
    
    def on_theme_selected(self, selection: str):
        """Handle theme selection from dropdown."""
        theme_list = theme_manager.get_theme_list()
        for tid, name, is_builtin in theme_list:
            if name == selection:
                # Check if switching to a built-in theme
                if is_builtin and tid != theme_manager.active_theme_id:
                    # Ask if they want fresh preset or current (possibly modified) version
                    result = messagebox.askyesnocancel(
                        "Load Theme",
                        f"Load '{name}' with fresh preset colors?\n\n"
                        f"• Yes = Load original preset colors\n"
                        f"• No = Keep any previous customizations\n"
                        f"• Cancel = Stay on current theme"
                    )
                    if result is None:  # Cancel
                        # Reset dropdown to current theme
                        self.theme_var.set(theme_manager.current.name)
                        return
                    elif result:  # Yes - load fresh
                        theme_manager.reset_theme(tid)
                
                theme_manager.set_theme(tid)
                self.refresh_color_entries()
                break
    
    def refresh_color_entries(self):
        """Refresh all color entries from current theme."""
        for prop_name, entry in self.color_entries.items():
            current = theme_manager.get(prop_name)
            entry.delete(0, "end")
            entry.insert(0, current)
            self.color_swatches[prop_name].configure(fg_color=current, hover_color=current)
    
    def save_theme_as(self):
        """Save current colors as a new named theme."""
        dialog = ctk.CTkInputDialog(
            text="Enter a name for your theme:",
            title="Save Theme"
        )
        name = dialog.get_input()
        
        if name:
            theme_id = theme_manager.create_custom_theme(name, theme_manager.active_theme_id)
            theme_manager.set_theme(theme_id)
            self.refresh_theme_dropdown()
            messagebox.showinfo("Saved", f"Theme '{name}' saved successfully!")
    
    def reset_theme(self):
        """Reset current theme to default preset values."""
        theme_name = theme_manager.current.name
        is_builtin = theme_manager.current.builtin
        
        if is_builtin:
            msg = f"Reset '{theme_name}' to its original preset colors?\n\nThis will undo all your customizations."
        else:
            msg = f"Delete custom theme '{theme_name}' and switch to TSM Dark?"
        
        if messagebox.askyesno("Reset Theme", msg):
            if is_builtin:
                theme_manager.reset_theme()
            else:
                theme_manager.delete_theme(theme_manager.active_theme_id)
                theme_manager.set_theme("tsm_dark")
                self.refresh_theme_dropdown()
            self.refresh_color_entries()
            messagebox.showinfo("Reset", f"Theme reset to defaults!")
    
    def export_theme(self):
        """Export current theme to a JSON file."""
        path = filedialog.asksaveasfilename(
            title="Export Theme",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            parent=self
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
            parent=self
        )
        if path:
            theme_id = theme_manager.import_theme(Path(path))
            if theme_id:
                theme_manager.set_theme(theme_id)
                self.refresh_theme_dropdown()
                self.refresh_color_entries()
                messagebox.showinfo("Imported", "Theme imported successfully!")
            else:
                messagebox.showerror("Error", "Failed to import theme")
    
    def randomize_theme(self):
        """Generate random colors for the current theme."""
        import random
        import colorsys
        
        def random_color() -> str:
            """Generate a random hex color."""
            return f"#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}"
        
        def random_dark_color() -> str:
            """Generate a random dark color for backgrounds."""
            h = random.random()
            s = random.uniform(0.1, 0.3)
            v = random.uniform(0.05, 0.25)
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        
        def random_light_color() -> str:
            """Generate a random light color for text."""
            h = random.random()
            s = random.uniform(0, 0.2)
            v = random.uniform(0.7, 1.0)
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        
        def random_accent_color() -> str:
            """Generate a random vibrant accent color."""
            h = random.random()
            s = random.uniform(0.7, 1.0)
            v = random.uniform(0.8, 1.0)
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        
        def darker_variant(hex_color: str) -> str:
            """Create a darker version of a color."""
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            return f"#{int(r*0.7):02x}{int(g*0.7):02x}{int(b*0.7):02x}"
        
        # Generate a cohesive random theme
        # Base dark colors (all using same hue for cohesion)
        base_hue = random.random()
        
        # Backgrounds - gradient from darkest to lightest
        for i, prop in enumerate(["bg_darkest", "bg_dark", "bg_medium", "bg_light", "bg_hover", "bg_selected"]):
            s = random.uniform(0.1, 0.3)
            v = 0.05 + (i * 0.05)  # Gradual lightening
            r, g, b = colorsys.hsv_to_rgb(base_hue, s, v)
            color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            theme_manager.set_color(prop, color)
        
        # Borders
        theme_manager.set_color("border_dark", random_dark_color())
        theme_manager.set_color("border_light", random_dark_color())
        
        # Text - light colors
        theme_manager.set_color("text_white", "#ffffff")
        theme_manager.set_color("text_light", random_light_color())
        theme_manager.set_color("text_gray", "#888888")
        theme_manager.set_color("text_dark", "#666666")
        
        # Accents - vibrant colors
        accent1 = random_accent_color()
        accent2 = random_accent_color()
        theme_manager.set_color("accent_primary", accent1)
        theme_manager.set_color("accent_primary_dark", darker_variant(accent1))
        theme_manager.set_color("accent_secondary", accent2)
        theme_manager.set_color("accent_secondary_dark", darker_variant(accent2))
        
        # Status colors - keep recognizable
        theme_manager.set_color("color_success", random_accent_color())
        theme_manager.set_color("color_success_dark", "#00aa00")
        theme_manager.set_color("color_warning", random_accent_color())
        theme_manager.set_color("color_error", f"#{random.randint(200,255):02x}{random.randint(0,80):02x}{random.randint(0,80):02x}")
        
        # Item quality - randomize
        theme_manager.set_color("quality_epic", random_accent_color())
        theme_manager.set_color("quality_rare", random_accent_color())
        theme_manager.set_color("quality_uncommon", random_accent_color())
        theme_manager.set_color("quality_common", "#ffffff")
        
        self.refresh_color_entries()
        theme_manager.save()
    
    def refresh_theme_dropdown(self):
        """Refresh the theme dropdown with current themes."""
        theme_list = theme_manager.get_theme_list()
        theme_names = [name for _, name, _ in theme_list]
        self.theme_combo.configure(values=theme_names)
        self.theme_var.set(theme_manager.current.name)
    
    def apply_and_close(self):
        """Save theme and close, prompting for restart."""
        theme_manager.save()
        if messagebox.askyesno(
            "Restart Required",
            "Theme saved! Restart the application now to see all changes?"
        ):
            self.destroy()
            self.parent.destroy()
            import subprocess
            subprocess.Popen([sys.executable, __file__])
        else:
            self.destroy()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    if not HAS_CTK:
        print("Warning: CustomTkinter not installed. For the best experience, run:")
        print("  pip install customtkinter")
        print()
    
    app = TSMScraperApp()
    app.mainloop()


if __name__ == "__main__":
    main()
