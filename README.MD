<div align="center">

# TSM-Scraper

![Version](https://img.shields.io/badge/version-v3.4.24-blue.svg?style=for-the-badge)
![Downloads](https://img.shields.io/github/downloads/Xurkon/TSM-Scraper/total?style=for-the-badge&color=e67e22)
[![Documentation](https://img.shields.io/badge/Documentation-View%20Docs-58a6ff?style=for-the-badge)](https://xurkon.github.io/TSM-Scraper/)
[![Patreon](https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white)](https://www.patreon.com/Xurkon)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://www.paypal.me/Xurkon)
![License](https://img.shields.io/github/license/Xurkon/TSM-Scraper?style=for-the-badge&color=2980b9)
![Python](https://img.shields.io/badge/PYTHON-3.11+-blue?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/PLATFORM-WINDOWS-blue?style=for-the-badge&logo=windows&logoColor=white)

<br/>
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

1. Download the latest release
2. Run `TSM Scraper.exe`
3. Configure your TSM path and start scraping!

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
| **Config** | `%APPDATA%\TSM-Scraper\config\gui_config.json` |
| **Logs** | `%APPDATA%\TSM-Scraper\logs\scraper.log` |

To open this folder, press `Win + R`, type `%APPDATA%\TSM-Scraper`, and press Enter.

## 📜 Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

### v3.5.0 - Wowhead ID Verification & Safety

- **Wowhead to Ascension ID Verification System**: Complete implementation of automatic item ID verification when importing from Wowhead databases to Project Ascension
- **Three Verification Modes**:
  - `Verified Only (Safest)`: Only imports items where the ID is confirmed to exist on Ascension with a matching name
  - `Trust Missing Items`: Also imports items not found in Ascension's database (useful since their DB is incomplete)
  - `No Verification (Risky)`: Uses Wowhead IDs directly without any verification
- **ID Conflict Detection**: Automatically detects when a Wowhead ID points to a different item on Ascension and searches by name to find the correct ID
- **Verification Statistics**: Results display now shows counts for verified, remapped, trusted, and failed items
- **Progress Feedback**: Status bar shows verification progress when processing Wowhead imports
- **Detailed Logging**: Failed items are logged with reasons for troubleshooting

## 👥 Credits

- **Xurkon** - Main Developer
- **Project Ascension** - For the amazing 3.3.5a custom server
- **Wowhead** - For the comprehensive item databases
- **TurtleWoW** - Also for a great server!

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.
