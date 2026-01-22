# ROM Image Renamer v3.0 - TrailerVert Edition

**Professional LaunchBox Image Organizer**

Automatically rename and organize your LaunchBox game images to match your ROM collection. Features intelligent matching, bulk processing, and extension conflict handling.

---

## 🚀 Quick Start

1. **Launch** - Double-click `ROM_Image_Renamer_v3_TrailerVert.exe`
2. **Select Folders** - Choose your XML, ROMs, images, and output folders
3. **Scan Types** - Click "Scan Types" to detect image folders
4. **Process** - Click "Start Processing" and wait for completion

---

## 📖 Step-by-Step Guide

### **What You Need:**
- LaunchBox platform XML (e.g., `Sega Genesis.xml`) - Optional but recommended
- ROM folder location
- Platform images folder (e.g., `LaunchBox\Images\Sega Genesis\`)
- Empty output folder

### **Example Workflow:**

**1. Select Platform XML:**  
`LaunchBox\Data\Platforms\Sega Genesis.xml`

**2. Select ROM Folder:**  
`LaunchBox\Games\Sega Genesis\`

**3. Select Platform Image Folder:**  
`LaunchBox\Images\Sega Genesis\`

**4. Select Output Folder:**  
`C:\Organized Images\`

**5. Choose Mode:**
- "Process single image type" - Just Box - Front, for example
- "Process all image types" - All folders at once

**6. Click "Scan Types"** - Detects available folders

**7. Click "Start Processing"** - Confirm and go!

**Result:**
```
Output/
└── Sega Genesis/
    ├── Box - Front/
    │   └── Sonic (USA).jpg
    └── Clear Logo/
        └── Sonic (USA).png
```

---

## ⚙️ Options

### **Remove duplicates (keep -01 only)**
✅ Removes -02, -03, etc. | ❌ Keeps all versions

### **Move unmatched images**
✅ Moves orphaned images to separate folder | ❌ Leaves in place

### **Create platform subfolder**
✅ Organizes as `Output/Platform/Type/` | ❌ Flat `Output/Type/`

### **Prefer extension (for conflicts)**
Handle cases where both `Game.jpg` AND `Game.png` exist:
- **None** - Keeps first alphabetically
- **.jpg / .png** - Keeps only your preference

---

## 🎯 How Matching Works

**Three methods in order:**

1. **XML Matching** (100% accurate) - Uses LaunchBox database
2. **Exact Name** - Image name matches ROM exactly
3. **Fuzzy Matching** - Intelligent similarity (85% threshold)

**Always use XML when available for best results!**

---

## 📊 Understanding Results

```
✓ ROMs found: 783
✓ Images processed: 1,245
✓ Successfully matched: 1,200
  - Via XML: 1,180
  - Via exact name: 15
  - Via fuzzy: 5
↺ Unmatched images: 45
⚠ ROMs without images: 0
⚠ Extension conflicts: 12
```

**Priority Folders** show coverage of important image types:
```
✓ Box - Front: 783 / 783 (100%) - COMPLETE!
⚠ Clear Logo: 750 / 783 (95.8%) - MISSING: 33
```

---

## 📁 Output Files

**1. Renamed Images** - Your output folder, organized  
**2. Processing Log** - `processing_log_*.txt` - Complete details  
**3. Missing ROMs List** - `Missing_ROMs_*.txt` - What's missing (if any)

---

## 💡 Pro Tips

✅ **Always use XML** - 100% accuracy, handles special characters  
✅ **Test small first** - 10-20 games to verify settings  
✅ **Use platform subfolders** - Safe for bulk processing  
✅ **Set extension preference** - Keep file types consistent  
✅ **Review audit log** - Check what matched and how

---

## 🐛 Troubleshooting

**"No image types found"**  
→ Select the platform folder (e.g., `Images\Sega Genesis\`), not a subfolder

**Images not matching**  
→ Provide XML file or lower threshold to 75-80%

**Extension conflicts**  
→ Set your preferred extension in options

---

## ⚠️ Important

- **Original files are safe** - Tool copies, never moves originals
- **Platform name** comes from XML filename
- **Special characters** handled automatically with XML

---

## 📜 Credits

**Developed by:** TrailerVert Team  
**Built with assistance from:** Claude (Anthropic AI)  
**Version:** 3.0  

---

**Happy organizing!** 🎮✨
