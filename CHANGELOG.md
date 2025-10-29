# Changelog

All notable changes to IG DRONES GeoTIFF Temperature Viewer.

---

## [8.1] - October 2024

### Major Features

#### Intelligent Memory Management
- Automatic file size detection before loading
- Large files (>50M pixels) automatically downsampled during load
- Memory limit: ~200MB per band to prevent crashes
- User notification dialog shows file size and downsampling factor
- Example: 10000x10000 x 11 bands → downsampled 5x to 2000x2000
- Status bar shows downsampling info

#### Smart Band Selection
- Automatically selects best temperature band from multi-band files
- Quality-based scoring algorithm (70% normal range, 30% valid data)
- Band selector hidden - no manual testing required
- Console logging shows band analysis results
- Works for Landsat, Sentinel, and custom multi-band files

#### Multi-Level Data Validation
- Three-tier classification: Normal / Unusual / Impossible
- Normal (0-50°C): Accepted without warnings
- Unusual (-60 to 0°C, 50-70°C): Accepted with warning
- Impossible (<-100°C, >100°C, NoData markers): Rejected
- Automatic filtering of NoData values (-9999, -127, etc.)

#### Intelligent Interpolation
- NoData pixels estimated from surrounding area
- Uses only normal range temperatures (0-50°C) for estimation
- Inverse distance weighting for accuracy
- Expanding search radius up to 15 pixels
- Validates interpolated results

### UI Improvements

#### Simplified Sidebar
- Removed technical details: CRS, band info, pixel coords, grid stats, quality reports
- Essential info only: File name, dimensions, location, temperature, data range
- Cleaner, more user-friendly interface

#### Professional Status Messages
- Concise progress updates during processing
- No marketing language or technical jargon
- Examples:
  - "Loading filename.tif..."
  - "Opened | 3 bands | 1495x1951px"
  - "Analyzing 3 bands..."
  - "Ready | filename | Band 1/3 | 1495x1951px"

#### Data Range Display
- Intelligent error handling with automatic fallbacks
- Shows "-" instead of error messages
- Auto-detects Kelvin vs Celsius
- Filters NoData values automatically
- 1 decimal place precision

### Technical Improvements

- Try-catch error handling with intelligent fallbacks
- Basic validation when advanced validator fails
- Silent error recovery - no error dialogs
- Automatic NoData filtering (-200 to 400 range check)
- Memory-efficient rasterio loading with out_shape parameter
- Fixed band count detection from actual loaded data

---

## [8.0] - September 2024

### Data Quality System
- Data quality validator with NoData detection
- Temperature range validation
- Quality statistics calculation
- Metadata transformation support

### Grid-Based Sampling
- 9-grid neighborhood averaging
- Adaptive grid sizing based on image resolution
- Statistical analysis per grid cell

---

## [7.0] - August 2024

### Features
- Temperature color legend
- Visual gradient display
- Dynamic range categorization

---

## [6.1] - July 2024

### Features
- Intelligent grid-based sampling
- Neighborhood averaging
- Statistical analysis

---

## [6.0] - June 2024

### Features
- Multi-band support
- Band selection UI
- RGB composite rendering
- Landsat thermal band detection

---

## Company Information

**Developer**: IG DRONES  
**Current Version**: 8.1  
**Python**: 3.10+  
**License**: MIT  

---

© 2024 IG DRONES. All rights reserved.
