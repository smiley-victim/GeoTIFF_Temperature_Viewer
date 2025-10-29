# IG DRONES - GeoTIFF Temperature Viewer v8.1

**Professional Desktop Application for Thermal Analysis of GeoTIFF Files**

---

## Overview

A powerful PyQt5-based desktop application designed for professional thermal analysis of GeoTIFF raster files. Features intelligent band selection, automatic memory management, data validation, and an intuitive interface.

---

## Key Features

### Intelligent Processing
- **Smart Band Selection** - Automatically selects the best temperature band based on data quality
- **Memory Management** - Handles large files (>50M pixels) with automatic downsampling
- **Data Validation** - Filters NoData values and validates temperature ranges
- **Auto Unit Detection** - Automatically detects and converts Kelvin to Celsius

### User Interface
- **Clean Sidebar** - Essential information only (File, Dimensions, Location, Temperature, Range)
- **Grid-Based Sampling** - 9-grid neighborhood averaging for accurate readings
- **Real-Time Status** - Progress messages show what's happening during processing
- **Visual Markers** - Pin markers show where you clicked for sampling

### File Support
- Single-band thermal GeoTIFFs
- Multi-band thermal imagery (Landsat, Sentinel, custom)
- RGB composite files
- Large files with automatic downsampling

---

## Quick Start

### Installation

1. **Install Python 3.10+**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Usage

```bash
python app.py
```

1. Click "Upload GeoTIFF" button
2. Select your GeoTIFF file
3. Click anywhere on the image to sample temperature
4. View results in the sidebar (coordinates, temperature, data range)

---

## Sidebar Information

### File Information
- File name
- Dimensions (width x height pixels)

### Clicked Location
- Latitude & Longitude
- Temperature reading

### Data Range
- Minimum temperature
- Maximum temperature
- Mean temperature

---

## Technical Features

### Memory Efficiency
- **Threshold**: 50M pixels (~200MB per band)
- **Automatic Downsampling**: Large files downsampled during load
- **User Notification**: Dialog shows file size and downsampling factor
- **Example**: 10000x10000 x 11 bands → downsampled 5x to 2000x2000

### Temperature Processing
- **Auto Kelvin Detection**: Values > 100 assumed Kelvin
- **Conversion**: Celsius = Kelvin - 273.15
- **Validation**: Filters impossible values (-9999, NaN, Inf)
- **Range**: Accepts -60°C to 70°C (warns on extremes)

### Sampling Accuracy
- **9-Grid Averaging**: Uses clicked cell + 8 neighbors
- **Adaptive Grid**: 
  - Small (<1000px): 20px cells
  - Medium (1000-5000px): 40px cells
  - Large (5000-10000px): 80px cells
  - Very Large (>10000px): 150px cells

---

## Status Messages

The application provides real-time feedback:

- `Loading filename.tif...` - Opening file
- `Opened | X bands | WxH px` - File loaded
- `Loading X bands...` - Reading data
- `Analyzing X bands...` - Finding best band
- `Band X selected | Validating...` - Quality check
- `Calculating statistics...` - Min/max/mean
- `Generating preview...` - Creating display
- `Ready | filename | Band X/Y | WxH` - Ready to use

For large files:
- `Large file | Downsampling Xx...` - Memory optimization
- `Ready | ... (downsampled Xx)` - Shows downsampling applied

---

## Building Executable

Create standalone Windows executable:

```bash
python build_exe.py
```

Or manually:

```bash
pyinstaller --onefile --windowed --name "IG_DRONES_GeoTIFF_Viewer" --icon=logo/igdrones.ico app.py
```

Executable will be in `dist/` folder.

---

## Requirements

```
PyQt5 >= 5.15.9
rasterio >= 1.3.9
numpy >= 1.24.0
Pillow >= 10.0.0
matplotlib >= 3.7.0
```

---

## Use Cases

### Agriculture
- Crop stress detection
- Irrigation monitoring
- Field uniformity analysis

### Environmental
- Water temperature monitoring
- Forest health assessment
- Climate studies

### Urban Planning
- Heat island mapping
- Building efficiency
- Infrastructure monitoring

---

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

**Current Version: 8.1**
- Intelligent memory management
- Automatic band selection
- Data validation and quality control
- Simplified UI with essential information
- Professional status messages

---

## Company Information

**Developer**: IG DRONES  
**Version**: 8.1  
**Python**: 3.10+  
**License**: MIT  

---

## Support

For issues or questions, please refer to the [CHANGELOG.md](CHANGELOG.md) for feature documentation.

---

© 2024 IG DRONES. All rights reserved.
