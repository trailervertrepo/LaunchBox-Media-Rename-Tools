"""
ROM Image Matcher & Renamer - v3.0
Enhanced version with LaunchBox XML support, multi-folder processing,
video processing, and platform subfolder organization
"""

import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set, Optional
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


class ROMImageMatcherV2:
    def __init__(self):
        self.xml_file = ""
        self.rom_folder = ""
        self.platform_image_folder = ""
        self.output_folder = ""
        self.threshold = 85
        self.process_mode = "single"  # "single" or "all"
        self.selected_image_type = ""
        
        # Statistics
        self.stats = {
            'roms_found': 0,
            'images_found': 0,
            'duplicates_removed': 0,
            'auto_matched': 0,
            'xml_matched': 0,
            'exact_matched': 0,  # NEW: Already correctly named
            'fuzzy_matched': 0,
            'no_match': 0,
            'unmatched_images': 0,
            'extension_conflicts': 0  # v3.0
        }
        
        # Priority folder tracking
        self.priority_folders = ['Box - Front', 'Clear Logo']
        self.priority_stats = {}  # {image_type: {'matched': X, 'total': Y}}
        
        # Data storage
        self.roms = {}  # {rom_name_no_ext: full_path}
        self.xml_mapping = {}  # {sanitized_title: rom_filename_no_ext}
        self.images = {}  # {relative_path: {name_no_ext: full_path}}
        self.matches = {}  # {image_path: (rom_name, image_type_folder)}
        self.unmatched_roms = []
        self.unmatched_images = []
        self.available_image_types = []
        
        # Image extensions
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
        
        # Extension preference for duplicate handling (v3.0)
        self.extension_preference = None  # None, '.jpg', '.png', etc.
        self.extension_conflicts = []  # Track conflicts for reporting
        
        
        
        # Platform subfolder option (v3.0)
        self.use_platform_subfolder = True
        self.platform_name = ""
        
        # Progress callback (v2.2)
        self.progress_callback = None
        
    def sanitize_title(self, title: str) -> str:
        """Sanitize title the way LaunchBox does for filenames"""
        # Replace characters that can't be in filenames
        sanitized = title.replace(':', '_')
        sanitized = sanitized.replace("'", '_')  # v2.2: Handle apostrophes
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
        """Extract platform name from XML filename (v3.0)"""
        if not self.xml_file:
            return ""
        
        # Get filename without extension
        # e.g., "Sega Genesis.xml" -> "Sega Genesis"
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
                        # Extract just the filename from the path
                        rom_filename = os.path.basename(app_path)
                        rom_name_no_ext = Path(rom_filename).stem
                        
                        # Sanitize title for matching with image names
                        sanitized_title = self.sanitize_title(title)
                        
                        mapping[sanitized_title] = rom_name_no_ext
            
            return mapping
            
        except Exception as e:
            print(f"Error parsing XML: {e}")
            return mapping
    
    def normalize_name(self, name: str) -> str:
        """Normalize filename for fuzzy comparison"""
        # Remove file extension
        name = Path(name).stem
        
        # Remove -01, -02, etc. suffixes
        name = re.sub(r'-\d+$', '', name)
        
        # Replace underscores with spaces
        name = name.replace('_', ' ')
        
        # Normalize spacing
        name = ' '.join(name.split())
        
        return name
    
    def get_core_name(self, name: str) -> str:
        """Get core game name without region tags for matching"""
        # Remove common region/version tags for fuzzy matching
        core = re.sub(r'\([^)]*\)', '', name)  # Remove parenthetical content
        core = re.sub(r'\[[^\]]*\]', '', core)  # Remove bracketed content
        core = core.strip()
        return core
    
    def is_usa_rom(self, rom_name: str) -> bool:
        """Check if ROM is USA region"""
        return '(USA)' in rom_name or '(U)' in rom_name
    
    def scan_roms(self) -> Dict[str, str]:
        """Scan ROM folder and return dict of {name: path}
        
        Supports both single-file ROMs and multi-file ROM systems:
        - Single file: Game.smc, Game.md, etc.
        - Multi-file: Game Folder/Game.bin + Game.cue
        """
        roms = {}
        if not os.path.exists(self.rom_folder):
            return roms
        
        # Multi-file ROM extensions (use .bin as the identifier)
        multi_file_extensions = {'.bin', '.gdi'}
        
        # Scan for both files and directories
        for item in os.listdir(self.rom_folder):
            item_path = os.path.join(self.rom_folder, item)
            
            # Handle regular ROM files
            if os.path.isfile(item_path):
                name_no_ext = Path(item).stem
                roms[name_no_ext] = item_path
            
            # Handle multi-file ROM directories (v2.2)
            elif os.path.isdir(item_path):
                # Look for .bin or .gdi files in subdirectory
                for subfile in os.listdir(item_path):
                    subfile_path = os.path.join(item_path, subfile)
                    if os.path.isfile(subfile_path):
                        ext = Path(subfile).suffix.lower()
                        if ext in multi_file_extensions:
                            # Use the .bin/.gdi filename (without extension) as ROM name
                            name_no_ext = Path(subfile).stem
                            roms[name_no_ext] = subfile_path
                            break  # Only take first .bin/.gdi found
        
        return roms
    
    def scan_image_types(self) -> List[str]:
        """Scan platform image folder and return list of image type folders"""
        types = []
        
        if not os.path.exists(self.platform_image_folder):
            return types
        
        for item in os.listdir(self.platform_image_folder):
            item_path = os.path.join(self.platform_image_folder, item)
            if os.path.isdir(item_path):
                # Check if this folder contains any images (recursively)
                if self.has_images_recursive(item_path):
                    types.append(item)
        
        return sorted(types)
    
    def has_images_recursive(self, folder: str) -> bool:
        """Check if folder contains any images (recursively)"""
        for root, dirs, files in os.walk(folder):
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in self.image_extensions:
                    return True
        return False
    
    def scan_images_in_type_folder(self, type_folder_path: str) -> Dict[str, str]:
        """Scan a specific image type folder recursively, return {name_no_ext: full_path}
        v3.0: Handles duplicate extensions (e.g., Space Invaders.jpg AND Space Invaders.png)
        """
        from collections import defaultdict
        
        images = {}
        files_by_base = defaultdict(list)  # {base_name: [(ext, path, full_name)]}
        
        # First pass: collect all images grouped by base name
        for root, dirs, files in os.walk(type_folder_path):
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in self.image_extensions:
                    file_path = os.path.join(root, file)
                    name_no_ext = Path(file).stem
                    # Remove -01, -02 suffix to get base name
                    base_name = re.sub(r'-\d+$', '', name_no_ext)
                    
                    # Group all variants of this base name
                    files_by_base[base_name].append((ext, file_path, name_no_ext))
        
        # Second pass: handle extension conflicts (v3.0)
        for base_name, file_list in files_by_base.items():
            # Get unique extensions for this base name
            extensions_found = sorted(set(ext for ext, _, _ in file_list))
            
            if len(extensions_found) > 1:
                # CONFLICT: Multiple file types for same base name
                self.extension_conflicts.append((base_name, extensions_found))
                self.stats['extension_conflicts'] += 1
                
                # Decide which extension to keep
                if self.extension_preference and self.extension_preference in extensions_found:
                    # Keep ONLY the preferred extension
                    for ext, path, name in file_list:
                        if ext == self.extension_preference:
                            images[name] = path
                else:
                    # No preference - keep first extension alphabetically
                    kept_ext = extensions_found[0]
                    for ext, path, name in file_list:
                        if ext == kept_ext:
                            images[name] = path
            else:
                # No conflict - add all files
                for ext, path, name in file_list:
                    images[name] = path
        
        return images
    
    def scan_all_images(self, image_types: List[str]) -> Dict[str, Dict[str, str]]:
        """Scan all specified image type folders"""
        all_images = {}
        
        for image_type in image_types:
            type_folder_path = os.path.join(self.platform_image_folder, image_type)
            images = self.scan_images_in_type_folder(type_folder_path)
            if images:
                all_images[image_type] = images
        
        return all_images
    
    def find_duplicates_in_folder(self, images: Dict[str, str]) -> Dict[str, List[Tuple]]:
        """Find duplicate images (same base name with -01, -02, etc.)"""
        duplicates = {}
        
        for img_name, img_path in images.items():
            # Check if this has a number suffix
            match = re.match(r'(.+)-(\d+)$', img_name)
            if match:
                base_name = match.group(1)
                suffix_num = int(match.group(2))
                
                if base_name not in duplicates:
                    duplicates[base_name] = []
                
                duplicates[base_name].append((suffix_num, img_name, img_path))
        
        # Filter to only groups with actual duplicates
        duplicates = {k: v for k, v in duplicates.items() if len(v) > 1}
        
        return duplicates
    
    def remove_duplicates_in_folder(self, images: Dict[str, str]) -> Tuple[int, Dict[str, str]]:
        """Remove duplicate images, keeping -01 versions. Returns (count_removed, updated_images)"""
        duplicates = self.find_duplicates_in_folder(images)
        removed_count = 0
        updated_images = images.copy()
        
        for base_name, images_list in duplicates.items():
            # Sort by suffix number
            images_list.sort(key=lambda x: x[0])
            
            # Keep -01 (first item), remove others
            for suffix_num, img_name, img_path in images_list[1:]:
                try:
                    os.remove(img_path)
                    removed_count += 1
                    # Remove from our images dict
                    if img_name in updated_images:
                        del updated_images[img_name]
                except Exception as e:
                    print(f"Error removing {img_path}: {e}")
        
        return removed_count, updated_images
    
    def match_image_to_rom_xml(self, img_name: str) -> Optional[str]:
        """Try to match image to ROM using XML mapping"""
        if not self.xml_mapping:
            return None
        
        # Remove -01, -02 suffix
        base_name = re.sub(r'-\d+$', '', img_name)
        
        # Direct lookup in XML mapping
        if base_name in self.xml_mapping:
            return self.xml_mapping[base_name]
        
        return None
    
    def match_image_to_rom_exact(self, img_name: str, rom_names: List[str]) -> Optional[str]:
        """Try to match image to ROM by exact name (already correctly named)"""
        # Remove -01, -02 suffix from image name
        base_name = re.sub(r'-\d+$', '', img_name)
        
        # Check if image name exactly matches a ROM name
        if base_name in rom_names:
            return base_name
        
        return None
    
    def match_image_to_rom_fuzzy(self, img_name: str, rom_names: List[str]) -> Tuple[Optional[str], float]:
        """Try to match image to ROM using fuzzy matching"""
        normalized_image = self.normalize_name(img_name)
        core_image = self.get_core_name(normalized_image)
        
        # Create list of normalized ROM names
        rom_choices = []
        for rom in rom_names:
            normalized_rom = self.normalize_name(rom)
            rom_choices.append((normalized_rom, rom))
        
        # Get all matches above threshold
        matches = []
        for normalized_rom, original_rom in rom_choices:
            core_rom = self.get_core_name(normalized_rom)
            
            # Try multiple matching strategies
            score1 = fuzz.ratio(normalized_image, normalized_rom)
            score2 = fuzz.ratio(core_image, core_rom)
            score3 = fuzz.partial_ratio(normalized_image, normalized_rom)
            
            # Use the best score
            best_score = max(score1, score2, score3)
            
            if best_score >= self.threshold:
                matches.append((original_rom, best_score))
        
        if not matches:
            return None, 0
        
        # If multiple matches, prefer USA versions
        usa_matches = [m for m in matches if self.is_usa_rom(m[0])]
        if usa_matches:
            usa_matches.sort(key=lambda x: x[1], reverse=True)
            return usa_matches[0]
        
        # Otherwise return highest scoring match
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[0]
    
    def match_images_to_roms(self, image_type: str, images: Dict[str, str]):
        """Match images in a specific type folder to ROMs"""
        rom_names = list(self.roms.keys()) if self.roms else []
        
        # Initialize priority stats for this image type
        if image_type in self.priority_folders:
            self.priority_stats[image_type] = {'matched': 0, 'total': len(images)}
        
        for img_name, img_path in images.items():
            matched_rom = None
            match_type = None
            
            # Try XML matching first
            matched_rom = self.match_image_to_rom_xml(img_name)
            if matched_rom:
                match_type = 'xml'
            
            # Try exact ROM name match (already correctly named)
            if not matched_rom and rom_names:
                matched_rom = self.match_image_to_rom_exact(img_name, rom_names)
                if matched_rom:
                    match_type = 'exact'
            
            # Fallback to fuzzy matching
            if not matched_rom and rom_names:
                matched_rom, score = self.match_image_to_rom_fuzzy(img_name, rom_names)
                if matched_rom and score >= self.threshold:
                    match_type = 'fuzzy'
            
            # Record the match
            if matched_rom:
                self.matches[img_path] = (matched_rom, image_type)
                self.stats['auto_matched'] += 1
                
                if match_type == 'xml':
                    self.stats['xml_matched'] += 1
                elif match_type == 'exact':
                    self.stats['exact_matched'] += 1
                elif match_type == 'fuzzy':
                    self.stats['fuzzy_matched'] += 1
                
                # Track priority folder matches
                if image_type in self.priority_folders:
                    self.priority_stats[image_type]['matched'] += 1
            else:
                self.unmatched_images.append((img_path, image_type))
                self.stats['unmatched_images'] += 1
    
    def execute_processing(self, image_types_to_process: List[str],
                          remove_duplicates: bool, move_unmatched: bool) -> Tuple[str, str, str]:
        """Execute the full processing workflow (v2.2: added video support)"""
        log_lines = []
        log_lines.append(f"ROM Image Matcher v3.0 - Processing Report")
        log_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_lines.append("=" * 70)
        
        # Calculate total steps for progress
        total_steps = 0
        if self.xml_file:
            total_steps += 1
        if self.rom_folder:
            total_steps += 1
        total_steps += len(image_types_to_process) * 2  # scan + match
        total_steps += 2  # copy files + cleanup
        
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
            
            # Extract platform name from XML (v3.0)
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
        
        # Process each image type
        total_duplicates_removed = 0
        
        for idx, image_type in enumerate(image_types_to_process):
            update_progress(f"Scanning {image_type}...")
            log_lines.append(f"\n{'=' * 70}")
            log_lines.append(f"--- PROCESSING IMAGE TYPE: {image_type} ---")
            
            type_folder_path = os.path.join(self.platform_image_folder, image_type)
            images = self.scan_images_in_type_folder(type_folder_path)
            
            log_lines.append(f"Images found: {len(images)}")
            self.stats['images_found'] += len(images)
            
            # Remove duplicates if enabled
            if remove_duplicates:
                removed, images = self.remove_duplicates_in_folder(images)
                total_duplicates_removed += removed
                if removed > 0:
                    log_lines.append(f"Duplicates removed: {removed}")
            
            update_progress(f"Matching {image_type} ({idx+1}/{len(image_types_to_process)})...")
            # Match images to ROMs
            self.match_images_to_roms(image_type, images)
        
        
        self.stats['duplicates_removed'] = total_duplicates_removed
        
        update_progress("Copying/renaming files...")
        
        # Create output folders
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Create unmatched folder
        if move_unmatched:
            unmatched_base = os.path.join(self.platform_image_folder, "Unmatched_Images")
            os.makedirs(unmatched_base, exist_ok=True)
        
        # Process matched images
        log_lines.append(f"\n{'=' * 70}")
        log_lines.append("\n--- MATCHED AND RENAMED ---")
        
        for img_path, (rom_name, image_type) in self.matches.items():
            img_ext = Path(img_path).suffix
            new_name = f"{rom_name}{img_ext}"
            
            # Build output path with optional platform subfolder (v3.0)
            if self.use_platform_subfolder and self.platform_name:
                output_type_folder = os.path.join(self.output_folder, self.platform_name, image_type)
            else:
                output_type_folder = os.path.join(self.output_folder, image_type)
            os.makedirs(output_type_folder, exist_ok=True)
            
            new_path = os.path.join(output_type_folder, new_name)
            
            try:
                shutil.copy2(img_path, new_path)
                log_lines.append(f"✓ [{image_type}] {Path(img_path).name} → {new_name}")
            except Exception as e:
                log_lines.append(f"✗ [{image_type}] Error copying {Path(img_path).name}: {e}")
        
        # Move unmatched images
        if move_unmatched and self.unmatched_images:
            log_lines.append(f"\n--- UNMATCHED IMAGES (Moved to Unmatched_Images) ---")
            
            for img_path, image_type in self.unmatched_images:
                img_name = Path(img_path).name
                
                # Maintain folder structure in unmatched folder
                unmatched_type_folder = os.path.join(unmatched_base, image_type)
                os.makedirs(unmatched_type_folder, exist_ok=True)
                
                unmatched_path = os.path.join(unmatched_type_folder, img_name)
                
                try:
                    shutil.move(img_path, unmatched_path)
                    log_lines.append(f"↺ [{image_type}] {img_name}")
                except Exception as e:
                    log_lines.append(f"✗ [{image_type}] Error moving {img_name}: {e}")
        
        update_progress("Finalizing...")
        
        # Find ROMs without images
        if self.roms:
            matched_roms = set(rom_name for rom_name, _ in self.matches.values())
            all_roms = set(self.roms.keys())
            self.unmatched_roms = list(all_roms - matched_roms)
            self.stats['no_match'] = len(self.unmatched_roms)
            
            log_lines.append(f"\n--- ROMS WITHOUT IMAGES ---")
            if self.unmatched_roms:
                for rom_name in sorted(self.unmatched_roms):
                    log_lines.append(f"⚠ {rom_name}")
            else:
                log_lines.append("None - all ROMs have matching images!")
        
        # Extension conflicts detail (v3.0)
        if self.extension_conflicts:
            log_lines.append(f"\n--- EXTENSION CONFLICTS ---")
            log_lines.append(f"Found {len(self.extension_conflicts)} images with multiple file types")
            if self.extension_preference:
                log_lines.append(f"Preference: {self.extension_preference} (kept preferred)")
            else:
                log_lines.append(f"No preference set (kept first alphabetically)")
            log_lines.append("")
            # Show first 20 conflicts
            for base_name, extensions in self.extension_conflicts[:20]:
                ext_list = ', '.join(sorted(extensions))
                log_lines.append(f"⚠ {base_name}: {ext_list}")
            if len(self.extension_conflicts) > 20:
                log_lines.append(f"... and {len(self.extension_conflicts) - 20} more conflicts")
        
                # Statistics summary
        log_lines.append("\n" + "=" * 70)
        log_lines.append("--- SUMMARY ---")
        if self.xml_file:
            log_lines.append(f"XML mappings loaded: {len(self.xml_mapping)}")
        if self.roms:
            log_lines.append(f"Total ROMs found: {self.stats['roms_found']}")
        log_lines.append(f"Total images found: {self.stats['images_found']}")
        log_lines.append(f"Image types processed: {len(image_types_to_process)}")
        log_lines.append(f"Duplicates removed: {self.stats['duplicates_removed']}")
        log_lines.append(f"Successfully matched: {self.stats['auto_matched']}")
        if self.xml_file or self.stats['exact_matched'] > 0 or self.stats['fuzzy_matched'] > 0:
            log_lines.append(f"  - Via XML: {self.stats['xml_matched']}")
            log_lines.append(f"  - Via exact name: {self.stats['exact_matched']}")
            log_lines.append(f"  - Via fuzzy matching: {self.stats['fuzzy_matched']}")
        log_lines.append(f"Unmatched images: {self.stats['unmatched_images']}")
        log_lines.append(f"ROMs without images: {self.stats['no_match']}")
        
        # Extension conflicts (v3.0)
        if self.stats['extension_conflicts'] > 0:
            log_lines.append(f"Extension conflicts: {self.stats['extension_conflicts']}")
            if self.extension_preference:
                log_lines.append(f"  Preferred extension: {self.extension_preference}")
        
        
        # Priority folder verification
        if self.priority_stats and self.roms:
            log_lines.append("\n" + "=" * 70)
            log_lines.append("--- PRIORITY FOLDERS VERIFICATION ---")
            for folder_name in self.priority_folders:
                if folder_name in self.priority_stats:
                    matched = self.priority_stats[folder_name]['matched']
                    total_roms = self.stats['roms_found']
                    percentage = (matched / total_roms * 100) if total_roms > 0 else 0
                    missing = total_roms - matched
                    status = "✓" if missing == 0 else "⚠"
                    log_lines.append(f"{status} {folder_name}: {matched} / {total_roms} ROMs ({percentage:.1f}%)")
                    if missing > 0:
                        log_lines.append(f"   MISSING: {missing} images")
        
        log_content = "\n".join(log_lines)
        
        # Save log file
        log_path = os.path.join(self.output_folder, 
                               f"processing_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        # Export missing ROMs list if there are any
        missing_roms_path = None
        if self.unmatched_roms:
            missing_roms_path = os.path.join(self.output_folder, 
                                            f"Missing_ROMs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(missing_roms_path, 'w', encoding='utf-8') as f:
                f.write("ROMs Without Images\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Missing: {len(self.unmatched_roms)}\n\n")
                
                # Group by image types processed
                if self.priority_stats:
                    f.write("Priority Folders Status:\n")
                    for folder_name in self.priority_folders:
                        if folder_name in self.priority_stats:
                            matched = self.priority_stats[folder_name]['matched']
                            total_roms = self.stats['roms_found']
                            missing = total_roms - matched
                            f.write(f"  {folder_name}: Missing {missing} images\n")
                    f.write("\n")
                
                f.write("Missing ROM Names:\n")
                f.write("-" * 50 + "\n")
                for rom_name in sorted(self.unmatched_roms):
                    f.write(f"{rom_name}\n")
        
        return log_content, log_path, missing_roms_path


class ROMImageMatcherGUIV2:
    def __init__(self, root):
        self.root = root
        self.root.title("ROM Image Matcher & Renamer v3.0 - TrailerVert Edition")

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        width  = int(screen_w * 0.50)
        height = int(screen_h * 0.80)

        x = (screen_w - width) // 2
        y = (screen_h - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(width, height)

        self.root.resizable(True, True)
        
        self.matcher = ROMImageMatcherV2()
        self.missing_roms_path = None
        
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
        
        # TrailerVert Branding (v3.0)
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
        
        title_label = ttk.Label(title_container, text="ROM Image Matcher & Renamer v3.0", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(anchor=tk.W)
        
        subtitle_label = ttk.Label(title_container, text="TrailerVert Edition", 
                                   font=('Arial', 10, 'italic'),
                                   foreground='#666666')
        subtitle_label.pack(anchor=tk.W)
        
        # Folder selection section
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
        
        # Platform Image Folder
        ttk.Label(main_frame, text="Platform Image Folder:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.platform_image_folder_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.platform_image_folder_var, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_platform_image_folder).grid(row=row, column=2)
        row += 1
        
        # Output Folder
        ttk.Label(main_frame, text="Output Folder:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.output_folder_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.output_folder_var, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_output_folder).grid(row=row, column=2)
        row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)
        row += 1
        
        # Processing mode selection
        mode_frame = ttk.LabelFrame(main_frame, text="Processing Mode", padding="10")
        mode_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.process_mode_var = tk.StringVar(value="single")
        
        single_radio = ttk.Radiobutton(mode_frame, text="Process single image type folder", 
                                       variable=self.process_mode_var, value="single",
                                       command=self.on_mode_change)
        single_radio.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        all_radio = ttk.Radiobutton(mode_frame, text="Process all image types for platform", 
                                    variable=self.process_mode_var, value="all",
                                    command=self.on_mode_change)
        all_radio.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        row += 1
        
        # Image type selection frame
        type_frame = ttk.Frame(main_frame)
        type_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        type_frame.columnconfigure(1, weight=1)
        
        ttk.Label(type_frame, text="Image Type:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.image_type_var = tk.StringVar()
        self.image_type_dropdown = ttk.Combobox(type_frame, textvariable=self.image_type_var, 
                                                state="readonly", width=47)
        self.image_type_dropdown.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        self.scan_types_button = ttk.Button(type_frame, text="Scan Types", 
                                           command=self.scan_image_types)
        self.scan_types_button.grid(row=0, column=2)
        
        row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)
        row += 1
        
        # Threshold slider (only used if no XML)
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
        
        self.maintain_structure_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Maintain folder structure in output", 
                       variable=self.maintain_structure_var, state=tk.DISABLED).pack(anchor=tk.W)
        
        self.remove_duplicates_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Remove duplicates (keep -01 only)", 
                       variable=self.remove_duplicates_var).pack(anchor=tk.W)
        
        self.move_unmatched_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Move unmatched images to separate folder", 
                       variable=self.move_unmatched_var).pack(anchor=tk.W)
        
        # Platform subfolder option
        self.use_platform_subfolder_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Create platform subfolder in output (safer for bulk processing)", 
                       variable=self.use_platform_subfolder_var).pack(anchor=tk.W)
        
        # Extension preference (v3.0)
        ext_pref_frame = ttk.Frame(options_frame)
        ext_pref_frame.pack(anchor=tk.W, fill=tk.X, pady=(5, 0))
        
        ttk.Label(ext_pref_frame, text="Prefer extension (for conflicts):").pack(side=tk.LEFT, padx=(0, 5))
        self.extension_pref_var = tk.StringVar(value="None")
        self.extension_pref_dropdown = ttk.Combobox(ext_pref_frame, 
                                                    textvariable=self.extension_pref_var,
                                                    values=["None", ".jpg", ".png", ".gif", ".bmp", ".webp"],
                                                    state="readonly", 
                                                    width=10)
        self.extension_pref_dropdown.pack(side=tk.LEFT)
        self.extension_pref_dropdown.current(0)
        
        ttk.Label(ext_pref_frame, text=" (when same image has multiple file types)", 
                 font=('Arial', 8, 'italic')).pack(side=tk.LEFT, padx=(5, 0))
        
        row += 1
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=15)
        
        self.process_button = ttk.Button(button_frame, text="Start Processing", 
                                        command=self.start_processing, state=tk.DISABLED)
        self.process_button.pack(side=tk.LEFT, padx=5)
        row += 1
        
        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        results_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(row, weight=1)
        
        # Progress bar (v2.2)
        progress_container = ttk.Frame(results_frame)
        progress_container.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_container, variable=self.progress_var, 
                                           maximum=100, mode='determinate', length=400)
        self.progress_bar.pack(fill=tk.X)
        
        self.status_label = ttk.Label(progress_container, textvariable=self.status_text_var,
                                     font=('Arial', 9))
        self.status_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Results text area
        self.results_text = scrolledtext.ScrolledText(results_frame, height=12, wrap=tk.WORD)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        row += 1
        
        # View log button
        self.view_log_button = ttk.Button(main_frame, text="View Full Audit Log", 
                                         command=self.view_log, state=tk.DISABLED)
        self.view_log_button.grid(row=row, column=0, columnspan=3, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Please select folders and image type.")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.log_path = None
        
        # Initialize mode
        self.on_mode_change()
    
    def update_threshold_label(self, value):
        self.threshold_label.config(text=f"{int(float(value))}%")
    
    def on_mode_change(self):
        """Handle processing mode change"""
        if self.process_mode_var.get() == "single":
            self.image_type_dropdown.config(state="readonly")
            self.scan_types_button.config(state=tk.NORMAL)
        else:
            self.image_type_dropdown.config(state=tk.DISABLED)
            self.scan_types_button.config(state=tk.NORMAL)
        
        # Update dropdown to add/remove "ALL" option if types already scanned
        if hasattr(self, 'matcher') and self.matcher.available_image_types:
            image_types = self.matcher.available_image_types
            if self.process_mode_var.get() == "all":
                dropdown_values = ["ALL - Process all types"] + image_types
            else:
                dropdown_values = image_types
            self.image_type_dropdown['values'] = dropdown_values
            if dropdown_values:
                self.image_type_dropdown.current(0)
    
    def browse_xml_file(self):
        file = filedialog.askopenfilename(title="Select Platform XML", 
                                         filetypes=[("XML files", "*.xml"), ("All files", "*.*")])
        if file:
            self.xml_file_var.set(file)
    
    def browse_rom_folder(self):
        folder = filedialog.askdirectory(title="Select ROM Folder")
        if folder:
            self.rom_folder_var.set(folder)
    
    def browse_platform_image_folder(self):
        folder = filedialog.askdirectory(title="Select Platform Image Folder")
        if folder:
            self.platform_image_folder_var.set(folder)
    
    def browse_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder_var.set(folder)
    
    def scan_image_types(self):
        """Scan platform image and video folders for available types (v2.2 updated)"""
        if not self.platform_image_folder_var.get():
            messagebox.showerror("Error", "Please select a Platform Image Folder first")
            return
        
        self.matcher.platform_image_folder = self.platform_image_folder_var.get()
        
        self.status_var.set("Scanning for image types...")
        self.status_text_var.set("Scanning folders...")
        self.root.update()
        
        # Scan image types
        image_types = self.matcher.scan_image_types()
        
        if not image_types:
            messagebox.showwarning("No Image Types", "No image type folders found with images")
            self.status_var.set("No image types found")
            return
        
        # Add "ALL" option at the beginning
        if self.process_mode_var.get() == "all":
            dropdown_values = ["ALL - Process all types"] + image_types
        else:
            dropdown_values = image_types
        
        self.image_type_dropdown['values'] = dropdown_values
        
        # Auto-select first item
        if dropdown_values:
            self.image_type_dropdown.current(0)
        
        self.matcher.available_image_types = image_types
        
        # Display results
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"Image types found: {len(image_types)}\n\n")
        self.results_text.insert(tk.END, "Available image types:\n")
        for img_type in image_types:
            self.results_text.insert(tk.END, f"  • {img_type}\n")
        
        self.process_button.config(state=tk.NORMAL)
        self.status_var.set(f"Found {len(image_types)} image types. Ready to process.")
        self.status_text_var.set("")
    
    def start_processing(self):
        """Start the processing workflow"""
        # Validate inputs
        if not self.platform_image_folder_var.get():
            messagebox.showerror("Error", "Please select a Platform Image Folder")
            return
        
        if not self.output_folder_var.get():
            messagebox.showerror("Error", "Please select an Output Folder")
            return
        
        if not self.xml_file_var.get() and not self.rom_folder_var.get():
            messagebox.showerror("Error", "Please provide either a Platform XML or ROM Folder")
            return
        
        if not self.matcher.available_image_types:
            messagebox.showerror("Error", "Please scan for image types first")
            return
        
        # Determine which image types to process
        if self.process_mode_var.get() == "all" or self.image_type_var.get().startswith("ALL"):
            image_types_to_process = self.matcher.available_image_types
        else:
            selected_type = self.image_type_var.get()
            if not selected_type:
                messagebox.showerror("Error", "Please select an image type")
                return
            image_types_to_process = [selected_type]
        
        # Confirm with user
        msg = f"Ready to process {len(image_types_to_process)} image type(s).\n\n"
        
        msg += "Image types:\n"
        for img_type in image_types_to_process[:5]:
            msg += f"  • {img_type}\n"
        if len(image_types_to_process) > 5:
            msg += f"  ... and {len(image_types_to_process) - 5} more\n"
        
        msg += "\nActions to be performed:\n"
        if self.remove_duplicates_var.get():
            msg += "• Remove duplicate images (keep -01 versions)\n"
        if self.xml_file_var.get():
            msg += "• Match using XML (primary method)\n"
        if self.rom_folder_var.get():
            msg += f"• Fuzzy match fallback (threshold: {self.threshold_var.get()}%)\n"
        msg += "• Copy renamed images to output folder\n"
        if self.move_unmatched_var.get():
            msg += "• Move unmatched images to 'Unmatched_Images' folder\n"
        msg += "\nProceed?"
        
        if not messagebox.askyesno("Confirm Processing", msg):
            return
        
        # Set matcher properties
        self.matcher.xml_file = self.xml_file_var.get()
        self.matcher.rom_folder = self.rom_folder_var.get()
        self.matcher.platform_image_folder = self.platform_image_folder_var.get()
        self.matcher.output_folder = self.output_folder_var.get()
        self.matcher.threshold = self.threshold_var.get()
        
        # Platform subfolder option
        self.matcher.use_platform_subfolder = self.use_platform_subfolder_var.get()
        
        # Extension preference (v3.0)
        if self.extension_pref_var.get() != "None":
            self.matcher.extension_preference = self.extension_pref_var.get()
        else:
            self.matcher.extension_preference = None
        
        # Set progress callback
        def update_progress(percentage, status_text):
            self.progress_var.set(percentage)
            self.status_text_var.set(status_text)
            self.root.update()
        
        self.matcher.progress_callback = update_progress
        
        # Reset stats
        self.matcher.stats = {
            'roms_found': 0,
            'images_found': 0,
            'duplicates_removed': 0,
            'auto_matched': 0,
            'xml_matched': 0,
            'exact_matched': 0,
            'fuzzy_matched': 0,
            'no_match': 0,
            'unmatched_images': 0,
            'extension_conflicts': 0  # v3.0
        }
        self.matcher.priority_stats = {}
        self.matcher.matches = {}
        self.matcher.unmatched_images = []
        self.matcher.unmatched_roms = []
        self.matcher.extension_conflicts = []  # v3.0
        
        # Reset progress
        self.progress_var.set(0)
        self.status_text_var.set("Starting processing...")
        
        self.status_var.set("Processing...")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Processing started...\n\n")
        self.root.update()
        
        try:
            log_content, log_path, missing_roms_path = self.matcher.execute_processing(
                image_types_to_process,
                self.remove_duplicates_var.get(),
                self.move_unmatched_var.get()
            )
            
            self.log_path = log_path
            self.missing_roms_path = missing_roms_path
            
            # Show summary
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, "=" * 60 + "\n")
            self.results_text.insert(tk.END, "PROCESSING COMPLETE!\n")
            self.results_text.insert(tk.END, "=" * 60 + "\n\n")
            
            if self.matcher.xml_file:
                self.results_text.insert(tk.END, f"✓ XML mappings loaded: {len(self.matcher.xml_mapping)}\n")
            if self.matcher.roms:
                self.results_text.insert(tk.END, f"✓ ROMs found: {self.matcher.stats['roms_found']}\n")
            self.results_text.insert(tk.END, f"✓ Images processed: {self.matcher.stats['images_found']}\n")
            self.results_text.insert(tk.END, f"✓ Image types: {len(image_types_to_process)}\n")
            if self.matcher.stats['duplicates_removed'] > 0:
                self.results_text.insert(tk.END, f"✓ Duplicates removed: {self.matcher.stats['duplicates_removed']}\n")
            
            self.results_text.insert(tk.END, f"\n✓ Successfully matched: {self.matcher.stats['auto_matched']}\n")
            if self.matcher.xml_file or self.matcher.stats['exact_matched'] > 0:
                self.results_text.insert(tk.END, f"  - Via XML: {self.matcher.stats['xml_matched']}\n")
                self.results_text.insert(tk.END, f"  - Via exact name: {self.matcher.stats['exact_matched']}\n")
                self.results_text.insert(tk.END, f"  - Via fuzzy: {self.matcher.stats['fuzzy_matched']}\n")
            
            self.results_text.insert(tk.END, f"↺ Unmatched images: {self.matcher.stats['unmatched_images']}\n")
            self.results_text.insert(tk.END, f"⚠ ROMs without images: {self.matcher.stats['no_match']}\n")
            
            # Extension conflicts (v3.0)
            if self.matcher.stats['extension_conflicts'] > 0:
                self.results_text.insert(tk.END, f"\n⚠ Extension conflicts: {self.matcher.stats['extension_conflicts']}\n")
                if self.matcher.extension_preference:
                    self.results_text.insert(tk.END, f"  Kept: {self.matcher.extension_preference} (preferred)\n")
                else:
                    self.results_text.insert(tk.END, f"  Kept: First alphabetically\n")
            
            # Show priority folder verification
            if self.matcher.priority_stats and self.matcher.roms:
                self.results_text.insert(tk.END, "\n" + "-" * 60 + "\n")
                self.results_text.insert(tk.END, "PRIORITY FOLDERS VERIFICATION:\n")
                self.results_text.insert(tk.END, "-" * 60 + "\n")
                for folder_name in self.matcher.priority_folders:
                    if folder_name in self.matcher.priority_stats:
                        matched = self.matcher.priority_stats[folder_name]['matched']
                        total_roms = self.matcher.stats['roms_found']
                        percentage = (matched / total_roms * 100) if total_roms > 0 else 0
                        missing = total_roms - matched
                        status = "✓" if missing == 0 else "⚠"
                        self.results_text.insert(tk.END, 
                            f"{status} {folder_name}: {matched} / {total_roms} ({percentage:.1f}%)")
                        if missing > 0:
                            self.results_text.insert(tk.END, f" - MISSING: {missing}\n")
                        else:
                            self.results_text.insert(tk.END, " - COMPLETE!\n")
            
            self.results_text.insert(tk.END, f"\n{'=' * 60}\n")
            self.results_text.insert(tk.END, f"Output: {self.matcher.output_folder}\n")
            self.results_text.insert(tk.END, f"Log: {log_path}\n")
            if missing_roms_path:
                self.results_text.insert(tk.END, f"Missing ROMs List: {missing_roms_path}\n")
            
            self.view_log_button.config(state=tk.NORMAL)
            self.status_var.set("Processing complete!")
            
            # Build success message
            success_msg = f"Processing complete!\n\n"
            success_msg += f"Matched: {self.matcher.stats['auto_matched']}\n"
            success_msg += f"Unmatched: {self.matcher.stats['unmatched_images']}\n"
            success_msg += f"ROMs without images: {self.matcher.stats['no_match']}\n"
            
            if self.matcher.priority_stats:
                success_msg += "\nPriority Folders:\n"
                for folder_name in self.matcher.priority_folders:
                    if folder_name in self.matcher.priority_stats:
                        matched = self.matcher.priority_stats[folder_name]['matched']
                        total_roms = self.matcher.stats['roms_found']
                        percentage = (matched / total_roms * 100) if total_roms > 0 else 0
                        success_msg += f"  {folder_name}: {percentage:.1f}% ({matched}/{total_roms})\n"
            
            if missing_roms_path:
                success_msg += f"\nMissing ROMs list exported!"
            
            # Extension conflicts (v3.0)
            if self.matcher.stats['extension_conflicts'] > 0:
                success_msg += f"\n\n⚠ {self.matcher.stats['extension_conflicts']} extension conflicts handled"
                if self.matcher.extension_preference:
                    success_msg += f" ({self.matcher.extension_preference} preferred)"
            
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
        if self.log_path and os.path.exists(self.log_path):
            # Open log in default text editor
            if os.name == 'nt':  # Windows
                os.startfile(self.log_path)
            else:
                messagebox.showinfo("Log Location", f"Log file saved at:\n{self.log_path}")
        else:
            messagebox.showerror("Error", "Log file not found")


def main():
    root = tk.Tk()
    app = ROMImageMatcherGUIV2(root)
    root.mainloop()


if __name__ == "__main__":
    main()
