import os
import urllib.parse
import xml.etree.ElementTree as ET
from xml.dom import minidom
import customtkinter as ctk
from customtkinter import filedialog
from mutagen import File

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
        
        # Ensure it floats on top
        self.attributes("-topmost", True)
        
        # Scrollable container
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
            # Flat playlist item
            lbl = ctk.CTkLabel(
                parent_widget, 
                text=f"{indent}🎵 {node['name']} ({node['direct_tracks']} tracks)",
                font=("Arial", 12)
            )
            lbl.pack(anchor="w", padx=5, pady=2)
        else:
            # Folder node item
            lbl = ctk.CTkLabel(
                parent_widget, 
                text=f"{indent}📁 {node['name']}",
                font=("Arial", 12, "bold"),
                text_color="#3a7ebf"
            )
            lbl.pack(anchor="w", padx=5, pady=2)
            
            if node["direct_tracks"] > 0:
                root_lbl = ctk.CTkLabel(
                    parent_widget,
                    text=f"{indent}    🎵 {node['name']} [Root Tracks] ({node['direct_tracks']} tracks)",
                    font=("Arial", 11, "italic"),
                    text_color="gray"
                )
                root_lbl.pack(anchor="w", padx=5, pady=1)
                
            for sub in node["sub_folders"]:
                self.render_node(parent_widget, sub, level + 1)


class RekordboxApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Rekordbox 7 Pro Sync (Python)")
        
        # EXPANDED: Increased initial height to 680 to show all elements cleanly
        self.geometry("800x800")
        self.resizable(True, True)
        
        # EXPANDED: Adjusted minimum size to prevent squishing the UI
        self.minsize(650, 580)
        
        self.folder_paths = []
        self.preview_trees = []
        self.preview_window = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        self.heading = ctk.CTkLabel(self, text="Rekordbox 7 Pro Sync v5.4", font=("Arial", 20, "bold"))
        self.heading.pack(pady=(20, 2))
        self.subheading = ctk.CTkLabel(self, text="Python Pipeline Engine", font=("Arial", 12), text_color="gray")
        self.subheading.pack(pady=(0, 10))
        
        # Section 1: Source Selection Frame
        self.src_frame = ctk.CTkFrame(self)
        self.src_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.src_title_frame = ctk.CTkFrame(self.src_frame, fg_color="transparent")
        self.src_title_frame.pack(fill="x", padx=10, pady=5)
        
        self.src_label = ctk.CTkLabel(self.src_title_frame, text="1. Source Selection:", font=("Arial", 13, "bold"))
        self.src_label.pack(side="left")
        
        self.btn_preview = ctk.CTkButton(
            self.src_title_frame, 
            text="👁️ Show Preview Window", 
            width=150, 
            height=24, 
            command=self.toggle_preview, 
            state="disabled"
        )
        self.btn_preview.pack(side="right")
        
        self.btn_add = ctk.CTkButton(self.src_frame, text="➕ Add Music Folder(s)", command=self.add_folders)
        self.btn_add.pack(anchor="w", padx=10, pady=5)
        
        # Scroll area expands to fill empty space
        self.scroll_paths = ctk.CTkScrollableFrame(self.src_frame)
        self.scroll_paths.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Section 2: Automation Frame
        self.opts_frame = ctk.CTkFrame(self)
        self.opts_frame.pack(fill="x", padx=20, pady=10)
        
        self.opts_label = ctk.CTkLabel(self.opts_frame, text="2. Automation Options:", font=("Arial", 13, "bold"))
        self.opts_label.pack(anchor="w", padx=10, pady=5)
        
        self.var_grouping = ctk.BooleanVar(value=True)
        self.chk_grouping = ctk.CTkCheckBox(self.opts_frame, text="🏷️ Push 'Energy X' to Grouping (Searchable)", variable=self.var_grouping)
        self.chk_grouping.pack(anchor="w", padx=15, pady=5)
        
        self.meta_info = ctk.CTkLabel(
            self.opts_frame, 
            text="• Maps Energy (1-10) to strict 0xRRGGBB Hex values\n• Auto-extracts Tonality, Label, Remixer, and Mix fields\n• Features 'Smart Mix Extraction' from Track Titles",
            justify="left", font=("Arial", 11), text_color="gray"
        )
        self.meta_info.pack(anchor="w", padx=15, pady=5)
        
        # Action Zone
        self.btn_generate = ctk.CTkButton(self, text="🚀 GENERATE V7 XML", font=("Arial", 16, "bold"), height=40, fg_color="#2b7337", hover_color="#1e5226", command=self.generate_xml, state="disabled")
        self.btn_generate.pack(pady=15)
        
        # Status Bar
        self.status_sep = ctk.CTkLabel(self, text="________________________________________________________________________", text_color="gray")
        self.status_sep.pack()
        self.status_lbl = ctk.CTkLabel(self, text="Ready to sync library to Rekordbox 7", font=("Arial", 12, "bold"), text_color="#4BB543")
        self.status_lbl.pack(pady=(5, 15))

    def add_folders(self):
        folder = filedialog.askdirectory()
        if folder:
            folder_abs = os.path.abspath(folder)
            if folder_abs not in self.folder_paths:
                self.folder_paths.append(folder_abs)
                self.refresh_paths_ui()
                
                # Build preview data
                tree_data = self.build_preview_tree(folder_abs)
                if tree_data:
                    self.preview_trees.append(tree_data)
                
                # Dynamic UI shifts
                self.btn_preview.configure(state="normal")
                self.btn_generate.configure(state="normal")
                
                # Auto pop-up window
                self.open_preview_window()

    def refresh_paths_ui(self):
        # Clear old items
        for widget in self.scroll_paths.winfo_children():
            widget.destroy()
            
        for idx, path in enumerate(self.folder_paths):
            row = ctk.CTkFrame(self.scroll_paths, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            btn_del = ctk.CTkButton(row, text="❌", width=24, height=24, fg_color="#8b2525", hover_color="#5e1919", command=lambda i=idx: self.remove_folder(i))
            btn_del.pack(side="left", padx=(0, 5))
            
            lbl = ctk.CTkLabel(row, text=path, font=("Arial", 11))
            lbl.pack(side="left")

    def remove_folder(self, idx):
        self.folder_paths.pop(idx)
        if idx < len(self.preview_trees):
            self.preview_trees.pop(idx)
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
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.destroy()
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
                    if sub and (sub["direct_tracks"] > 0 or sub["sub_folders"]):
                        sub_folders.append(sub)
                elif os.path.isfile(full_path) and full_path.lower().endswith(AUDIO_EXTENSIONS):
                    direct_tracks += 1
        except Exception:
            return None
            
        if direct_tracks > 0 or sub_folders:
            return {"name": name, "direct_tracks": direct_tracks, "sub_folders": sub_folders}
        return None

    def get_track_metadata(self, file_path):
        meta = {"energy": None, "tonality": None, "label": None, "remixer": None, "mix": None}
        try:
            audio = File(file_path)
            if audio and audio.tags:
                tags = audio.tags
                
                # Check for InitialKey/Tonality
                for key in ['TKEY', 'initialkey']:
                    if key in tags:
                        meta["tonality"] = str(tags[key][0]) if isinstance(tags[key], list) else str(tags[key])
                        break
                        
                # Check for Label/Publisher
                for key in ['TPUB', 'publisher', 'label']:
                    if key in tags:
                        meta["label"] = str(tags[key][0]) if isinstance(tags[key], list) else str(tags[key])
                        break

                # Check for Remixer
                for key in ['TPE4', 'remixer']:
                    if key in tags:
                        meta["remixer"] = str(tags[key][0]) if isinstance(tags[key], list) else str(tags[key])
                        break

                # Check for Mix version (Subtitle)
                for key in ['TIT3', 'subtitle']:
                    if key in tags:
                        meta["mix"] = str(tags[key][0]) if isinstance(tags[key], list) else str(tags[key])
                        break

                # Parse Grouping field (TIT1 or equivalent) for Energy
                grouping_text = ""
                for key in ['TIT1', 'grouping', 'CONTENTGROUP']:
                    if key in tags:
                        grouping_text = str(tags[key][0]).lower() if isinstance(tags[key], list) else str(tags[key]).lower()
                        break
                        
                if "energy" in grouping_text:
                    digits = "".join([c for c in grouping_text.split("energy")[-1] if c.isdigit()])
                    if digits: meta["energy"] = int(digits)

                # Fallback to Comment parser for Energy
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
                        if digits and 0 < int(digits) <= 10:
                            meta["energy"] = int(digits)

                # Fallback smart extraction from Title string parenthesis
                if meta["mix"] is None and 'TIT2' in tags:
                    title = str(tags['TIT2'][0]) if isinstance(tags['TIT2'], list) else str(tags['TIT2'])
                    if '(' in title and ')' in title:
                        possible_mix = title.split('(')[-1].split(')')[0]
                        lm = possible_mix.lower()
                        if any(x in lm for x in ["mix", "edit", "dub", "remix"]):
                            meta["mix"] = possible_mix
        except Exception:
            pass
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
                        if child_count > 0:
                            sub_nodes.append(child_folder_node)
                    elif os.path.isfile(full_path) and full_path.lower().endswith(AUDIO_EXTENSIONS):
                        stem = os.path.splitext(entry)[0]
                        
                        abs_url = full_path.replace("\\", "/")
                        loc_uri = f"file://localhost/{urllib.parse.quote(abs_url)}".replace("%2F", "/").replace("%3A", ":")
                        
                        meta = self.get_track_metadata(full_path)
                        
                        track_attrs = {
                            "TrackID": str(track_id),
                            "Name": stem,
                            "Location": loc_uri
                        }
                        
                        color_hex = self.get_colour_hex(meta["energy"])
                        if color_hex:
                            track_attrs["Colour"] = color_hex
                            
                        if self.var_grouping.get() and meta["energy"] is not None:
                            track_attrs["Grouping"] = f"Energy {meta['energy']}"
                            
                        if meta["tonality"]: track_attrs["Tonality"] = meta["tonality"]
                        if meta["label"]: track_attrs["Label"] = meta["label"]
                        if meta["remixer"]: track_attrs["Remixer"] = meta["remixer"]
                        if meta["mix"]: track_attrs["Mix"] = meta["mix"]
                        
                        ET.SubElement(collection_xml, "TRACK", **track_attrs)
                        
                        playlist_track = ET.Element("TRACK", Key=str(track_id))
                        tracks_in_node.append(playlist_track)
                        track_id += 1
            except Exception:
                pass
                
            folder_child_count = len(sub_nodes)
            playlist_node_xml = None
            if tracks_in_node:
                playlist_node_xml = ET.Element("NODE", Name=name, Type="1", KeyType="0", Entries=str(len(tracks_in_node)))
                playlist_node_xml.extend(tracks_in_node)
                folder_child_count += 1
                
            if folder_child_count == 0:
                return None, 0
                
            folder_node_xml = ET.Element("NODE", Name=name, Type="0", Count=str(folder_child_count))
            folder_node_xml.extend(sub_nodes)
            if playlist_node_xml is not None:
                folder_node_xml.append(playlist_node_xml)
                
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
        
        with open(save_file, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
            
        self.status_lbl.configure(text=f"Success! {track_id - 1} tracks processed across {len(self.folder_paths)} folders.", text_color="#4BB543")

if __name__ == "__main__":
    app = RekordboxApp()
    app.mainloop()