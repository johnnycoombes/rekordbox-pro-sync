# 🎧 Rekordbox 7 Pro Sync Suite 

A high-performance, standalone Windows utility designed to automate Rekordbox library management and audio conversion for professional DJ workflows. Built for seamless integration with modern standalone hardware like the AlphaTheta XDJ-AZ.

This suite operates as a 100% portable, single `.exe` file. No Python installation, system PATH configuration, or external FFmpeg downloads are required.

## 🚀 Key Features

### 📁 Module 1: Directory XML Sync
Perfect for bulk-importing new tracks with rich metadata.
* **Smart Meta-Extraction:** Reads ID3 tags (including Mixed In Key data) to extract Tonality, Label, Remixer, and Mix tags dynamically. Features a fallback engine to extract mix titles directly from track parentheses.
* **Automated Colour Coding:** Reads `ContentGroup` or `Comment` tags for "Energy X" (1-10) values and maps them directly to Rekordbox's strict 8-colour RGB hex spectrum.
* **Visual Preview:** A floating, interactive UI that visualizes exactly how your folders will look inside Rekordbox before you generate the XML.

### 🔄 Module 2: M3U8 FLAC to MP3 Converter
Designed to prep high-res library playlists for hardware that requires specific formats.
* **In-Place Conversion:** Scans a Rekordbox `.m3u8` exported playlist, locates the local FLAC files, and clones them into pristine 320kbps CBR MP3s directly alongside the originals.
* **Lossless Tag Mirroring:** Copies all custom DJ metadata (Energy, Key, Mix, Remixer) from the FLAC and perfectly injects it into the new MP3's ID3 frames.
* **Auto-XML Generation:** Drops a `rekordbox_converted_playlist.xml` directly into the M3U8's source folder, ready for instant Rekordbox import.
* **Bundled FFmpeg:** The audio encoding engine is securely bundled inside the application. No external dependencies required.

## 💻 Tech Stack
* **Language:** Python 3.12+
* **GUI Framework:** `customtkinter` (Modern Dark-Mode UI)
* **Metadata Parsing:** `mutagen` (Robust multi-format ID3/Vorbis parsing)
* **Audio Engine:** `ffmpeg` (Bundled dynamically via PyInstaller)
* **XML Engine:** Native `xml.etree.ElementTree` with `minidom` formatting

## 🛠️ How to Use

**For Standard Directory Syncing:**
1. Open `RB-Pro-Sync.exe`.
2. On Tab 1, click **Add Music Folder(s)** to queue your local drives.
3. Review your hierarchy in the **Preview Window**.
4. Click **GENERATE V7 XML** and save the file.
5. In Rekordbox, go to *Preferences > Advanced > Database*, and point the "rekordbox xml" path to your generated file.

**For FLAC Playlist Conversion:**
1. In Rekordbox, right-click a playlist and select *Export Playlist > As M3U8 format*.
2. Open `RB-Pro-Sync.exe` and navigate to Tab 2.
3. Click **Select Playlist M3U8 File**.
4. Click **Preview Tracks to Convert** to verify the paths.
5. Click **RUN IN-PLACE FLAC PIPELINE**. The app will create the MP3s and the final XML right next to your M3U8 file.

## 📦 How to Build from Source
If you wish to compile the application yourself, ensure Python is installed and added to your system PATH. You will also need a downloaded copy of `ffmpeg.exe` placed in the project root folder.

```bash
# 1. Install Python requirements
pip install customtkinter mutagen pyinstaller

# 2. Compile the standalone executable (Bundling FFmpeg inside)
pyinstaller --noconsole --onefile --add-binary "ffmpeg.exe;." --collect-all customtkinter RB-Pro-Sync.py
