# TSM Item Scraper

**Cross-server Item Scraping Tool for TradeSkillMaster on Project Ascension & Retail**

[⬇ Download](https://github.com/Xurkon/TSMItemScraper/releases)
[📂 View Source](https://github.com/Xurkon/TSMItemScraper)

## ✨ Features

### 🌍 Cross-Server Support

Scrape items from **Project Ascension**, **Turtle WoW**, and **Wowhead** (Retail, WotLK, TBC, Classic Era, Cata, MoP).

### 📦 Multi-Format Export

Export item strings in **WotLK 3.3.5a** classic format (`item:12345`) or **Retail TSM** format (`i:12345`).

### 🖥️ Modern GUI

Sleek, dark-themed interface with **Theme Editor** (4 built-in themes + custom colors).

### ⚡ One-Click Import

Directly updates your `TradeSkillMaster.lua` SavedVariables file - no copy-paste needed.

### 🛡️ Smart Safety

Automatic backups of your TSM config before every import.

## 📥 Installation

### Option 1: Standalone EXE (Recommended)

1. Download the latest release
2. Run `TSM Scraper.exe`
3. Configure your TSM path and start scraping!

### Option 2: Python Source

1. Clone this repository
2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Run the GUI:

   ```
   python gui_modern.py
   ```

## 🔧 Usage

1. **Select Database**: Choose your game version (e.g., `Wowhead (WotLK)`, `Project Ascension`)
2. **Select Format**: Choose your client version (`WotLK 3.3.5a` or `Retail`)
3. **Select Categories**: Check the item types you want (Weapons, Armor, Consumables)
4. **Scrape**: Click the **🔍 Scrape Items** button
5. **Import**: Review new items and click **📥 Import to TSM**

## 📜 Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

### v2.1.0 - Cross-Server Update

- Added **all Wowhead versions** (TBC, Cata, MoP Classic)
- Added **Turtle WoW** database support
- **Format Selection**: Separate TSM output format from database source
- **GUI**: Mouse wheel scrolling, theme updates, dialog fixes

## 👥 Credits

- **Xurkon** - Main Developer
- **Project Ascension** - For the amazing 3.3.5a custom server
- **Wowhead** - For the comprehensive item databases

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.
