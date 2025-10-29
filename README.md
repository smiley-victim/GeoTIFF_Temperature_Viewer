# 🌡️ IG DRONES GeoTIFF Temperature Viewer

[![Version](https://img.shields.io/badge/version-8.1-blue.svg)](https://github.com/yourusername/geotiff-viewer)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

> **Professional thermal analysis software for GeoTIFF files with intelligent processing and instant feedback**

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Installation](#️-installation)
- [Usage](#-usage)
- [Key Capabilities](#-key-capabilities)
- [Technical Details](#️-technical-details)
- [Building](#-building)
- [Use Cases](#-use-cases)
- [Support](#-support)

---

## ✨ Overview

A powerful desktop application for thermal analysis of GeoTIFF raster files. Built with PyQt5, featuring intelligent band selection, automatic memory management, data validation, instant visual feedback, and a professional user interface.

**Perfect for**: Agriculture monitoring, environmental analysis, urban planning, and infrastructure inspection.

---

## 🚀 Features

### 🧠 Intelligent Processing

- **🎯 Automatic Band Selection** - AI-powered scoring system (70% normal range + 30% valid data) auto-selects best temperature band
- **💾 Smart Memory Management** - Handles files up to 4GB+ with automatic downsampling (>50M pixels)
- **✅ Multi-Level Validation** - Normal (0-50°C), Unusual (-60-70°C), Impossible (<-100, >100°C) temperature ranges
- **🔄 NoData Interpolation** - Intelligent gap filling using inverse distance weighting from valid neighbors
- **🌡️ Unit Auto-Detection** - Automatically detects and converts Kelvin to Celsius

### 🎨 Modern User Experience

- **⚡ Instant Feedback** - Orange "Estimating..." popup shows processing status immediately
- **🔒 Processing Lock** - Prevents multiple simultaneous operations with user-friendly messages
- **🎭 Loading Skeleton** - Smooth pulsing animation during file loading
- **🎨 Color-Coded States** - Orange (processing), Green (success), Red (error) in sidebar
- **📍 Visual Markers** - Pin markers show clicked locations
- **🎯 Grid-Based Sampling** - 9-grid neighborhood averaging for accuracy

### 📂 File Support

- ✅ Single-band thermal GeoTIFFs
- ✅ Multi-band imagery (Landsat, Sentinel, MODIS, custom)
- ✅ RGB composite files with thermal bands
- ✅ Large files (4GB+) with auto-downsampling
- ✅ NoData values (-9999, NaN, Inf)

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10** or higher
- **Windows OS** (Windows 10/11 recommended)
- **4GB RAM** minimum (8GB+ for large files)

### ⚙️ Installation

1. **Clone or download** the repository

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

### 📖 Usage

1. **Upload** - Click "Upload GeoTIFF" button and select your file
2. **Wait** - Watch the loading skeleton animation
3. **Click** - Click anywhere on the image to sample temperature
4. **View** - See instant results in sidebar:
   - 🟠 "Estimating..." (processing)
   - 🟢 Temperature value (success)
   - 🔴 "No Data" (error)

---

## 🎯 Key Capabilities

### 📊 Instant Visual Feedback

**When you click a location:**

1. **Instant Response** (<50ms):
   - 📍 Pin marker appears
   - 🟠 Orange "Estimating..." in sidebar
   - 🔶 Orange floating popup with warning
   - 📊 Status bar updates

2. **Processing** (0.5-2s):
   - 🔄 Status shows "Searching for valid data..."
   - ⚠️ "Please wait... Avoid clicking again" warning
   - 🔒 Additional clicks blocked

3. **Result** (instant):
   - 🟢 Green temperature value in sidebar
   - 🔵 Teal popup with final result
   - ✅ Ready for next click

### 🎨 UI Elements

**File Information Card:**
- 📄 File name
- 📐 Dimensions (width × height pixels)

**Clicked Location Card:**
- 🌍 Latitude & Longitude (6 decimal places)
- 🌡️ Temperature reading with color coding:
  - 🟠 Orange = Estimating
  - 🟢 Green = Valid result
  - 🔴 Red = No data/Error

---

## 🛠️ Technical Details

### 💾 Memory Management

| File Size | Strategy | Example |
|-----------|----------|----------|
| < 50M pixels | Load full resolution | 5000×5000 → 5000×5000 |
| > 50M pixels | Auto-downsample | 10000×10000 → 2000×2000 |
| Very large | User confirmation | Shows size and downsampling factor |

**Smart Calculation:**
```python
scale_factor = √(total_pixels / 50_000_000)
downsampled_size = original_size / scale_factor
```

**Example:** 10000×10000 × 11 bands (4.4GB) → 2000×2000 (176MB)

### 🌡️ Temperature Validation

| Level | Range | Action | Color |
|-------|-------|--------|-------|
| **Normal** | 0°C to 50°C | Accept silently | 🟢 Green |
| **Unusual** | -60°C to 0°C, 50°C to 70°C | Accept with warning | 🟡 Yellow |
| **Impossible** | <-100°C, >100°C | Reject as NoData | 🔴 Red |

**Auto-Detection:**
- Values > 100 → Assumed Kelvin → Convert to Celsius
- NoData values: -9999, NaN, Inf → Filtered out

### 🎯 Sampling System

**Adaptive Grid Sizing:**

| Image Size | Grid Size | Grids | Purpose |
|------------|-----------|-------|----------|
| < 1000px | 20px | ~50 × 50 | High precision |
| 1000-5000px | 40px | ~100 × 100 | Balanced |
| 5000-10000px | 80px | ~100 × 100 | Performance |
| > 10000px | 150px | ~100 × 100 | Large datasets |

**9-Grid Averaging:**
```
[NW] [N] [NE]
[W]  [C] [E]
[SW] [S] [SE]
```
Averages clicked cell + 8 neighbors for accurate readings.

### 🔄 Interpolation System

**Dynamic Search Radius:**
- Minimum: 50 pixels
- Maximum: 20% of image dimension
- Method: Inverse distance weighting
- Neighbors: Uses only NORMAL range temperatures

**Formula:**
```python
weight = 1 / distance²
interpolated_value = Σ(value × weight) / Σ(weight)
```

---

## 📋 Status Messages

### File Loading

```
🟦 Loading filename.tif...
🟦 Opened | 11 bands | 10000x10000 px
🟦 Large file | Downsampling 5x...
🟦 Loading 11 bands...
🟦 Analyzing 11 bands for temperature...
🟦 Band 10 selected | Validating...
🟦 Generating preview...
🟢 Ready | filename.tif | Band 10/11 | 2000x2000px (downsampled 5x) | IG DRONES
```

### Click Processing

```
🟠 Analyzing location | Lat X, Lon Y | IG DRONES
🟠 Validating data...
🟠 Searching for valid data...
🟢 Estimated: 28.5°C | IG DRONES
```

### User Feedback

```
🔴 Processing... Please wait | IG DRONES  (when clicking during estimation)
🔴 No data available at this location | IG DRONES
🔴 File loading cancelled | IG DRONES
```

---

## 📦 Building

### Windows Executable

**Using build script:**
```bash
python build_exe.py
```

**Manual build:**
```bash
pyinstaller --onefile --windowed \
  --name "IG_DRONES_GeoTIFF_Viewer_v8.1" \
  --icon=logo/igdrones.ico \
  --add-data "logo/igdrones.ico;logo" \
  app.py
```

**Output:**
- Executable: `dist/IG_DRONES_GeoTIFF_Viewer_v8.1.exe`
- Size: ~100MB (includes Python + libraries)
- Dependencies: None (standalone)

### Android APK

⚠️ **Not supported** - PyQt5 is not compatible with Android. Consider:
- **Alternative**: Rewrite using Kivy or React Native
- **Web App**: Deploy as Flask/Django web application
- **Remote Desktop**: Use Windows app via RDP

---

## 📚 Dependencies

### Core Requirements

```txt
PyQt5 >= 5.15.9          # GUI framework
rasterio >= 1.3.9        # GeoTIFF reading
numpy >= 1.24.0          # Array operations
Pillow >= 10.0.0         # Image processing
matplotlib >= 3.7.0      # Color mapping
```

### Full `requirements.txt`

```bash
PyQt5==5.15.9
PyQt5-Qt5==5.15.2
PyQt5-sip==12.12.1
rasterio==1.3.9
numpy==1.24.3
Pillow==10.0.0
matplotlib==3.7.2
affine==2.4.0
click==8.1.7
click-plugins==1.1.1
cligj==0.7.2
attrs==23.1.0
certifi==2023.7.22
```

**Install all:**
```bash
pip install -r requirements.txt
```

---

## 🌍 Use Cases

### 🌾 Agriculture

- **Crop Stress Detection** - Identify water-stressed areas
- **Irrigation Optimization** - Monitor field moisture distribution
- **Yield Prediction** - Correlate temperature with crop health
- **Pest Detection** - Early identification of infested areas

### 🌲 Environmental Monitoring

- **Water Temperature** - Lake and river thermal analysis
- **Forest Health** - Detect stressed or diseased vegetation
- **Climate Research** - Long-term temperature pattern analysis
- **Wildlife Habitat** - Thermal comfort zone mapping

### 🏙️ Urban Planning

- **Heat Island Mapping** - Identify urban hot spots
- **Building Efficiency** - Detect heat loss in structures
- **Infrastructure Monitoring** - Thermal anomaly detection
- **Energy Management** - Optimize cooling/heating systems

### 🏭 Industrial

- **Equipment Monitoring** - Detect overheating machinery
- **Solar Panel Inspection** - Identify faulty panels
- **Pipeline Monitoring** - Detect leaks via thermal signatures
- **Quality Control** - Manufacturing process temperature verification

---

## 📅 Version History

### v8.1 (Current) - Enhanced Intelligence & UX

**Major Features:**
- ⚡ Instant visual feedback with "Estimating..." popup
- 🔒 Processing lock prevents multiple simultaneous operations
- 🎭 Loading skeleton with smooth pulsing animation
- 🎨 Color-coded UI states (Orange/Green/Red)
- 💾 Intelligent memory management (>4GB files supported)
- 🎯 Automatic band selection (AI-powered scoring)
- ✅ Multi-level temperature validation
- 🔄 NoData interpolation with dynamic search radius

**UI Improvements:**
- Removed unnecessary clutter (emojis, marketing text)
- Simplified sidebar (File, Dimensions, Location, Temperature)
- Professional status messages
- Clean data range display with intelligent formatting

**Bug Fixes:**
- Fixed sticky popup issue with rapid clicking
- Fixed band count display for RGB composites
- Fixed large file dialog cancellation
- Fixed processing flag reset in error cases

### Previous Versions

- **v8.0** - Data Quality & Validation
- **v7.0** - Visual Enhancements & Color Legend
- **v6.1** - Grid System & Neighborhood Averaging
- **v6.0** - Multi-Band Support & Basic Loading

See [COMPLETE_PROJECT_DOCUMENTATION.md](COMPLETE_PROJECT_DOCUMENTATION.md) for full details.

---

## 👥 Team & Credits

**Developed by:** IG DRONES  
**Version:** 8.1  
**Platform:** Windows Desktop  
**Framework:** PyQt5  
**Python:** 3.10+  
**License:** MIT  

### Technologies Used

- **PyQt5** - Cross-platform GUI framework
- **Rasterio** - Geospatial raster I/O
- **NumPy** - Numerical computing
- **Matplotlib** - Color mapping and visualization
- **Pillow** - Image processing

---

## 📞 Support

### Documentation

- **Quick Reference**: This README.md
- **Complete Guide**: [COMPLETE_PROJECT_DOCUMENTATION.md](COMPLETE_PROJECT_DOCUMENTATION.md)
- **Technical Details**: See inline code comments

### Troubleshooting

**Issue**: Application crashes with large files  
**Solution**: Use automatic downsampling (accept dialog prompt)

**Issue**: "No data available" message  
**Solution**: Click on area with valid temperature data

**Issue**: "Processing... Please wait" when clicking  
**Solution**: Wait for current operation to complete

**Issue**: Temperature values seem wrong  
**Solution**: Check if values are in Kelvin (auto-converts if >100)

### Contact

For issues, questions, or feature requests, please refer to the documentation or contact IG DRONES.

---

## 📄 License

**MIT License**

Copyright © 2024 IG DRONES. All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## ⭐ Acknowledgments

Built with ❤️ by **IG DRONES** for professional thermal analysis.

**Special thanks to:**
- The Rasterio community for excellent geospatial tools
- The PyQt5 team for the powerful GUI framework
- All users providing feedback for continuous improvement

---

<div align="center">

**🌡️ IG DRONES GeoTIFF Temperature Viewer v8.1**

*Professional thermal analysis made simple*

[⬆ Back to top](#)

</div>
