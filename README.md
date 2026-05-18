# Rekordbox 7 Pro Sync (Python Edition)

A high-performance, standalone Windows utility designed to automate Rekordbox library management for professional DJ workflows. This tool crawls local SSD directories, parses ID3 metadata (including Mixed In Key tags), and generates a perfectly formatted Pioneer DJ XML file optimized for the Rekordbox v7.x engine.

## 🚀 Features
* **Multi-Folder Queuing:** Select multiple root directories across different drives.
* **Interactive Playlist Preview:** A floating, scrollable UI that visualizes exactly how your folders will look inside Rekordbox before you sync.
* **Smart Meta-Extraction:** Extracts Tonality, Label, Remixer, and Mix tags dynamically. Features a fallback engine to extract mix titles directly from track parentheses.
* **Automated Colour Coding:** Reads `ContentGroup` or `Comment` tags for "Energy X" values and maps them directly to Rekordbox's strict 8-colour RGB hex spectrum.
* **Zero Dependencies:** Fully compiled standalone `.exe` using PyInstaller.

## 💻 Tech Stack
* **Language:** Python 3.12+
* **GUI Framework:** `customtkinter` (Modern Dark-Mode UI)
* **Metadata Parsing:** `mutagen` (Robust multi-format ID3/Vorbis parsing)
* **XML Engine:** Native `xml.etree.ElementTree` with `minidom` formatting

## 🛠️ How to Use
1. Download the latest `RB-Pro-Sync.exe` from the Releases tab (or compile it yourself).
2. Click **Add Music Folder(s)** to queue your local drives.
3. Review your hierarchy in the **Preview Window**.
4. Click **GENERATE V7 XML** and save the file.
5. Open Rekordbox, go to *Preferences > Advanced > Database*, and point the "rekordbox xml" path to your generated file.

## 📦 How to Build from Source
Ensure Python is installed and added to your system PATH.
```bash
# Install requirements
pip install customtkinter mutagen pyinstaller

# Compile the standalone executable
pyinstaller --noconsole --onefile --collect-all customtkinter RB-Pro-Sync.py