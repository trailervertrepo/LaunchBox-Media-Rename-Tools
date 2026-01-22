"""
ROM Video Renamer v1.1 - TrailerVert Edition
Dedicated tool for renaming LaunchBox video files to match ROM names.
Supports rename-in-place (fast) or move-to-output (organized) modes.
Professional TrailerVert branding with arcade cabinet logo.
"""

import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import re
import xml.etree.ElementTree as ET

try:
    from rapidfuzz import fuzz, process
except ImportError:
    messagebox.showerror("Missing Dependency", 
                        "Please install rapidfuzz:\npip install rapidfuzz")
    exit(1)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


class ROMVideoRenamer:
    def __init__(self):
        self.xml_file = ""
        self.rom_folder = ""
        self.platform_video_folder = ""
        self.output_folder = ""
        self.threshold = 85
        self.video_mode = "rename"  # "rename" or "move"
        self.use_platform_subfolder = True
        self.platform_name = ""
        
        # Statistics
        self.stats = {
            'roms_found': 0,
            'videos_found': 0,
            'videos_matched': 0,
            'videos_unmatched': 0
        }
        
        # Data storage
        self.roms = {}  # {rom_name_no_ext: full_path}
        self.xml_mapping = {}  # {sanitized_title: rom_filename_no_ext}
        self.video_matches = {}  # {video_path: (rom_name, video_type_folder)}
        self.unmatched_videos = []
        self.available_video_types = []
        
        # Video extensions
        self.video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
        
        # Progress callback
        self.progress_callback = None
    
    def sanitize_title(self, title: str) -> str:
        """Sanitize title the way LaunchBox does for filenames"""
        sanitized = title.replace(':', '_')
        sanitized = sanitized.replace("'", '_')
        sanitized = sanitized.replace('/', '_')
        sanitized = sanitized.replace('\\', '_')
        sanitized = sanitized.replace('?', '_')
        sanitized = sanitized.replace('*', '_')
        sanitized = sanitized.replace('"', '_')
        sanitized = sanitized.replace('<', '_')
        sanitized = sanitized.replace('>', '_')
        sanitized = sanitized.replace('|', '_')
        return sanitized
    
    def extract_platform_name(self) -> str:
        """Extract platform name from XML filename"""
        if not self.xml_file:
            return ""
        xml_filename = os.path.basename(self.xml_file)
        platform_name = Path(xml_filename).stem
        return platform_name
    
    def parse_xml(self) -> Dict[str, str]:
        """Parse LaunchBox XML and create Title -> ROM filename mapping"""
        mapping = {}
        
        if not self.xml_file or not os.path.exists(self.xml_file):
            return mapping
        
        try:
            tree = ET.parse(self.xml_file)
            root = tree.getroot()
            
            for game in root.findall('Game'):
                title_elem = game.find('Title')
                app_path_elem = game.find('ApplicationPath')
                
                if title_elem is not None and app_path_elem is not None:
                    title = title_elem.text
                    app_path = app_path_elem.text
                    
                    if title and app_path:
                        rom_filename = os.path.basename(app_path)
                        rom_name_no_ext = Path(rom_filename).stem
                        sanitized_title = self.sanitize_title(title)
                        mapping[sanitized_title] = rom_name_no_ext
            
            return mapping
        except Exception as e:
            print(f"Error parsing XML: {e}")
            return mapping
    
    def scan_roms(self) -> Dict[str, str]:
        """Scan ROM folder and return dict of {name: path}
        Supports both single-file and multi-file ROM systems (.bin/.cue, .gdi)
        """
        roms = {}
        if not os.path.exists(self.rom_folder):
            return roms
        
        multi_file_extensions = {'.bin', '.gdi'}
        
        for item in os.listdir(self.rom_folder):
            item_path = os.path.join(self.rom_folder, item)
            
            if os.path.isfile(item_path):
                name_no_ext = Path(item).stem
                roms[name_no_ext] = item_path
            elif os.path.isdir(item_path):
                for subfile in os.listdir(item_path):
                    subfile_path = os.path.join(item_path, subfile)
                    if os.path.isfile(subfile_path):
                        ext = Path(subfile).suffix.lower()
                        if ext in multi_file_extensions:
                            name_no_ext = Path(subfile).stem
                            roms[name_no_ext] = subfile_path
                            break
        
        return roms
    
    def scan_video_types(self) -> List[str]:
        """Scan platform video folder and return list of video type folders"""
        types = []
        
        if not os.path.exists(self.platform_video_folder):
            return types
        
        # Check if root folder itself has videos (LaunchBox default dump location)
        root_has_videos = False
        for file in os.listdir(self.platform_video_folder):
            file_path = os.path.join(self.platform_video_folder, file)
            if os.path.isfile(file_path):
                ext = Path(file).suffix.lower()
                if ext in self.video_extensions:
                    root_has_videos = True
                    break
        
        if root_has_videos:
            types.append("Root")  # Special type for root folder
        
        # Scan subfolders
        for item in os.listdir(self.platform_video_folder):
            item_path = os.path.join(self.platform_video_folder, item)
            if os.path.isdir(item_path):
                if self.has_videos_recursive(item_path):
                    types.append(item)
        
        return sorted(types)
    
    def has_videos_recursive(self, folder: str) -> bool:
        """Check if folder contains any videos (recursively)"""
        for root, dirs, files in os.walk(folder):
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in self.video_extensions:
                    return True
        return False
    
    def scan_videos_in_type_folder(self, type_folder_path: str) -> Dict[str, str]:
        """Scan a specific video type folder recursively, return {name_no_ext: full_path}"""
        videos = {}
        
        # Special handling for "Root" type - scan only root folder, not recursively
        if type_folder_path == self.platform_video_folder or os.path.basename(type_folder_path) == "Root":
            for file in os.listdir(self.platform_video_folder):
                file_path = os.path.join(self.platform_video_folder, file)
                if os.path.isfile(file_path):
                    ext = Path(file).suffix.lower()
                    if ext in self.video_extensions:
                        name_no_ext = Path(file).stem
                        base_name = re.sub(r'-\d+$', '', name_no_ext)
                        videos[name_no_ext] = file_path
            return videos
        
        # Normal recursive scan for subfolders
        for root, dirs, files in os.walk(type_folder_path):
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in self.video_extensions:
                    file_path = os.path.join(root, file)
                    name_no_ext = Path(file).stem
                    base_name = re.sub(r'-\d+$', '', name_no_ext)
                    videos[name_no_ext] = file_path
        
        return videos
    
    def normalize_name(self, name: str) -> str:
        """Normalize filename for fuzzy comparison"""
        name = Path(name).stem
        name = re.sub(r'-\d+$', '', name)
        name = name.replace('_', ' ')
        name = ' '.join(name.split())
        return name
    
    def get_core_name(self, name: str) -> str:
        """Get core game name without region tags for matching"""
        core = re.sub(r'\([^)]*\)', '', name)
        core = re.sub(r'\[[^\]]*\]', '', core)
        core = core.strip()
        return core
    
    def is_usa_rom(self, rom_name: str) -> bool:
        """Check if ROM is USA region"""
        return '(USA)' in rom_name or '(U)' in rom_name
    
    def match_video_to_rom_xml(self, vid_name: str) -> Optional[str]:
        """Try to match video to ROM using XML mapping"""
        if not self.xml_mapping:
            return None
        
        base_name = re.sub(r'-\d+$', '', vid_name)
        
        if base_name in self.xml_mapping:
            return self.xml_mapping[base_name]
        
        return None
    
    def match_video_to_rom_exact(self, vid_name: str, rom_names: List[str]) -> Optional[str]:
        """Try to match video to ROM by exact name"""
        base_name = re.sub(r'-\d+$', '', vid_name)
        
        if base_name in rom_names:
            return base_name
        
        return None
    
    def match_video_to_rom_fuzzy(self, vid_name: str, rom_names: List[str]) -> Tuple[Optional[str], float]:
        """Try to match video to ROM using fuzzy matching"""
        normalized_video = self.normalize_name(vid_name)
        core_video = self.get_core_name(normalized_video)
        
        rom_choices = []
        for rom in rom_names:
            normalized_rom = self.normalize_name(rom)
            rom_choices.append((normalized_rom, rom))
        
        matches = []
        for normalized_rom, original_rom in rom_choices:
            core_rom = self.get_core_name(normalized_rom)
            
            score1 = fuzz.ratio(normalized_video, normalized_rom)
            score2 = fuzz.ratio(core_video, core_rom)
            score3 = fuzz.partial_ratio(normalized_video, normalized_rom)
            
            best_score = max(score1, score2, score3)
            
            if best_score >= self.threshold:
                matches.append((original_rom, best_score))
        
        if not matches:
            return None, 0
        
        usa_matches = [m for m in matches if self.is_usa_rom(m[0])]
        if usa_matches:
            usa_matches.sort(key=lambda x: x[1], reverse=True)
            return usa_matches[0]
        
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[0]
    
    def match_videos_to_roms(self, video_type: str, videos: Dict[str, str]):
        """Match videos in a specific type folder to ROMs"""
        rom_names = list(self.roms.keys()) if self.roms else []
        
        for vid_name, vid_path in videos.items():
            matched_rom = None
            
            # Try XML matching first
            matched_rom = self.match_video_to_rom_xml(vid_name)
            
            # Try exact ROM name match
            if not matched_rom and rom_names:
                matched_rom = self.match_video_to_rom_exact(vid_name, rom_names)
            
            # Fallback to fuzzy matching
            if not matched_rom and rom_names:
                matched_rom, score = self.match_video_to_rom_fuzzy(vid_name, rom_names)
                if not (matched_rom and score >= self.threshold):
                    matched_rom = None
            
            if matched_rom:
                self.video_matches[vid_path] = (matched_rom, video_type)
                self.stats['videos_matched'] += 1
            else:
                self.unmatched_videos.append((vid_path, video_type))
                self.stats['videos_unmatched'] += 1
    
    def execute_processing(self, video_types_to_process: List[str]) -> Tuple[str, str]:
        """Execute the video processing workflow"""
        log_lines = []
        log_lines.append(f"ROM Video Renamer v1.1 - TrailerVert Edition")
        log_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_lines.append("=" * 70)
        
        # Calculate progress steps
        total_steps = 0
        if self.xml_file:
            total_steps += 1
        if self.rom_folder:
            total_steps += 1
        total_steps += len(video_types_to_process) * 2  # scan + match
        total_steps += 1  # process files
        
        current_step = 0
        
        def update_progress(status_text):
            nonlocal current_step
            current_step += 1
            if self.progress_callback:
                progress_pct = int((current_step / total_steps) * 100) if total_steps > 0 else 0
                self.progress_callback(progress_pct, status_text)
        
        # Parse XML if provided
        if self.xml_file:
            update_progress("Parsing XML...")
            log_lines.append(f"\n--- XML PARSING ---")
            log_lines.append(f"XML File: {os.path.basename(self.xml_file)}")
            self.xml_mapping = self.parse_xml()
            log_lines.append(f"Title-to-ROM mappings loaded: {len(self.xml_mapping)}")
            
            self.platform_name = self.extract_platform_name()
            if self.use_platform_subfolder and self.platform_name:
                log_lines.append(f"Platform: {self.platform_name}")
        
        # Scan ROMs if folder provided
        if self.rom_folder:
            update_progress("Scanning ROMs...")
            log_lines.append(f"\n--- ROM SCANNING ---")
            log_lines.append(f"ROM Folder: {self.rom_folder}")
            self.roms = self.scan_roms()
            self.stats['roms_found'] = len(self.roms)
            log_lines.append(f"ROMs found: {self.stats['roms_found']}")
        
        # Process each video type
        for idx, video_type in enumerate(video_types_to_process):
            update_progress(f"Scanning videos: {video_type}...")
            log_lines.append(f"\n{'=' * 70}")
            log_lines.append(f"--- PROCESSING VIDEO TYPE: {video_type} ---")
            
            # Handle Root specially - use platform video folder itself
            if video_type == "Root":
                type_folder_path = self.platform_video_folder
            else:
                type_folder_path = os.path.join(self.platform_video_folder, video_type)
            
            videos = self.scan_videos_in_type_folder(type_folder_path)
            
            log_lines.append(f"Videos found: {len(videos)}")
            self.stats['videos_found'] += len(videos)
            
            update_progress(f"Matching videos: {video_type} ({idx+1}/{len(video_types_to_process)})...")
            self.match_videos_to_roms(video_type, videos)
        
        update_progress("Processing video files...")
        
        # Process matched videos
        log_lines.append(f"\n{'=' * 70}")
        log_lines.append("\n--- MATCHED AND RENAMED ---")
        
        for vid_path, (rom_name, video_type) in self.video_matches.items():
            vid_ext = Path(vid_path).suffix
            new_name = f"{rom_name}{vid_ext}"
            
            if self.video_mode == "rename":
                # Rename in place
                vid_dir = os.path.dirname(vid_path)
                new_path = os.path.join(vid_dir, new_name)
                
                try:
                    os.rename(vid_path, new_path)
                    log_lines.append(f"✓ [VIDEO-{video_type}] Renamed: {Path(vid_path).name} → {new_name}")
                except Exception as e:
                    log_lines.append(f"✗ [VIDEO-{video_type}] Error renaming {Path(vid_path).name}: {e}")
                    
            else:  # move mode
                # Move to output folder with optional platform subfolder
                if self.use_platform_subfolder and self.platform_name:
                    # Handle root videos specially - they go directly in Videos/ folder
                    if video_type == "Root":
                        output_type_folder = os.path.join(self.output_folder, self.platform_name, "Videos")
                    else:
                        output_type_folder = os.path.join(self.output_folder, self.platform_name, "Videos", video_type)
                else:
                    # Handle root videos specially - they go directly in Videos/ folder
                    if video_type == "Root":
                        output_type_folder = os.path.join(self.output_folder, "Videos")
                    else:
                        output_type_folder = os.path.join(self.output_folder, "Videos", video_type)
                os.makedirs(output_type_folder, exist_ok=True)
                
                new_path = os.path.join(output_type_folder, new_name)
                
                try:
                    shutil.move(vid_path, new_path)
                    log_lines.append(f"✓ [VIDEO-{video_type}] Moved: {Path(vid_path).name} → {new_name}")
                except Exception as e:
                    log_lines.append(f"✗ [VIDEO-{video_type}] Error moving {Path(vid_path).name}: {e}")
        
        # Unmatched videos
        if self.unmatched_videos:
            log_lines.append(f"\n--- UNMATCHED VIDEOS ---")
            for vid_path, video_type in self.unmatched_videos:
                log_lines.append(f"⚠ [{video_type}] {Path(vid_path).name}")
        
        update_progress("Finalizing...")
        
        # Summary
        log_lines.append("\n" + "=" * 70)
        log_lines.append("--- SUMMARY ---")
        if self.xml_file:
            log_lines.append(f"XML mappings loaded: {len(self.xml_mapping)}")
        if self.roms:
            log_lines.append(f"Total ROMs found: {self.stats['roms_found']}")
        log_lines.append(f"Total videos found: {self.stats['videos_found']}")
        log_lines.append(f"Video types processed: {len(video_types_to_process)}")
        log_lines.append(f"Videos matched: {self.stats['videos_matched']}")
        log_lines.append(f"Videos unmatched: {self.stats['videos_unmatched']}")
        log_lines.append(f"Mode: {self.video_mode}")
        
        log_content = "\n".join(log_lines)
        
        # Save log file
        if self.video_mode == "move":
            log_folder = self.output_folder
        else:
            log_folder = self.platform_video_folder
        
        log_path = os.path.join(log_folder, 
                               f"video_processing_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        return log_content, log_path


class ROMVideoRenamerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ROM Video Renamer v1.1 - TrailerVert Edition")

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        width  = int(screen_w * 0.50)
        height = int(screen_h * 0.80)

        x = (screen_w - width) // 2
        y = (screen_h - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(width, height)

        self.root.resizable(True, True)
        
        self.renamer = ROMVideoRenamer()
        
        # Progress tracking
        self.progress_var = tk.IntVar(value=0)
        self.status_text_var = tk.StringVar(value="")
        
        self.create_widgets()


            
    def create_widgets(self):
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # TrailerVert Branding (v1.1)
        branding_frame = ttk.Frame(main_frame)
        branding_frame.grid(row=row, column=0, columnspan=3, pady=(0, 15))
        
        # Try to load logo
        try:
            logo_path = resource_path('logo.png')
            
            if os.path.exists(logo_path):
                logo_img = tk.PhotoImage(file=logo_path)
                # Resize logo
                subsample_x = max(1, logo_img.width() // 48)
                subsample_y = max(1, logo_img.height() // 48)
                logo_img = logo_img.subsample(subsample_x, subsample_y)
                logo_label = ttk.Label(branding_frame, image=logo_img)
                logo_label.image = logo_img  # Keep reference
                logo_label.pack(side=tk.LEFT, padx=(0, 10))
        except Exception:
            pass  # Continue without logo if it fails
        
        # Title and subtitle
        title_container = ttk.Frame(branding_frame)
        title_container.pack(side=tk.LEFT)
        
        title_label = ttk.Label(title_container, text="ROM Video Renamer v1.1", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(anchor=tk.W)
        
        subtitle_label = ttk.Label(title_container, text="TrailerVert Edition", 
                                   font=('Arial', 10, 'italic'),
                                   foreground='#666666')
        subtitle_label.pack(anchor=tk.W)
        
        row = 1
        
        # Platform XML (Optional)
        ttk.Label(main_frame, text="Platform XML: (Optional)").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.xml_file_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.xml_file_var, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_xml_file).grid(row=row, column=2)
        row += 1
        
        # ROM Folder (Optional if XML)
        ttk.Label(main_frame, text="ROM Folder: (Optional if XML)").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.rom_folder_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.rom_folder_var, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_rom_folder).grid(row=row, column=2)
        row += 1
        
        # Platform Video Folder
        ttk.Label(main_frame, text="Platform Video Folder:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.platform_video_folder_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.platform_video_folder_var, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_platform_video_folder).grid(row=row, column=2)
        row += 1
        
        # Output Folder (only for move mode)
        ttk.Label(main_frame, text="Output Folder: (For move mode)").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.output_folder_var = tk.StringVar()
        self.output_entry = ttk.Entry(main_frame, textvariable=self.output_folder_var, width=50, state=tk.DISABLED)
        self.output_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        self.output_browse_btn = ttk.Button(main_frame, text="Browse...", command=self.browse_output_folder, state=tk.DISABLED)
        self.output_browse_btn.grid(row=row, column=2)
        row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)
        row += 1
        
        # Video Mode Selection
        mode_frame = ttk.LabelFrame(main_frame, text="Video Processing Mode", padding="10")
        mode_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.video_mode_var = tk.StringVar(value="rename")
        
        rename_radio = ttk.Radiobutton(mode_frame, 
                                       text="Rename in place (recommended - fast, no copying)", 
                                       variable=self.video_mode_var, 
                                       value="rename",
                                       command=self.on_mode_change)
        rename_radio.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        move_radio = ttk.Radiobutton(mode_frame, 
                                     text="Move to output folder (for reorganization)", 
                                     variable=self.video_mode_var, 
                                     value="move",
                                     command=self.on_mode_change)
        move_radio.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        row += 1
        
        # Scan button
        scan_frame = ttk.Frame(main_frame)
        scan_frame.grid(row=row, column=0, columnspan=3, pady=10)
        
        self.scan_button = ttk.Button(scan_frame, text="Scan Video Types", 
                                      command=self.scan_video_types)
        self.scan_button.pack()
        row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)
        row += 1
        
        # Threshold slider
        threshold_frame = ttk.Frame(main_frame)
        threshold_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(threshold_frame, text="Match Threshold:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(threshold_frame, text="(Used only if XML not provided)", 
                 font=('Arial', 8, 'italic')).pack(side=tk.LEFT, padx=(0, 10))
        self.threshold_var = tk.IntVar(value=85)
        self.threshold_slider = ttk.Scale(threshold_frame, from_=60, to=100, 
                                         variable=self.threshold_var, orient=tk.HORIZONTAL, length=200)
        self.threshold_slider.pack(side=tk.LEFT, padx=5)
        self.threshold_label = ttk.Label(threshold_frame, text="85%")
        self.threshold_label.pack(side=tk.LEFT, padx=5)
        
        self.threshold_slider.configure(command=self.update_threshold_label)
        row += 1
        
        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="5")
        options_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.use_platform_subfolder_var = tk.BooleanVar(value=True)
        self.platform_subfolder_check = ttk.Checkbutton(options_frame, 
                                                        text="Create platform subfolder in output (safer for bulk processing)", 
                                                        variable=self.use_platform_subfolder_var,
                                                        state=tk.DISABLED)
        self.platform_subfolder_check.pack(anchor=tk.W)
        row += 1
        
        # Process button
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=15)
        
        self.process_button = ttk.Button(button_frame, text="Start Processing", 
                                        command=self.start_processing, state=tk.DISABLED)
        self.process_button.pack()
        row += 1
        
        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        results_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(row, weight=1)
        
        # Progress bar
        progress_container = ttk.Frame(results_frame)
        progress_container.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_container, variable=self.progress_var, 
                                           maximum=100, mode='determinate', length=400)
        self.progress_bar.pack(fill=tk.X)
        
        self.status_label = ttk.Label(progress_container, textvariable=self.status_text_var,
                                     font=('Arial', 9))
        self.status_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Results text area
        self.results_text = scrolledtext.ScrolledText(results_frame, height=10, wrap=tk.WORD)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        row += 1
        
        # View log button
        self.view_log_button = ttk.Button(main_frame, text="View Full Log", 
                                         command=self.view_log, state=tk.DISABLED)
        self.view_log_button.grid(row=row, column=0, columnspan=3, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=row+1, column=0, columnspan=3, sticky=(tk.W, tk.E))
    
    def on_mode_change(self):
        """Enable/disable output folder based on mode"""
        if self.video_mode_var.get() == "move":
            self.output_entry.config(state=tk.NORMAL)
            self.output_browse_btn.config(state=tk.NORMAL)
            self.platform_subfolder_check.config(state=tk.NORMAL)
        else:
            self.output_entry.config(state=tk.DISABLED)
            self.output_browse_btn.config(state=tk.DISABLED)
            self.platform_subfolder_check.config(state=tk.DISABLED)
    
    def update_threshold_label(self, value):
        """Update threshold label when slider moves"""
        self.threshold_label.config(text=f"{int(float(value))}%")
    
    def browse_xml_file(self):
        file = filedialog.askopenfilename(title="Select Platform XML", 
                                         filetypes=[("XML files", "*.xml"), ("All files", "*.*")])
        if file:
            self.xml_file_var.set(file)
    
    def browse_rom_folder(self):
        folder = filedialog.askdirectory(title="Select ROM Folder")
        if folder:
            self.rom_folder_var.set(folder)
    
    def browse_platform_video_folder(self):
        folder = filedialog.askdirectory(title="Select Platform Video Folder")
        if folder:
            self.platform_video_folder_var.set(folder)
    
    def browse_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder_var.set(folder)
    
    def scan_video_types(self):
        """Scan platform video folder for available video types"""
        if not self.platform_video_folder_var.get():
            messagebox.showerror("Error", "Please select a Platform Video Folder first")
            return
        
        self.renamer.platform_video_folder = self.platform_video_folder_var.get()
        
        self.status_var.set("Scanning for video types...")
        self.status_text_var.set("Scanning folders...")
        self.root.update()
        
        video_types = self.renamer.scan_video_types()
        
        if not video_types:
            messagebox.showwarning("No Video Types", "No video type folders found with videos")
            self.status_var.set("No video types found")
            return
        
        self.renamer.available_video_types = video_types
        
        # Display results
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"Video types found: {len(video_types)}\n\n")
        self.results_text.insert(tk.END, "Available video types:\n")
        for vid_type in video_types:
            self.results_text.insert(tk.END, f"  • {vid_type}\n")
        
        self.process_button.config(state=tk.NORMAL)
        self.status_var.set(f"Found {len(video_types)} video types. Ready to process.")
        self.status_text_var.set("")
    
    def start_processing(self):
        """Start the video processing workflow"""
        # Validate inputs
        if not self.platform_video_folder_var.get():
            messagebox.showerror("Error", "Please select a Platform Video Folder")
            return
        
        if self.video_mode_var.get() == "move" and not self.output_folder_var.get():
            messagebox.showerror("Error", "Please select an Output Folder for move mode")
            return
        
        if not self.xml_file_var.get() and not self.rom_folder_var.get():
            messagebox.showerror("Error", "Please provide either a Platform XML or ROM Folder")
            return
        
        if not self.renamer.available_video_types:
            messagebox.showerror("Error", "Please scan for video types first")
            return
        
        video_types_to_process = self.renamer.available_video_types
        
        # Confirm with user
        msg = f"Ready to process {len(video_types_to_process)} video type(s).\n\n"
        msg += "Video types:\n"
        for vid_type in video_types_to_process[:5]:
            msg += f"  • {vid_type}\n"
        if len(video_types_to_process) > 5:
            msg += f"  ... and {len(video_types_to_process) - 5} more\n"
        
        msg += "\nActions to be performed:\n"
        if self.xml_file_var.get():
            msg += "• Match using XML (primary method)\n"
        if self.rom_folder_var.get():
            msg += f"• Fuzzy match fallback (threshold: {self.threshold_var.get()}%)\n"
        
        if self.video_mode_var.get() == "rename":
            msg += "• Rename videos in place (no moving/copying)\n"
        else:
            msg += "• Move renamed videos to output folder\n"
            if self.use_platform_subfolder_var.get():
                msg += "• Create platform subfolder in output\n"
        
        msg += "\nProceed?"
        
        if not messagebox.askyesno("Confirm Processing", msg):
            return
        
        # Set renamer properties
        self.renamer.xml_file = self.xml_file_var.get()
        self.renamer.rom_folder = self.rom_folder_var.get()
        self.renamer.platform_video_folder = self.platform_video_folder_var.get()
        self.renamer.output_folder = self.output_folder_var.get()
        self.renamer.threshold = self.threshold_var.get()
        self.renamer.video_mode = self.video_mode_var.get()
        self.renamer.use_platform_subfolder = self.use_platform_subfolder_var.get()
        
        # Set progress callback
        def update_progress(percentage, status_text):
            self.progress_var.set(percentage)
            self.status_text_var.set(status_text)
            self.root.update()
        
        self.renamer.progress_callback = update_progress
        
        # Reset stats
        self.renamer.stats = {
            'roms_found': 0,
            'videos_found': 0,
            'videos_matched': 0,
            'videos_unmatched': 0
        }
        self.renamer.video_matches = {}
        self.renamer.unmatched_videos = []
        
        # Reset progress
        self.progress_var.set(0)
        self.status_text_var.set("Starting processing...")
        
        self.status_var.set("Processing...")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Processing started...\n\n")
        self.root.update()
        
        try:
            log_content, log_path = self.renamer.execute_processing(video_types_to_process)
            
            self.log_path = log_path
            
            # Show summary
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, "=" * 60 + "\n")
            self.results_text.insert(tk.END, "PROCESSING COMPLETE!\n")
            self.results_text.insert(tk.END, "=" * 60 + "\n\n")
            
            if self.renamer.xml_file:
                self.results_text.insert(tk.END, f"✓ XML mappings loaded: {len(self.renamer.xml_mapping)}\n")
            if self.renamer.roms:
                self.results_text.insert(tk.END, f"✓ ROMs found: {self.renamer.stats['roms_found']}\n")
            self.results_text.insert(tk.END, f"✓ Videos processed: {self.renamer.stats['videos_found']}\n")
            self.results_text.insert(tk.END, f"✓ Video types: {len(video_types_to_process)}\n")
            
            self.results_text.insert(tk.END, f"\n✓ Videos matched: {self.renamer.stats['videos_matched']}\n")
            self.results_text.insert(tk.END, f"⚠ Videos unmatched: {self.renamer.stats['videos_unmatched']}\n")
            
            mode_text = "Renamed in place" if self.video_mode_var.get() == "rename" else "Moved to output"
            self.results_text.insert(tk.END, f"✓ Action: {mode_text}\n")
            
            self.results_text.insert(tk.END, f"\n{'=' * 60}\n")
            self.results_text.insert(tk.END, f"Log: {log_path}\n")
            
            self.view_log_button.config(state=tk.NORMAL)
            self.status_var.set("Processing complete!")
            
            # Build success message
            success_msg = f"Processing complete!\n\n"
            success_msg += f"Videos matched: {self.renamer.stats['videos_matched']}\n"
            success_msg += f"Videos unmatched: {self.renamer.stats['videos_unmatched']}\n"
            success_msg += f"Action: {mode_text}"
            
            messagebox.showinfo("Success", success_msg)
            
            # Reset progress bar
            self.progress_var.set(100)
            self.status_text_var.set("Complete!")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.status_var.set("Error occurred during processing")
            self.results_text.insert(tk.END, f"\n❌ ERROR: {str(e)}\n")
            import traceback
            traceback.print_exc()
    
    def view_log(self):
        if hasattr(self, 'log_path') and os.path.exists(self.log_path):
            # Open log in default text editor
            if os.name == 'nt':  # Windows
                os.startfile(self.log_path)
            else:
                messagebox.showinfo("Log Location", f"Log file saved at:\n{self.log_path}")
        else:
            messagebox.showwarning("No Log", "No log file available")


if __name__ == "__main__":
    root = tk.Tk()
    app = ROMVideoRenamerGUI(root)
    root.mainloop()
