# 🎧 Rekordbox 7 Pro Sync Suite

A high-performance, standalone Windows utility designed to automate Rekordbox library management and audio conversion for professional DJ workflows. This tool is purpose-built for seamless integration with modern standalone hardware like the AlphaTheta XDJ-AZ.

## 🚀 Key Features

### 📁 Module 1: Directory XML Sync
Manage your entire library hierarchy with surgical precision.
* **Interactive Selection:** Use the **Preview Window** to selectively sync folders or individual tracks. Default state is "Select All," with granular toggle support.
* **Smart Meta-Extraction:** Automatically parses ID3 tags for Tonality, Label, Remixer, and Mix information.
* **Audio Analytics:** Automatically calculates track **Length**, **Bitrate**, and **Type** for every file in your library.
* **LQ Detection:** Automatically flags any MP3 files below 320kbps with a high-visibility **[LQ]** tag and red background alert, allowing you to identify files needing replacement before your gig.
* **Energy Mapping:** Reads Energy levels (1-10) and maps them to Rekordbox's strict RGB colour spectrum.

### 🔄 Module 2: M3U8 FLAC to MP3 Converter
Prepare high-res archives for older hardware compatibility.
* **In-Place Conversion:** Scans a Rekordbox `.m3u8` playlist, clones FLAC tracks into 320kbps CBR MP3s, and saves them directly alongside the source files.
* **Metadata Integrity:** Mirrors all DJ metadata (Energy, Key, Mix, Remixer) from the FLAC file into the new MP3 ID3 frames.
* **Bulk Management:** A dedicated **FLAC Manager** utility allows you to select specific files for batch conversion, bypassing the need to convert your entire library if you only need a few tracks.
* **Bundled Engine:** Uses a bundled `ffmpeg.exe`—no installation required.

## 💻 Tech Stack
* **Language:** Python 3.12+
* **GUI:** `customtkinter` (Modern, scalable dark-mode UI)
* **Metadata Parsing:** `mutagen` (Robust multi-format ID3/Vorbis parsing)
* **Audio Engine:** `ffmpeg` (Bundled dynamically for portability)
* **XML Engine:** Native `xml.etree.ElementTree`

## 🛠️ How to Use

**For Syncing/XML Generation:**
1. Open `RB-Pro-Sync.exe`.
2. Add your music folders.
3. Click **Show Preview Window** to toggle specific folders or tracks for the sync.
4. Click **GENERATE V7 XML** and save the file.
5. In Rekordbox, point your *rekordbox xml* path (in Preferences) to the generated file.

**For FLAC Conversion:**
1. Export a playlist from Rekordbox as an `.m3u8` file.
2. Open the **FLAC to MP3 Converter** tab.
3. Pick your `.m3u8` file.
4. Convert tracks in-place. The suite will create the new MP3 files and the updated XML mapper automatically.

## 📦 How to Build from Source
Ensure Python is installed. You will need `ffmpeg.exe` in your project root.

```bash
# 1. Install dependencies
pip install customtkinter mutagen pyinstaller

# 2. Compile standalone executable
pyinstaller --noconsole --onefile --add-binary "ffmpeg.exe;." --collect-all customtkinter RB-Pro-Sync.py