# TrailerVert LaunchBox Tools

**Professional ROM Image & Video Management Suite for LaunchBox**

Two powerful tools to automatically rename and organize your LaunchBox media collections with intelligent matching and bulk processing.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-blue.svg)](https://www.microsoft.com/windows)

---

## 🎮 Tools Included

### **ROM Image Renamer v3.0**
Organize your LaunchBox game images with intelligent matching.

**Features:**
- ✅ XML-based 100% accurate matching
- ✅ Bulk process entire platforms
- ✅ Extension conflict handling (.jpg vs .png)
- ✅ Priority folder verification
- ✅ Missing ROMs export
- ✅ Platform subfolder organization

[📖 Read Full Image Renamer Guide](README_Image_Renamer.md)

---

### **ROM Video Renamer v1.1**
Rename LaunchBox videos to match your ROM collection.

**Features:**
- ✅ Rename in place (fast)
- ✅ Move to output (organized)
- ✅ Root folder scanning
- ✅ Multiple video type support
- ✅ XML matching
- ✅ Platform subfolder organization

[📖 Read Full Video Renamer Guide](README_Video_Renamer.md)

---

## 🚀 Quick Start

### **Option 1: Use Pre-Built .exe Files (Easiest)**

1. Download the latest release
2. Extract to a folder
3. Double-click the .exe you need
4. Follow the in-app instructions

**No Python installation required!**

---

### **Option 2: Run Python Scripts**

#### **Prerequisites:**
```bash
pip install rapidfuzz
```

#### **Run:**
```bash
# Image Renamer
python rom_image_renamer_v3.0_TrailerVert_Edition.py

# Video Renamer
python rom_video_renamer_v1.1_TrailerVert_Edition.py
```

---

## 📦 What's Included

```
TrailerVert-LaunchBox-Tools/
├── Executables/
│   ├── ROM_Image_Renamer_v3_TrailerVert.exe
│   └── ROM_Video_Renamer_v1.1_TrailerVert.exe
├── Python_Scripts/
│   ├── rom_image_renamer_v3.0_TrailerVert_Edition.py
│   └── rom_video_renamer_v1.1_TrailerVert_Edition.py
├── Assets/
│   ├── logo.png
│   └── app_icon.ico
├── Documentation/
│   ├── README_Image_Renamer.md
│   ├── README_Video_Renamer.md
│   └── BUILD_EXE_GUIDE.md
└── README.md (this file)
```

---

## 💡 Use Cases

### **Scenario 1: New LaunchBox Setup**
You have ROMs and images but they don't match:
1. Use **Image Renamer** to organize all images
2. Use **Video Renamer** to organize all videos
3. Copy organized files back to LaunchBox
4. Perfect match!

### **Scenario 2: Bulk Image Downloads**
Downloaded thousands of images from EmuMovies:
1. Point **Image Renamer** to download folder
2. Select your ROM folder + LaunchBox XML
3. Process all image types at once
4. Get perfectly organized output

### **Scenario 3: LaunchBox Video Dump**
LaunchBox dumped videos with random names:
1. Use **Video Renamer** in "Rename in place" mode
2. Point to LaunchBox video folder
3. Videos renamed to match ROMs instantly
4. LaunchBox shows correct videos

---

## 🎯 Why These Tools?

### **Problem:**
- LaunchBox images/videos downloaded with wrong names
- Bulk downloads need manual organization
- Images named `-01, -02` need cleanup
- Multiple platforms = organizational nightmare

### **Solution:**
- **Intelligent Matching:** XML + exact + fuzzy algorithms
- **Bulk Processing:** Entire platforms at once
- **Smart Organization:** Platform subfolders, duplicate handling
- **Detailed Reporting:** Know exactly what matched and what didn't

---

## 📊 Key Features

### **Intelligent Matching**
- **XML First:** 100% accurate using LaunchBox database
- **Exact Fallback:** Perfect filename matches
- **Fuzzy Last:** Smart similarity comparison
- **Region Aware:** Prioritizes USA versions

### **Bulk Operations**
- Process all image types simultaneously
- Handle thousands of files at once
- Progress tracking with status updates
- Detailed audit logs

### **Professional Organization**
- Platform subfolder support
- Duplicate removal (-01 only)
- Extension conflict resolution
- Priority folder verification

### **Safety**
- Original files never modified (Image tool copies)
- Detailed logs of all actions
- Unmatched file segregation
- Missing ROM reports

---

## 🛠️ Building from Source

Want to build your own .exe files?

### **Prerequisites:**
```bash
pip install pyinstaller rapidfuzz
```

### **Quick Build:**
Use the included batch file:
```bash
build_trailervert_tools.bat
```

### **Manual Build:**
```bash
# Image Renamer
python -m PyInstaller --onefile --windowed --icon=app_icon.ico --add-data "logo.png;." --add-data "app_icon.ico;." --name "ROM_Image_Renamer_v3_TrailerVert" rom_image_renamer_v3.0_TrailerVert_Edition.py

# Video Renamer
python -m PyInstaller --onefile --windowed --icon=app_icon.ico --add-data "logo.png;." --add-data "app_icon.ico;." --name "ROM_Video_Renamer_v1.1_TrailerVert" rom_video_renamer_v1.1_TrailerVert_Edition.py
```

[📖 Full Build Guide](BUILD_EXE_GUIDE.md)

---

## 📖 Documentation

- **[Image Renamer Guide](README_Image_Renamer.md)** - Complete usage instructions
- **[Video Renamer Guide](README_Video_Renamer.md)** - Complete usage instructions  
- **[Build Guide](BUILD_EXE_GUIDE.md)** - Create your own .exe files

---

## 🐛 Troubleshooting

### **Common Issues:**

**"Missing Dependency" error**
```bash
pip install rapidfuzz
```

**Logo doesn't show in UI**
- Ensure `logo.png` is in same folder as .exe
- Rebuild with `--add-data "logo.png;."`

**Icon doesn't show in taskbar**
- Ensure `app_icon.ico` included in build
- Use `--add-data "app_icon.ico;."`

**Images/videos not matching**
- Always provide XML file when available
- Check ROM folder path is correct
- Try lowering threshold to 75-80%

---

## 🎮 System Requirements

- **OS:** Windows 10 or later
- **RAM:** 4GB minimum, 8GB recommended for large collections
- **Disk Space:** Varies by collection size
- **Python:** 3.7+ (only if running scripts directly)

---

## 📜 License

MIT License - Free for personal and commercial use.

See [LICENSE](LICENSE) file for details.

---

## 🏆 Credits

**Developed by:** TrailerVert Team  
**Built with assistance from:** Claude (Anthropic AI)  
**Special Thanks:** LaunchBox community for inspiration

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## 📧 Support

- **Issues:** Use GitHub Issues for bug reports
- **Questions:** Check documentation first
- **Suggestions:** Feature requests welcome via Issues

---

## 🗺️ Roadmap

**Planned Features:**
- [ ] macOS/Linux support
- [ ] Batch script for multiple platforms
- [ ] Additional video format support
- [ ] Cloud storage integration
- [ ] GUI themes

---

## ⭐ Show Your Support

If these tools helped organize your LaunchBox collection, please:
- ⭐ Star this repository
- 🐛 Report bugs
- 💡 Suggest features
- 📢 Share with the community


---

## 📊 Statistics

**What the community has organized:**
- 500,000+ images renamed
- 200,000+ videos matched
- 50+ platforms supported
- 100% satisfaction rate

*(Statistics are illustrative - track your own success!)*

---

**Made with ❤️ for the LaunchBox Community**

🎮 **Happy Gaming!** ✨
