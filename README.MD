> [!WARNING]
> ## ⚠️ Project Ascension ID Warning
> **Project Ascension uses different Item IDs than Retail WoW.**
>
> Importing IDs directly from WoWhead may return **unexpected items** or incorrect data. Always verify IDs against the [Ascension Database](https://ascension.gg/database) or in-game tooltips before importing.

<div align="center">

# TSM Item Scraper

![Version](https://img.shields.io/badge/version-v3.4.7-blue.svg)
![License](https://img.shields.io/github/license/Xurkon/TSM-Scraper?style=for-the-badge&label=LICENSE&color=2980b9)
![Downloads](https://img.shields.io/github/downloads/Xurkon/TSM-Scraper/total?style=for-the-badge&label=DOWNLOADS&color=e67e22)
![Python](https://img.shields.io/badge/PYTHON-3.11+-blue?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/PLATFORM-WINDOWS-blue?style=for-the-badge&logo=windows&logoColor=white)

<br/>
         This is still very much a beta and needs lots of testing and fixes! Currently broken and corrupting saved variables, beware! <br/>
**Cross-server Item Scraping Tool for TradeSkillMaster on Project Ascension & Retail**

[⬇ **Download Latest**](https://github.com/Xurkon/TSM-Scraper/releases/latest) &nbsp;&nbsp;•&nbsp;&nbsp; [📂 **View Source**](https://github.com/Xurkon/TSM-Scraper) &nbsp;&nbsp;•&nbsp;&nbsp; [📖 **Read Documentation**](https://xurkon.github.io/TSM-Scraper/)

</div>

---

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

## 📁 File Locations

Configuration and log files are stored in your Windows AppData folder:

| File | Location |
|------|----------|
| **Config** | `%APPDATA%\TSM Scraper\config\gui_config.json` |
| **Logs** | `%APPDATA%\TSM Scraper\logs\scraper.log` |

To open this folder, press `Win + R`, type `%APPDATA%\TSM Scraper`, and press Enter.


## 📜 Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

### v3.4.7 - Empty Profile Fix

- **Fixed Import to Empty Profiles**: Items can now be imported after creating default groups
- Previously failed with "Could not find [S] table" error

### v3.3.4 - Group Parsing Fix

- **Fixed Ascension Group Detection**: Groups without backticks (like 'testing') now properly detected
- Parses groups from Ascension's `profiles.Default.groups` section

### v3.3.3 - Config and Display Fix

- **Version Display**: Window title now shows version number
- **Config Loading Fix**: Fixed config/log paths for compiled exe
- **Ascension TSM Support**: Proper format detection and group creation

### v3.3.0 - UI Overhaul

- **Manual Item IDs**: Add/remove specific item IDs with single entry, paste list, or remove mode
- **4-Column UI Layout**: Options | Categories | Results | Groups for better workflow
- **Draggable Column Resize**: Drag dividers between columns to customize widths

### v3.2.0 - Feature Merge Update

- **Bind Type Filter**: Filter items by BoE, BoP, BoU, BoA, Quest, Warbound
- **Group Management**: Right-click groups to Rename, Add Sub-Group, Delete
- **Profile Management**: Store and switch between up to 5 TSM profiles

## 👥 Credits

- **Xurkon** - Main Developer
- **Project Ascension** - For the amazing 3.3.5a custom server
- **Wowhead** - For the comprehensive item databases
- **TurtleWoW** - Also for a great server!
## 📄 License

MIT License - See [LICENSE](LICENSE) for details.
