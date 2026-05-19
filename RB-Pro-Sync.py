import sys
import os
import shutil
import urllib.parse
import subprocess
import threading
import xml.etree.ElementTree as ET
from xml.dom import minidom
import customtkinter as ctk
from customtkinter import filedialog
from mutagen import File
from mutagen.id3 import ID3, TKEY, TPUB, TPE4, TIT3, TIT1, COMM

# Set modern dark mode styling
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

AUDIO_EXTENSIONS = (".mp3", ".wav", ".flac", ".aif", ".aiff", ".m4a")

class PreviewWindow(ctk.CTkToplevel):
    """Separate, floating, resizable and scrollable Playlist Preview Window."""
    def __init__(self, parent, preview_data):
        super().__init__(parent)
        self.title("👁️ Rekordbox Playlist Preview")
        self.geometry("450x550")
        self.attributes("-topmost", True)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Visual Hierarchy Tree")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        if not preview_data:
            lbl = ctk.CTkLabel(self.scroll_frame, text="No folders queued yet.", font=("Arial", 13, "italic"))
            lbl.pack(anchor="w", padx=10, pady=5)
            return

        for tree in preview_data:
            self.render_node(self.scroll_frame, tree, level=0)
            
    def render_node(self, parent_widget, node, level):
        indent = "    " * level
        if not node["sub_folders"]:
            lbl = ctk.CTkLabel(parent_widget, text=f"{indent}🎵 {node['name']} ({node['direct_tracks']} tracks)", font=("Arial", 12))
            lbl.pack(anchor="w", padx=5, pady=2)
        else:
            lbl = ctk.CTkLabel(parent_widget, text=f"{indent}📁 {node['name']}", font=("Arial", 12, "bold"), text_color="#3a7ebf")
            lbl.pack(anchor="w", padx=5, pady=2)
            
            if node["direct_tracks"] > 0:
                root_lbl = ctk.CTkLabel(parent_widget, text=f"{indent}    🎵 {node['name']} [Root Tracks] ({node['direct_tracks']} tracks)", font=("Arial", 11, "italic"), text_color="gray")
                root_lbl.pack(anchor="w", padx=5, pady=1)
                
            for sub in node["sub_folders"]:
                self.render_node(parent_widget, sub, level + 1)

class ConverterPreviewWindow(ctk.CTkToplevel):
    """Separate window to preview FLAC tracks queued for conversion."""
    def __init__(self, parent, track_list):
        super().__init__(parent)
        self.title("👁️ Tracks Queued for Conversion")
        self.geometry("500x400")
        self.attributes("-topmost", True)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text=f"Found {len(track_list)} FLAC Tracks")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        if not track_list:
            lbl = ctk.CTkLabel(self.scroll_frame, text="No valid FLAC tracks found.", font=("Arial", 13, "italic"))
            lbl.pack(anchor="w", padx=10, pady=5)
            return

        for idx, track_path in enumerate(track_list, 1):
            file_name = os.path.basename(track_path)
            lbl = ctk.CTkLabel(self.scroll_frame, text=f"{idx}. {file_name}", font=("Arial", 11))
            lbl.pack(anchor="w", padx=5, pady=2)


class RekordboxApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Rekordbox 7 Pro Sync Suite")
        self.geometry("700x700")
        self.resizable(True, True)
        self.minsize(680, 600)
        
        # State Data
        self.folder_paths = []
        self.preview_trees = []
        self.preview_window = None
        
        self.m3u8_path = ""
        self.m3u8_flac_paths = [] 
        self.converter_preview_window = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        self.heading = ctk.CTkLabel(self, text="Rekordbox 7 Pro Sync Suite v6.8", font=("Arial", 22, "bold"))
        self.heading.pack(pady=(15, 2))
        self.subheading = ctk.CTkLabel(self, text="Advanced Music Pipeline Engine", font=("Arial", 12), text_color="gray")
        self.subheading.pack(pady=(0, 10))
        
        # TAB CONFIGURATION
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=10)
        
        self.tab_sync = self.tabview.add("📁 Directory XML Sync")
        self.tab_convert = self.tabview.add("🔄 M3U8 FLAC to MP3 Converter")
        
        self.build_sync_tab()
        self.build_converter_tab()

    # =========================================================================
    # TAB 1: DIRECTORY SYNC LOGIC
    # =========================================================================
    def build_sync_tab(self):
        self.src_frame = ctk.CTkFrame(self.tab_sync)
        self.src_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.src_title_frame = ctk.CTkFrame(self.src_frame, fg_color="transparent")
        self.src_title_frame.pack(fill="x", padx=10, pady=5)
        
        self.src_label = ctk.CTkLabel(self.src_title_frame, text="1. Source Selection:", font=("Arial", 13, "bold"))
        self.src_label.pack(side="left")
        
        self.btn_preview = ctk.CTkButton(self.src_title_frame, text="👁️ Show Preview Window", width=150, height=24, command=self.toggle_preview, state="disabled")
        self.btn_preview.pack(side="right")
        
        self.btn_add = ctk.CTkButton(self.src_frame, text="➕ Add Music Folder(s)", command=self.add_folders)
        self.btn_add.pack(anchor="w", padx=10, pady=5)
        
        self.scroll_paths = ctk.CTkScrollableFrame(self.src_frame)
        self.scroll_paths.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.opts_frame = ctk.CTkFrame(self.tab_sync)
        self.opts_frame.pack(fill="x", padx=10, pady=10)
        
        self.opts_label = ctk.CTkLabel(self.opts_frame, text="2. Automation Options:", font=("Arial", 13, "bold"))
        self.opts_label.pack(anchor="w", padx=10, pady=5)
        
        self.var_grouping = ctk.BooleanVar(value=True)
        self.chk_grouping = ctk.CTkCheckBox(self.opts_frame, text="🏷️ Push 'Energy X' to Grouping (Searchable)", variable=self.var_grouping)
        self.chk_grouping.pack(anchor="w", padx=15, pady=5)
        
        self.btn_generate = ctk.CTkButton(self.tab_sync, text="🚀 GENERATE V7 XML", font=("Arial", 16, "bold"), height=40, fg_color="#2b7337", hover_color="#1e5226", command=self.generate_xml, state="disabled")
        self.btn_generate.pack(pady=10)
        
        self.status_lbl = ctk.CTkLabel(self.tab_sync, text="Ready to sync library to Rekordbox 7", font=("Arial", 12, "bold"), text_color="#4BB543")
        self.status_lbl.pack(pady=5)

    # =========================================================================
    # TAB 2: M3U8 FLAC TO MP3 CONVERTER LOGIC
    # =========================================================================
    def build_converter_tab(self):
        conv_frame = ctk.CTkFrame(self.tab_convert)
        conv_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        lbl_desc = ctk.CTkLabel(conv_frame, text="Scan an export playlist (.m3u8), clone FLAC tracks into 320kbps CBR MP3s\nsaved directly alongside the source files, mirror tags, and build an XML mapper.", justify="left", font=("Arial", 12))
        lbl_desc.pack(anchor="w", padx=15, pady=15)
        
        self.lbl_m3u8 = ctk.CTkLabel(conv_frame, text="No M3U8 file selected.", text_color="gray", font=("Arial", 11, "italic"))
        
        btn_row = ctk.CTkFrame(conv_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=5)
        
        btn_pick_m3u8 = ctk.CTkButton(btn_row, text="📋 Select Playlist M3U8 File", command=self.pick_m3u8)
        btn_pick_m3u8.pack(side="left", padx=(0, 10))
        
        self.btn_preview_m3u8 = ctk.CTkButton(btn_row, text="👁️ Preview Tracks to Convert", command=self.show_m3u8_preview, state="disabled", fg_color="#5a5a5a", hover_color="#404040")
        self.btn_preview_m3u8.pack(side="left")
        
        self.lbl_m3u8.pack(anchor="w", padx=25, pady=(0, 15))
        
        self.txt_console = ctk.CTkTextbox(conv_frame, height=180, font=("Courier", 11))
        self.txt_console.pack(fill="both", expand=True, padx=15, pady=10)
        self.txt_console.configure(state="disabled")
        
        self.btn_convert_pipeline = ctk.CTkButton(self.tab_convert, text="🔄 RUN IN-PLACE FLAC PIPELINE", font=("Arial", 16, "bold"), height=40, fg_color="#3a7ebf", hover_color="#275682", command=self.start_conversion_thread, state="disabled")
        self.btn_convert_pipeline.pack(pady=15)

    def log_to_conv_console(self, msg):
        """Thread-safe UI logging"""
        def update():
            self.txt_console.configure(state="normal")
            self.txt_console.insert("end", msg + "\n")
            self.txt_console.see("end")
            self.txt_console.configure(state="disabled")
        self.after(0, update)

    def clean_rekordbox_path(self, raw_path):
        p = urllib.parse.unquote(raw_path.strip())
        if p.startswith("file://localhost/"): p = p[17:]
        elif p.startswith("file:///"): p = p[8:]
        elif p.startswith("file://"): p = p[7:]
        
        if os.name == 'nt' and p.startswith('/') and len(p) > 2 and p[2] == ':':
            p = p[1:]
            
        if not os.path.isabs(p):
            p = os.path.join(os.path.dirname(self.m3u8_path), p)
            
        return os.path.normpath(p)

    def pick_m3u8(self):
        f = filedialog.askopenfilename(filetypes=[("M3U8 Playlist", "*.m3u8")])
        if f:
            self.m3u8_path = os.path.abspath(f)
            self.lbl_m3u8.configure(text=self.m3u8_path, text_color="white")
            self.parse_m3u8_for_preview()

    def parse_m3u8_for_preview(self):
        self.m3u8_flac_paths = []
        missing_paths = []
        self.log_to_conv_console("Scanning playlist file...")
        
        try:
            with open(self.m3u8_path, "r", encoding="utf-8-sig") as f:
                for line in f:
                    if line.strip().lower().endswith(".flac"):
                        clean_path = self.clean_rekordbox_path(line)
                        if os.path.exists(clean_path):
                            self.m3u8_flac_paths.append(clean_path)
                        else:
                            missing_paths.append(clean_path)
        except Exception as e:
            self.log_to_conv_console(f"❌ Failed parsing playlist file: {str(e)}")
            
        if self.m3u8_flac_paths:
            self.btn_preview_m3u8.configure(state="normal")
            self.btn_convert_pipeline.configure(state="normal")
            self.log_to_conv_console(f"✅ Loaded M3U8. Found {len(self.m3u8_flac_paths)} valid FLAC tracks.")
        else:
            self.btn_preview_m3u8.configure(state="disabled")
            self.btn_convert_pipeline.configure(state="disabled")
            self.log_to_conv_console("⚠️ Loaded M3U8, but found 0 valid local FLAC tracks.")
            
        if missing_paths:
            self.log_to_conv_console(f"⚠️ Warning: Could not locate {len(missing_paths)} tracks on your hard drive. Example:")
            self.log_to_conv_console(f"   -> {missing_paths[0]}")

    def show_m3u8_preview(self):
        if self.converter_preview_window and self.converter_preview_window.winfo_exists():
            self.converter_preview_window.destroy()
        self.converter_preview_window = ConverterPreviewWindow(self, self.m3u8_flac_paths)

    def start_conversion_thread(self):
        self.btn_convert_pipeline.configure(state="disabled")
        threading.Thread(target=self.run_m3u8_pipeline, daemon=True).start()

    def get_ffmpeg_path(self):
        """Looks for ffmpeg.exe bundled in PyInstaller, then locally, then system PATH."""
        # 1. If running as a bundled PyInstaller exe, look in the temp _MEIPASS folder
        if hasattr(sys, '_MEIPASS'):
            bundled_ffmpeg = os.path.join(sys._MEIPASS, 'ffmpeg.exe')
            if os.path.exists(bundled_ffmpeg):
                return bundled_ffmpeg
                
        # 2. Look in the local directory next to the Python script
        if os.path.exists("ffmpeg.exe"):
            return "ffmpeg.exe"
            
        # 3. Look in the system PATH
        if shutil.which("ffmpeg"):
            return "ffmpeg"
            
        return None

    def run_m3u8_pipeline(self):
        ffmpeg_exe = self.get_ffmpeg_path()
        if not ffmpeg_exe:
            self.log_to_conv_console("\n❌ CRITICAL ERROR: 'ffmpeg.exe' was not found.")
            self.log_to_conv_console("Please download ffmpeg.exe and place it in the same folder as this app.")
            self.after(0, lambda: self.btn_convert_pipeline.configure(state="normal"))
            return

        if not self.m3u8_flac_paths:
            self.log_to_conv_console("❌ Complete: No valid local FLAC tracks discovered.")
            self.after(0, lambda: self.btn_convert_pipeline.configure(state="normal"))
            return
            
        self.log_to_conv_console(f"\n🚀 Commencing conversion using bundled engine...")
        
        root_node = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
        ET.SubElement(root_node, "PRODUCT", Name="rekordbox", Version="7.2.0", Vendor="PioneerDJ")
        collection_xml = ET.SubElement(root_node, "COLLECTION", Entries="0")
        playlists_root = ET.SubElement(root_node, "PLAYLISTS")
        root_playlist_node = ET.SubElement(playlists_root, "NODE", Name="ROOT", Type="0", Count="1")
        
        playlist_name = os.path.splitext(os.path.basename(self.m3u8_path))[0] + " (Converted MP3)"
        playlist_node_xml = ET.SubElement(root_playlist_node, "NODE", Name=playlist_name, Type="1", KeyType="0", Entries="0")
        
        track_id = 1
        
        for f_path in self.m3u8_flac_paths:
            base_name = os.path.splitext(os.path.basename(f_path))[0]
            parent_dir = os.path.dirname(f_path)
            out_mp3_path = os.path.join(parent_dir, f"{base_name}.mp3")
            
            self.log_to_conv_console(f"Processing [{track_id}/{len(self.m3u8_flac_paths)}]: {base_name}...")
            
            meta = self.get_track_metadata(f_path)
            
            cmd = [
                ffmpeg_exe, "-y", "-i", f_path,
                "-codec:a", "libmp3lame", "-b:a", "320k",
                "-map_metadata", "0", out_mp3_path
            ]
            
            try:
                subprocess.run(cmd, capture_output=True, check=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                
                try:
                    mp3_file = ID3(out_mp3_path)
                    if meta["tonality"]: mp3_file.add(TKEY(encoding=3, text=meta["tonality"]))
                    if meta["label"]: mp3_file.add(TPUB(encoding=3, text=meta["label"]))
                    if meta["remixer"]: mp3_file.add(TPE4(encoding=3, text=meta["remixer"]))
                    if meta["mix"]: mp3_file.add(TIT3(encoding=3, text=meta["mix"]))
                    
                    if meta["energy"] is not None:
                        mp3_file.add(TIT1(encoding=3, text=f"Energy {meta['energy']}"))
                        mp3_file.add(COMM(encoding=3, lang='eng', desc='', text=f"Energy {meta['energy']}"))
                    mp3_file.save()
                except Exception as id3_err:
                    self.log_to_conv_console(f"  ⚠️ ID3 Meta Warning: {str(id3_err)}")

                abs_url = out_mp3_path.replace("\\", "/")
                loc_uri = f"file://localhost/{urllib.parse.quote(abs_url)}".replace("%2F", "/").replace("%3A", ":")
                
                track_attrs = {
                    "TrackID": str(track_id),
                    "Name": base_name,
                    "Location": loc_uri
                }
                
                color_hex = self.get_colour_hex(meta["energy"])
                if color_hex: track_attrs["Colour"] = color_hex
                if meta["energy"] is not None: track_attrs["Grouping"] = f"Energy {meta['energy']}"
                if meta["tonality"]: track_attrs["Tonality"] = meta["tonality"]
                if meta["label"]: track_attrs["Label"] = meta["label"]
                if meta["remixer"]: track_attrs["Remixer"] = meta["remixer"]
                if meta["mix"]: track_attrs["Mix"] = meta["mix"]
                
                ET.SubElement(collection_xml, "TRACK", **track_attrs)
                ET.SubElement(playlist_node_xml, "TRACK", Key=str(track_id))
                
                track_id += 1
                
            except subprocess.CalledProcessError as e:
                self.log_to_conv_console(f"❌ Conversion failed! FFMPEG Error:\n{e.stderr}")
                self.after(0, lambda: self.btn_convert_pipeline.configure(state="normal"))
                return
            except Exception as ex:
                self.log_to_conv_console(f"❌ Pipeline exception encounter: {str(ex)}")
                self.after(0, lambda: self.btn_convert_pipeline.configure(state="normal"))
                return
                
        collection_xml.set("Entries", str(track_id - 1))
        playlist_node_xml.set("Entries", str(track_id - 1))
        
        m3u8_dir = os.path.dirname(self.m3u8_path)
        xml_save_path = os.path.join(m3u8_dir, "rekordbox_converted_playlist.xml")
        raw_xml = ET.tostring(root_node, 'utf-8')
        reparsed = minidom.parseString(raw_xml)
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")
        
        with open(xml_save_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
            
        self.log_to_conv_console(f"\n🎉 PIPELINE SUCCESSFUL!")
        self.log_to_conv_console(f"• Generated {track_id - 1} MP3 files in-place alongside original FLAC assets.")
        self.log_to_conv_console(f"• Saved index mapper XML directly to:\n  {xml_save_path}")
        
        self.after(0, lambda: self.btn_convert_pipeline.configure(state="normal"))

    # =========================================================================
    # BACKEND HELPERS & GENERAL METADATA HANDLING ENGINE
    # =========================================================================
    def add_folders(self):
        folder = filedialog.askdirectory()
        if folder:
            folder_abs = os.path.abspath(folder)
            if folder_abs not in self.folder_paths:
                self.folder_paths.append(folder_abs)
                self.refresh_paths_ui()
                tree_data = self.build_preview_tree(folder_abs)
                if tree_data: self.preview_trees.append(tree_data)
                self.btn_preview.configure(state="normal")
                self.btn_generate.configure(state="normal")
                self.open_preview_window()

    def refresh_paths_ui(self):
        for widget in self.scroll_paths.winfo_children(): widget.destroy()
        for idx, path in enumerate(self.folder_paths):
            row = ctk.CTkFrame(self.scroll_paths, fg_color="transparent")
            row.pack(fill="x", pady=2)
            btn_del = ctk.CTkButton(row, text="❌", width=24, height=24, fg_color="#8b2525", hover_color="#5e1919", command=lambda i=idx: self.remove_folder(i))
            btn_del.pack(side="left", padx=(0, 5))
            lbl = ctk.CTkLabel(row, text=path, font=("Arial", 11))
            lbl.pack(side="left")

    def remove_folder(self, idx):
        self.folder_paths.pop(idx)
        if idx < len(self.preview_trees): self.preview_trees.pop(idx)
        self.refresh_paths_ui()
        if not self.folder_paths:
            self.btn_preview.configure(state="disabled")
            self.btn_generate.configure(state="disabled")
            if self.preview_window:
                self.preview_window.destroy()
                self.preview_window = None
        elif self.preview_window:
            self.open_preview_window()

    def toggle_preview(self):
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.destroy()
            self.preview_window = None
        else:
            self.open_preview_window()

    def open_preview_window(self):
        if self.preview_window and self.preview_window.winfo_exists(): self.preview_window.destroy()
        self.preview_window = PreviewWindow(self, self.preview_trees)

    def build_preview_tree(self, dir_path):
        name = os.path.basename(dir_path)
        if not name: return None
        direct_tracks = 0
        sub_folders = []
        try:
            entries = sorted(os.listdir(dir_path))
            for entry in entries:
                full_path = os.path.join(dir_path, entry)
                if os.path.isdir(full_path):
                    sub = self.build_preview_tree(full_path)
                    if sub and (sub["direct_tracks"] > 0 or sub["sub_folders"]): sub_folders.append(sub)
                elif os.path.isfile(full_path) and full_path.lower().endswith(AUDIO_EXTENSIONS):
                    direct_tracks += 1
        except Exception: return None
        if direct_tracks > 0 or sub_folders:
            return {"name": name, "direct_tracks": direct_tracks, "sub_folders": sub_folders}
        return None

    def get_track_metadata(self, file_path):
        meta = {"energy": None, "tonality": None, "label": None, "remixer": None, "mix": None}
        try:
            audio = File(file_path)
            if audio and audio.tags:
                tags = audio.tags
                
                for key in ['TKEY', 'initialkey', 'ORGANIZATION']: 
                    if key in tags:
                        meta["tonality"] = str(tags[key][0]) if isinstance(tags[key], list) else str(tags[key])
                        break
                for key in ['TPUB', 'publisher', 'label', 'ORGANIZATION']: 
                    if key in tags:
                        meta["label"] = str(tags[key][0]) if isinstance(tags[key], list) else str(tags[key])
                        break
                for key in ['TPE4', 'remixer']: 
                    if key in tags:
                        meta["remixer"] = str(tags[key][0]) if isinstance(tags[key], list) else str(tags[key])
                        break
                for key in ['TIT3', 'subtitle']: 
                    if key in tags:
                        meta["mix"] = str(tags[key][0]) if isinstance(tags[key], list) else str(tags[key])
                        break

                grouping_text = ""
                for key in ['TIT1', 'grouping', 'CONTENTGROUP']:
                    if key in tags:
                        grouping_text = str(tags[key][0]).lower() if isinstance(tags[key], list) else str(tags[key]).lower()
                        break
                if "energy" in grouping_text:
                    digits = "".join([c for c in grouping_text.split("energy")[-1] if c.isdigit()])
                    if digits: meta["energy"] = int(digits)

                if meta["energy"] is None:
                    comment_text = ""
                    for key in ['COMM', 'comment', 'DESCRIPTION']:
                        if key in tags:
                            comment_text = str(tags[key]).lower()
                            break
                    if "energy" in comment_text:
                        digits = "".join([c for c in comment_text.split("energy")[-1] if c.isdigit()])
                        if digits: meta["energy"] = int(digits)
                    else:
                        digits = "".join([c for c in comment_text if c.isdigit()])
                        if digits and 0 < int(digits) <= 10: meta["energy"] = int(digits)

                if meta["mix"] is None:
                    title = ""
                    for key in ['TIT2', 'title']:
                        if key in tags:
                            title = str(tags[key][0]) if isinstance(tags[key], list) else str(tags[key])
                            break
                    if '(' in title and ')' in title:
                        possible_mix = title.split('(')[-1].split(')')[0]
                        lm = possible_mix.lower()
                        if any(x in lm for x in ["mix", "edit", "dub", "remix"]): meta["mix"] = possible_mix
        except Exception: pass
        return meta

    def get_colour_hex(self, energy):
        if energy == 1: return "0x660099"
        elif energy in [2, 3]: return "0x0000FF"
        elif energy == 4: return "0x25FDE9"
        elif energy == 5: return "0x00FF00"
        elif energy == 6: return "0xFFFF00"
        elif energy == 7: return "0xFFA500"
        elif energy in [8, 9]: return "0xFF0000"
        elif energy == 10: return "0xFF007F"
        return None

    def generate_xml(self):
        save_file = filedialog.asksaveasfilename(defaultextension=".xml", filetypes=[("XML files", "*.xml")], initialfile="rekordbox_import.xml")
        if not save_file: return
        
        root_node = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
        ET.SubElement(root_node, "PRODUCT", Name="rekordbox", Version="7.2.0", Vendor="PioneerDJ")
        collection_xml = ET.SubElement(root_node, "COLLECTION", Entries="0")
        playlists_root = ET.SubElement(root_node, "PLAYLISTS")
        
        track_id = 1
        total_root_count = 0
        all_roots_nodes = []

        def walk(dir_path):
            nonlocal track_id
            name = os.path.basename(dir_path)
            sub_nodes = []
            tracks_in_node = []
            try:
                entries = sorted(os.listdir(dir_path))
                for entry in entries:
                    full_path = os.path.join(dir_path, entry)
                    if os.path.isdir(full_path):
                        child_folder_node, child_count = walk(full_path)
                        if child_count > 0: sub_nodes.append(child_folder_node)
                    elif os.path.isfile(full_path) and full_path.lower().endswith(AUDIO_EXTENSIONS):
                        stem = os.path.splitext(entry)[0]
                        abs_url = full_path.replace("\\", "/")
                        loc_uri = f"file://localhost/{urllib.parse.quote(abs_url)}".replace("%2F", "/").replace("%3A", ":")
                        meta = self.get_track_metadata(full_path)
                        
                        track_attrs = {"TrackID": str(track_id), "Name": stem, "Location": loc_uri}
                        color_hex = self.get_colour_hex(meta["energy"])
                        if color_hex: track_attrs["Colour"] = color_hex
                        if self.var_grouping.get() and meta["energy"] is not None: track_attrs["Grouping"] = f"Energy {meta['energy']}"
                        if meta["tonality"]: track_attrs["Tonality"] = meta["tonality"]
                        if meta["label"]: track_attrs["Label"] = meta["label"]
                        if meta["remixer"]: track_attrs["Remixer"] = meta["remixer"]
                        if meta["mix"]: track_attrs["Mix"] = meta["mix"]
                        
                        ET.SubElement(collection_xml, "TRACK", **track_attrs)
                        playlist_track = ET.Element("TRACK", Key=str(track_id))
                        tracks_in_node.append(playlist_track)
                        track_id += 1
            except Exception: pass
                
            folder_child_count = len(sub_nodes)
            playlist_node_xml = None
            if tracks_in_node:
                playlist_node_xml = ET.Element("NODE", Name=name, Type="1", KeyType="0", Entries=str(len(tracks_in_node)))
                playlist_node_xml.extend(tracks_in_node)
                folder_child_count += 1
            if folder_child_count == 0: return None, 0
                
            folder_node_xml = ET.Element("NODE", Name=name, Type="0", Count=str(folder_child_count))
            folder_node_xml.extend(sub_nodes)
            if playlist_node_xml is not None: folder_node_xml.append(playlist_node_xml)
            return folder_node_xml, folder_child_count

        for folder in self.folder_paths:
            root_folder_node, root_count = walk(folder)
            if root_count > 0:
                all_roots_nodes.append(root_folder_node)
                total_root_count += 1
                
        root_playlist_node = ET.SubElement(playlists_root, "NODE", Name="ROOT", Type="0", Count=str(total_root_count))
        root_playlist_node.extend(all_roots_nodes)
        collection_xml.set("Entries", str(track_id - 1))

        raw_xml = ET.tostring(root_node, 'utf-8')
        reparsed = minidom.parseString(raw_xml)
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")
        
        with open(save_file, "w", encoding="utf-8") as f: f.write(pretty_xml)
        self.status_lbl.configure(text=f"Success! {track_id - 1} tracks processed across {len(self.folder_paths)} folders.", text_color="#4BB543")

if __name__ == "__main__":
    app = RekordboxApp()
    app.mainloop()