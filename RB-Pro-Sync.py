import sys
import os
import shutil
import urllib.parse
import subprocess
import threading
import tkinter.ttk as ttk
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
    """High-performance, collapsible Treeview with Checkboxes and File Metadata."""
    def __init__(self, parent, preview_data):
        super().__init__(parent)
        self.title("👁️ Rekordbox Directory Preview")
        self.geometry("1250x800")
        self.attributes("-topmost", True)
        self.item_mapping = {}
        
        # Action Bar for Bulk Selection
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=15, pady=(15, 0))
        
        self.btn_sel_all = ctk.CTkButton(action_frame, text="☑ Select All", width=140, height=35, font=("Arial", 16), command=lambda: self.set_all(True))
        self.btn_sel_all.pack(side="left", padx=(0, 10))
        
        self.btn_desel_all = ctk.CTkButton(action_frame, text="☐ Deselect All", width=140, height=35, font=("Arial", 16), fg_color="#5a5a5a", hover_color="#404040", command=lambda: self.set_all(False))
        self.btn_desel_all.pack(side="left")
        
        lbl_hint = ctk.CTkLabel(action_frame, text="Click the 'Sync' column to toggle tracks or entire folders.", text_color="gray", font=("Arial", 16, "italic"))
        lbl_hint.pack(side="right")
        
        # Super-scaled typography for ultimate readability, unified with main window
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0, rowheight=40, font=("Arial", 16)) 
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="white", font=("Arial", 16, "bold")) 
        style.map("Treeview", background=[('selected', '#3a7ebf')])

        # Build Columns
        self.tree = ttk.Treeview(self, columns=("Sync", "Artist", "Energy", "Type", "Bitrate", "Length"), selectmode="none")
        self.tree.heading("#0", text="📁 Playlist / 🎵 Title", anchor="w")
        self.tree.heading("Sync", text="Sync", anchor="center")
        self.tree.heading("Artist", text="Artist", anchor="w")
        self.tree.heading("Energy", text="Energy", anchor="w")
        self.tree.heading("Type", text="Type", anchor="center")
        self.tree.heading("Bitrate", text="Bitrate", anchor="w")
        self.tree.heading("Length", text="Length", anchor="w")
        
        self.tree.column("#0", width=420)
        self.tree.column("Sync", width=80, anchor="center")
        self.tree.column("Artist", width=250)
        self.tree.column("Energy", width=120)
        self.tree.column("Type", width=90, anchor="center")
        self.tree.column("Bitrate", width=120)
        self.tree.column("Length", width=100)
        self.tree.pack(fill="both", expand=True, padx=15, pady=15)

        self.tree.bind("<ButtonRelease-1>", self.on_click)

        colors = {
            1: "#9c42f5", 2: "#4a86e8", 3: "#4a86e8", 4: "#25FDE9",
            5: "#00FF00", 6: "#FFFF00", 7: "#FFA500", 8: "#FF4040",
            9: "#FF4040", 10: "#FF007F"
        }
        for e_lvl, hex_val in colors.items():
            self.tree.tag_configure(f"energy_{e_lvl}", foreground=hex_val)
            
        self.tree.tag_configure("flac_highlight", foreground="#25FDE9")
        # LQ Highlight Tag (Red Background, White Text)
        self.tree.tag_configure("lq_highlight", background="#c42b2b", foreground="white")

        if not preview_data:
            self.tree.insert("", "end", text="No folders queued yet.")
        else:
            for tree_data in preview_data:
                self.insert_node("", tree_data)

    def insert_node(self, parent_id, node):
        cb_char = "☑" if node["checked"] else "☐"
        folder_id = self.tree.insert(parent_id, "end", text=f"📁 {node['name']}", values=(cb_char, "", "", "", "", ""), open=False)
        self.item_mapping[folder_id] = node

        for track in node["direct_tracks"]:
            energy_val = track["energy"]
            is_flac = track.get("is_flac", False)
            is_lq = track.get("is_lq", False)
            energy_str = f"Energy {energy_val}" if energy_val else ""
            
            # Prioritize LQ highlight over energy colours
            if is_lq: tag = ("lq_highlight",)
            elif energy_val: tag = (f"energy_{energy_val}",)
            elif is_flac: tag = ("flac_highlight",)
            else: tag = ()
                
            prefix = ""
            if is_lq: prefix += "[LQ] "
            if is_flac: prefix += "[FLAC] "
            
            t_cb_char = "☑" if track["checked"] else "☐"
            
            t_id = self.tree.insert(folder_id, "end", text=f"🎵 {prefix}{track['title']}", 
                                    values=(t_cb_char, track["artist"], energy_str, track["type"], track["bitrate"], track["length"]), tags=tag)
            self.item_mapping[t_id] = track

        for sub in node["sub_folders"]:
            self.insert_node(folder_id, sub)

    def on_click(self, event):
        item_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if item_id and col == '#1': 
            node_data = self.item_mapping.get(item_id)
            if node_data:
                new_state = not node_data["checked"]
                self.update_state_recursive(item_id, new_state)
                
    def update_state_recursive(self, item_id, state):
        node_data = self.item_mapping[item_id]
        node_data["checked"] = state
        
        vals = list(self.tree.item(item_id, "values"))
        vals[0] = "☑" if state else "☐"
        self.tree.item(item_id, values=vals)
        
        for child_id in self.tree.get_children(item_id):
            self.update_state_recursive(child_id, state)
            
    def set_all(self, state):
        for item_id in self.tree.get_children(""):
            self.update_state_recursive(item_id, state)


class FlacManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent, flac_paths, app_instance):
        super().__init__(parent)
        self.title("🛠️ Pre-Import FLAC Manager")
        self.geometry("900x750")
        self.attributes("-topmost", True)
        self.app_instance = app_instance
        self.flac_paths = flac_paths
        
        self.lbl_title = ctk.CTkLabel(self, text=f"Detected {len(flac_paths)} FLAC Tracks", font=("Arial", 22, "bold"))
        self.lbl_title.pack(pady=(20, 5))
        
        self.lbl_desc = ctk.CTkLabel(self, text="Select files to generate 320kbps MP3 clones directly alongside the originals.\nBoth files will be imported to Rekordbox.", font=("Arial", 16), text_color="gray")
        self.lbl_desc.pack(pady=(0, 15))

        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.checkboxes = {}
        for path in self.flac_paths:
            var = ctk.BooleanVar(value=True)
            chk = ctk.CTkCheckBox(self.scroll_frame, text=os.path.basename(path), variable=var, font=("Arial", 16))
            chk.pack(anchor="w", padx=10, pady=6)
            self.checkboxes[path] = var

        self.txt_console = ctk.CTkTextbox(self, height=140, font=("Courier", 15))
        self.txt_console.pack(fill="x", padx=20, pady=15)
        self.txt_console.configure(state="disabled")

        self.btn_convert = ctk.CTkButton(self, text="🔄 CONVERT SELECTED IN-PLACE", font=("Arial", 20, "bold"), height=50, fg_color="#3a7ebf", hover_color="#275682", command=self.start_conversion)
        self.btn_convert.pack(pady=20)

    def log(self, msg):
        def update():
            self.txt_console.configure(state="normal")
            self.txt_console.insert("end", msg + "\n")
            self.txt_console.see("end")
            self.txt_console.configure(state="disabled")
        self.after(0, update)

    def start_conversion(self):
        self.btn_convert.configure(state="disabled")
        threading.Thread(target=self.process_flacs, daemon=True).start()

    def process_flacs(self):
        ffmpeg_exe = self.app_instance.get_ffmpeg_path()
        if not ffmpeg_exe:
            self.log("❌ ERROR: 'ffmpeg.exe' not found. Cannot convert.")
            self.after(0, lambda: self.btn_convert.configure(state="normal"))
            return

        selected_paths = [path for path, var in self.checkboxes.items() if var.get()]
        if not selected_paths:
            self.log("⚠️ No tracks selected.")
            self.after(0, lambda: self.btn_convert.configure(state="normal"))
            return

        self.log(f"🚀 Starting conversion of {len(selected_paths)} tracks...")

        for idx, f_path in enumerate(selected_paths, 1):
            base_name = os.path.splitext(os.path.basename(f_path))[0]
            parent_dir = os.path.dirname(f_path)
            out_mp3_path = os.path.join(parent_dir, f"{base_name}.mp3")
            
            self.log(f"[{idx}/{len(selected_paths)}] Encoding: {base_name}.mp3")
            meta = self.app_instance.get_track_metadata(f_path)
            
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
                except Exception as e:
                    self.log(f"  ⚠️ Meta warning: {e}")

            except subprocess.CalledProcessError as e:
                self.log(f"❌ Failed: {e.stderr}")
            except Exception as ex:
                self.log(f"❌ Error: {str(ex)}")
                
        self.log("🎉 All conversions complete!")
        self.log("Refreshing Tab 1 Queue to include new MP3s...")
        
        self.after(2000, self.app_instance.rebuild_all_trees)
        self.after(2500, self.destroy)


class ConverterPreviewWindow(ctk.CTkToplevel):
    """High-performance Treeview to preview FLAC tracks queued for conversion (Tab 2)."""
    def __init__(self, parent, track_list, metadata_parser):
        super().__init__(parent)
        self.title("👁️ Tracks Queued for Conversion")
        self.geometry("1150x750")
        self.attributes("-topmost", True)
        
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0, rowheight=40, font=("Arial", 16))
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="white", font=("Arial", 16, "bold"))
        style.map("Treeview", background=[('selected', '#3a7ebf')])

        self.tree = ttk.Treeview(self, columns=("Artist", "Energy", "Type", "Bitrate", "Length"), selectmode="none")
        self.tree.heading("#0", text="🎵 Track Title", anchor="w")
        self.tree.heading("Artist", text="Artist", anchor="w")
        self.tree.heading("Energy", text="Energy", anchor="w")
        self.tree.heading("Type", text="Type", anchor="center")
        self.tree.heading("Bitrate", text="Bitrate", anchor="w")
        self.tree.heading("Length", text="Length", anchor="w")
        
        self.tree.column("#0", width=420)
        self.tree.column("Artist", width=250)
        self.tree.column("Energy", width=120)
        self.tree.column("Type", width=90, anchor="center")
        self.tree.column("Bitrate", width=120)
        self.tree.column("Length", width=100)
        self.tree.pack(fill="both", expand=True, padx=15, pady=15)

        colors = {
            1: "#9c42f5", 2: "#4a86e8", 3: "#4a86e8", 4: "#25FDE9",
            5: "#00FF00", 6: "#FFFF00", 7: "#FFA500", 8: "#FF4040",
            9: "#FF4040", 10: "#FF007F"
        }
        for e_lvl, hex_val in colors.items():
            self.tree.tag_configure(f"energy_{e_lvl}", foreground=hex_val)

        if not track_list:
            self.tree.insert("", "end", text="No valid FLAC tracks found.")
        else:
            for track_path in track_list:
                meta = metadata_parser(track_path)
                title = meta.get("title") or os.path.basename(track_path)
                artist = meta.get("artist") or "Unknown"
                energy_val = meta.get("energy")
                
                energy_str = f"Energy {energy_val}" if energy_val else ""
                tag = (f"energy_{energy_val}",) if energy_val else ()
                
                self.tree.insert("", "end", text=f"🎵 {title}", values=(artist, energy_str, meta["type"], meta["bitrate"], meta["length"]), tags=tag)


class RekordboxApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Rekordbox 7 Pro Sync Suite")
        self.geometry("900x850") 
        self.resizable(True, True)
        self.minsize(800, 750)
        
        self.folder_paths = []
        self.preview_trees = []
        self.detected_flacs = [] 
        self.preview_window = None
        
        self.m3u8_path = ""
        self.m3u8_flac_paths = [] 
        self.converter_preview_window = None
        self.flac_manager_window = None
        
        self.setup_ui()
        
    def setup_ui(self):
        self.heading = ctk.CTkLabel(self, text="Rekordbox 7 Pro Sync Suite v7.8", font=("Arial", 28, "bold"))
        self.heading.pack(pady=(20, 5))
        self.subheading = ctk.CTkLabel(self, text="Advanced Music Pipeline Engine", font=("Arial", 16), text_color="gray")
        self.subheading.pack(pady=(0, 15))
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview._segmented_button.configure(font=("Arial", 16, "bold"))
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.tab_sync = self.tabview.add("📁 Directory XML Sync")
        self.tab_convert = self.tabview.add("🔄 M3U8 FLAC to MP3 Converter")
        
        self.build_sync_tab()
        self.build_converter_tab()

    def create_colour_guide_frame(self, parent_widget):
        guide_frame = ctk.CTkFrame(parent_widget, fg_color="transparent")
        guide_lbl = ctk.CTkLabel(guide_frame, text="Energy Map:", font=("Arial", 16, "bold"), text_color="gray")
        guide_lbl.pack(side="left", padx=(0, 8))
        
        colors = [
            ("1", "#660099", "white"), ("2-3", "#0000FF", "white"), 
            ("4", "#25FDE9", "black"), ("5", "#00FF00", "black"), 
            ("6", "#FFFF00", "black"), ("7", "#FFA500", "black"), 
            ("8-9", "#FF0000", "white"), ("10", "#FF007F", "white")
        ]
        
        for text, hex_val, txt_col in colors:
            chip = ctk.CTkLabel(guide_frame, text=f" {text} ", fg_color=hex_val, text_color=txt_col, font=("Arial", 14, "bold"), corner_radius=6, height=28)
            chip.pack(side="left", padx=3)
            
        return guide_frame

    # =========================================================================
    # TAB 1: DIRECTORY SYNC LOGIC
    # =========================================================================
    def build_sync_tab(self):
        self.src_frame = ctk.CTkFrame(self.tab_sync)
        self.src_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.src_title_frame = ctk.CTkFrame(self.src_frame, fg_color="transparent")
        self.src_title_frame.pack(fill="x", padx=10, pady=5)
        
        self.src_label = ctk.CTkLabel(self.src_title_frame, text="1. Source Selection:", font=("Arial", 16, "bold"))
        self.src_label.pack(side="left")
        
        self.btn_preview = ctk.CTkButton(self.src_title_frame, text="👁️ Show Preview Window", width=180, height=35, font=("Arial", 16), command=self.toggle_preview, state="disabled")
        self.btn_preview.pack(side="right")
        
        btn_action_row = ctk.CTkFrame(self.src_frame, fg_color="transparent")
        btn_action_row.pack(fill="x", padx=10, pady=10)
        
        self.btn_add = ctk.CTkButton(btn_action_row, text="➕ Add Music Folder(s)", height=35, font=("Arial", 16), command=self.add_folders)
        self.btn_add.pack(side="left", padx=(0, 10))
        
        self.btn_manage_flacs = ctk.CTkButton(btn_action_row, text="🛠️ Manage Detected FLACs", height=35, font=("Arial", 16), fg_color="#b86914", hover_color="#8a4d0d", command=self.open_flac_manager, state="disabled")
        self.btn_manage_flacs.pack(side="left")
        
        self.scroll_paths = ctk.CTkScrollableFrame(self.src_frame)
        self.scroll_paths.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.opts_frame = ctk.CTkFrame(self.tab_sync)
        self.opts_frame.pack(fill="x", padx=15, pady=15)
        
        self.opts_label = ctk.CTkLabel(self.opts_frame, text="2. Automation Options:", font=("Arial", 16, "bold"))
        self.opts_label.pack(anchor="w", padx=10, pady=10)
        
        self.var_grouping = ctk.BooleanVar(value=True)
        self.chk_grouping = ctk.CTkCheckBox(self.opts_frame, text="🏷️ Push 'Energy X' to Grouping (Searchable)", variable=self.var_grouping, font=("Arial", 16))
        self.chk_grouping.pack(anchor="w", padx=15, pady=10)
        
        self.colour_guide = self.create_colour_guide_frame(self.opts_frame)
        self.colour_guide.pack(anchor="w", padx=15, pady=(5, 15))
        
        self.btn_generate = ctk.CTkButton(self.tab_sync, text="🚀 GENERATE V7 XML", font=("Arial", 20, "bold"), height=50, fg_color="#2b7337", hover_color="#1e5226", command=self.generate_xml, state="disabled")
        self.btn_generate.pack(pady=15)
        
        self.status_lbl = ctk.CTkLabel(self.tab_sync, text="Ready to sync library to Rekordbox 7", font=("Arial", 16, "bold"), text_color="#4BB543")
        self.status_lbl.pack(pady=5)

    def add_folders(self):
        folder = filedialog.askdirectory()
        if folder:
            folder_abs = os.path.abspath(folder)
            if folder_abs not in self.folder_paths:
                self.status_lbl.configure(text=f"Scanning files and parsing ID3 tags in {os.path.basename(folder_abs)}...", text_color="#FFA500")
                self.update_idletasks()
                
                self.folder_paths.append(folder_abs)
                
                tree_data = self.build_preview_tree(folder_abs)
                if tree_data:
                    self.preview_trees.append(tree_data)
                
                self.refresh_paths_ui()
                self.update_ui_states()

    def rebuild_all_trees(self):
        self.preview_trees = []
        self.detected_flacs = [] 
        
        for folder in self.folder_paths:
            tree_data = self.build_preview_tree(folder)
            if tree_data: 
                self.preview_trees.append(tree_data)
                
        self.refresh_paths_ui()
        self.update_ui_states()
        
    def update_ui_states(self):
        if self.preview_trees:
            self.btn_preview.configure(state="normal")
            self.btn_generate.configure(state="normal")
        else:
            self.btn_preview.configure(state="disabled")
            self.btn_generate.configure(state="disabled")
            
        if self.detected_flacs:
            self.btn_manage_flacs.configure(state="normal", text=f"🛠️ Manage {len(self.detected_flacs)} FLACs")
        else:
            self.btn_manage_flacs.configure(state="disabled", text="🛠️ Manage Detected FLACs")
            
        self.status_lbl.configure(text="Ready to sync library to Rekordbox 7", text_color="#4BB543")
        
        if self.preview_window and self.preview_window.winfo_exists():
            self.open_preview_window()

    def refresh_paths_ui(self):
        for widget in self.scroll_paths.winfo_children(): widget.destroy()
        for idx, path in enumerate(self.folder_paths):
            row = ctk.CTkFrame(self.scroll_paths, fg_color="transparent")
            row.pack(fill="x", pady=2)
            btn_del = ctk.CTkButton(row, text="❌", width=30, height=30, font=("Arial", 16), fg_color="#8b2525", hover_color="#5e1919", command=lambda i=idx: self.remove_folder(i))
            btn_del.pack(side="left", padx=(0, 8))
            lbl = ctk.CTkLabel(row, text=path, font=("Arial", 16))
            lbl.pack(side="left")

    def remove_folder(self, idx):
        self.folder_paths.pop(idx)
        if idx < len(self.preview_trees):
            self.preview_trees.pop(idx)
        self.refresh_paths_ui()
        self.update_ui_states()

    def toggle_preview(self):
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.destroy()
            self.preview_window = None
        else:
            self.open_preview_window()

    def open_preview_window(self):
        if self.preview_window and self.preview_window.winfo_exists(): self.preview_window.destroy()
        self.preview_window = PreviewWindow(self, self.preview_trees)

    def open_flac_manager(self):
        if self.flac_manager_window and self.flac_manager_window.winfo_exists():
            self.flac_manager_window.destroy()
        self.flac_manager_window = FlacManagerWindow(self, self.detected_flacs, self)

    def build_preview_tree(self, dir_path):
        name = os.path.basename(dir_path)
        if not name: return None
        direct_tracks = []
        sub_folders = []
        try:
            entries = sorted(os.listdir(dir_path))
            for entry in entries:
                full_path = os.path.join(dir_path, entry)
                if os.path.isdir(full_path):
                    sub = self.build_preview_tree(full_path)
                    if sub and (sub["direct_tracks"] or sub["sub_folders"]): 
                        sub_folders.append(sub)
                elif os.path.isfile(full_path) and full_path.lower().endswith(AUDIO_EXTENSIONS):
                    meta = self.get_track_metadata(full_path)
                    
                    is_flac = full_path.lower().endswith(".flac")
                    if is_flac and full_path not in self.detected_flacs:
                        self.detected_flacs.append(full_path)
                        
                    direct_tracks.append({
                        "filename": entry,
                        "full_path": full_path,
                        "title": meta.get("title") or os.path.splitext(entry)[0],
                        "artist": meta.get("artist") or "Unknown Artist",
                        "energy": meta["energy"],
                        "tonality": meta["tonality"],
                        "label": meta["label"],
                        "remixer": meta["remixer"],
                        "mix": meta["mix"],
                        "type": meta["type"],
                        "bitrate": meta["bitrate"],
                        "length": meta["length"],
                        "is_flac": is_flac,
                        "is_lq": meta["is_lq"],
                        "checked": True 
                    })
        except Exception: return None
        if direct_tracks or sub_folders:
            return {"name": name, "checked": True, "direct_tracks": direct_tracks, "sub_folders": sub_folders}
        return None

    def get_track_metadata(self, file_path):
        meta = {
            "energy": None, "tonality": None, "label": None, 
            "remixer": None, "mix": None, "title": None, 
            "artist": None, "type": os.path.splitext(file_path)[1][1:].upper(),
            "bitrate": "-", "length": "-", "is_lq": False
        }
        try:
            audio = File(file_path)
            
            # Extract Technical Info
            if audio and hasattr(audio, 'info') and audio.info:
                br = 0
                if hasattr(audio.info, 'bitrate') and audio.info.bitrate:
                    br = int(audio.info.bitrate / 1000)
                    meta["bitrate"] = f"{br} kbps"
                
                if hasattr(audio.info, 'length') and audio.info.length:
                    mins, secs = divmod(int(audio.info.length), 60)
                    meta["length"] = f"{mins}:{secs:02d}"

                # Trigger LQ Warning if MP3 and below strict 320kbps threshold
                if meta["type"] == "MP3" and br > 0 and br < 320:
                    meta["is_lq"] = True

            # Extract Tags
            if audio and audio.tags:
                tags = audio.tags
                for key in ['TPE1', 'artist']:
                    if key in tags:
                        meta["artist"] = str(tags[key][0]) if isinstance(tags[key], list) else str(tags[key])
                        break
                for key in ['TIT2', 'title']:
                    if key in tags:
                        meta["title"] = str(tags[key][0]) if isinstance(tags[key], list) else str(tags[key])
                        break
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

                if meta["mix"] is None and meta["title"]:
                    title = meta["title"]
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

        def build_xml_from_tree(node):
            nonlocal track_id
            if not node["checked"]:
                return None, 0
                
            sub_nodes = []
            tracks_in_node = []
            
            for sub in node["sub_folders"]:
                child_folder_node, child_count = build_xml_from_tree(sub)
                if child_count > 0:
                    sub_nodes.append(child_folder_node)
                    
            for track in node["direct_tracks"]:
                if not track["checked"]:
                    continue
                    
                abs_url = track["full_path"].replace("\\", "/")
                loc_uri = f"file://localhost/{urllib.parse.quote(abs_url)}".replace("%2F", "/").replace("%3A", ":")
                
                track_attrs = {
                    "TrackID": str(track_id),
                    "Name": track.get("title") or track["filename"],
                    "Location": loc_uri
                }
                
                color_hex = self.get_colour_hex(track["energy"])
                if color_hex: track_attrs["Colour"] = color_hex
                if self.var_grouping.get() and track["energy"] is not None: 
                    track_attrs["Grouping"] = f"Energy {track['energy']}"
                if track["tonality"]: track_attrs["Tonality"] = track["tonality"]
                if track["label"]: track_attrs["Label"] = track["label"]
                if track["remixer"]: track_attrs["Remixer"] = track["remixer"]
                if track["mix"]: track_attrs["Mix"] = track["mix"]
                
                ET.SubElement(collection_xml, "TRACK", **track_attrs)
                playlist_track = ET.Element("TRACK", Key=str(track_id))
                tracks_in_node.append(playlist_track)
                track_id += 1
                
            folder_child_count = len(sub_nodes)
            playlist_node_xml = None
            if tracks_in_node:
                playlist_node_xml = ET.Element("NODE", Name=node["name"], Type="1", KeyType="0", Entries=str(len(tracks_in_node)))
                playlist_node_xml.extend(tracks_in_node)
                folder_child_count += 1
                
            if folder_child_count == 0:
                return None, 0
                
            folder_node_xml = ET.Element("NODE", Name=node["name"], Type="0", Count=str(folder_child_count))
            folder_node_xml.extend(sub_nodes)
            if playlist_node_xml is not None:
                folder_node_xml.append(playlist_node_xml)
                
            return folder_node_xml, folder_child_count

        for tree in self.preview_trees:
            root_folder_node, root_count = build_xml_from_tree(tree)
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
        self.status_lbl.configure(text=f"Success! {track_id - 1} tracks included in sync.", text_color="#4BB543")

    # =========================================================================
    # TAB 2: M3U8 FLAC TO MP3 CONVERTER LOGIC
    # =========================================================================
    def build_converter_tab(self):
        conv_frame = ctk.CTkFrame(self.tab_convert)
        conv_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        lbl_desc = ctk.CTkLabel(conv_frame, text="Scan an export playlist (.m3u8), clone FLAC tracks into 320kbps CBR MP3s\nsaved directly alongside the source files, mirror tags, and build an XML mapper.", justify="left", font=("Arial", 16))
        lbl_desc.pack(anchor="w", padx=15, pady=(15, 10))
        
        self.colour_guide_conv = self.create_colour_guide_frame(conv_frame)
        self.colour_guide_conv.pack(anchor="w", padx=15, pady=(0, 20))
        
        self.lbl_m3u8 = ctk.CTkLabel(conv_frame, text="No M3U8 file selected.", text_color="gray", font=("Arial", 15, "italic"))
        
        btn_row = ctk.CTkFrame(conv_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=10)
        
        self.btn_pick_m3u8 = ctk.CTkButton(btn_row, text="📋 Select Playlist M3U8 File", font=("Arial", 16), height=40, command=self.pick_m3u8)
        self.btn_pick_m3u8.pack(side="left", padx=(0, 15))
        
        self.btn_preview_m3u8 = ctk.CTkButton(btn_row, text="👁️ Preview Tracks to Convert", font=("Arial", 16), height=40, command=self.show_m3u8_preview, state="disabled", fg_color="#5a5a5a", hover_color="#404040")
        self.btn_preview_m3u8.pack(side="left")
        
        self.lbl_m3u8.pack(anchor="w", padx=25, pady=(0, 15))
        
        self.txt_console = ctk.CTkTextbox(conv_frame, height=220, font=("Courier", 15))
        self.txt_console.pack(fill="both", expand=True, padx=15, pady=10)
        self.txt_console.configure(state="disabled")
        
        self.btn_convert_pipeline = ctk.CTkButton(self.tab_convert, text="🔄 RUN IN-PLACE FLAC PIPELINE", font=("Arial", 20, "bold"), height=50, fg_color="#3a7ebf", hover_color="#275682", command=self.start_conversion_thread, state="disabled")
        self.btn_convert_pipeline.pack(pady=15)

    def log_to_conv_console(self, msg):
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
            self.log_to_conv_console(f"⚠️ Warning: Could not locate {len(missing_paths)} tracks. Example: {missing_paths[0]}")

    def show_m3u8_preview(self):
        if self.converter_preview_window and self.converter_preview_window.winfo_exists():
            self.converter_preview_window.destroy()
        self.converter_preview_window = ConverterPreviewWindow(self, self.m3u8_flac_paths, self.get_track_metadata)

    def start_conversion_thread(self):
        self.btn_convert_pipeline.configure(state="disabled")
        threading.Thread(target=self.run_m3u8_pipeline, daemon=True).start()

    def get_ffmpeg_path(self):
        if hasattr(sys, '_MEIPASS'):
            bundled_ffmpeg = os.path.join(sys._MEIPASS, 'ffmpeg.exe')
            if os.path.exists(bundled_ffmpeg):
                return bundled_ffmpeg
        if os.path.exists("ffmpeg.exe"):
            return "ffmpeg.exe"
        if shutil.which("ffmpeg"):
            return "ffmpeg"
        return None

    def run_m3u8_pipeline(self):
        ffmpeg_exe = self.get_ffmpeg_path()
        if not ffmpeg_exe:
            self.log_to_conv_console("\n❌ CRITICAL ERROR: 'ffmpeg.exe' was not found.")
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
                except Exception as e:
                    self.log_to_conv_console(f"  ⚠️ ID3 Meta Warning: {str(e)}")

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

if __name__ == "__main__":
    app = RekordboxApp()
    app.mainloop()