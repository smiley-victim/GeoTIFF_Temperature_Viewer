"""
IG DRONES - GeoTIFF Temperature Viewer v8.1

A professional desktop application for viewing and querying temperature data 
from GeoTIFF raster files with full multi-band support and intelligent grid-based sampling.

Company: IG DRONES
Python Version: 3.10+
License: MIT

Features v8.1:
- **Multi-Level Validation** ⭐ ENHANCED - Normal/Unusual/Impossible classification
- **Smart Range Detection** ⭐ ENHANCED - Accepts extreme but valid temps (-48°C, 65°C)
- **Context-Aware Warnings** ⭐ NEW - Explains why temperature is unusual
- **Data Quality Validation** - Proper NoData value handling and masking
- **Physical Range Validation** - Reject impossible temperatures (-110°C bug fixed!)
- **Smart Temperature Detection** - Improved Kelvin/Celsius auto-detection
- **Metadata Reading** - Apply scale factors and offsets from file
- **Data Quality Report** - Show data validity statistics
- **Temperature Color Legend** - Visual guide showing temperature ranges by color
- **Dynamic Color Mapping** - Automatic categorization (Cold/Average/Hot) based on data
- **Enhanced Visual Feedback** - Gradient display with precise temperature ranges
- **Grid-Based Sampling** - Intelligent averaging of grid cells for accurate readings
- **Adaptive Grid System** - Automatic grid sizing based on image resolution
- **Statistical Analysis** - Shows mean, min, max, std dev per grid cell
- **Optional Grid Overlay** - Toggle grid visualization for analysis
- **Multi-band Detection** - Automatic detection of single vs multi-band files
- **Band Selection UI** - Dropdown selector for multi-band GeoTIFFs
- **RGB Composite Rendering** - True color display for multi-spectral imagery
- **Landsat 8/9 Support** - Native support for thermal bands (Band 10/11)
- **Intelligent Rendering** - Auto-detect and render RGB or thermal appropriately
- Visual click marker for sampled locations
- Enhanced temperature display (shows both Kelvin and Celsius)
- Floating info label on click
- Smooth zoom and pan with QGraphicsView
- Efficient rendering for large GeoTIFFs
- Accurate temperature sampling from full resolution
- Geographic coordinate conversion
- Automatic Kelvin to Celsius conversion

Usage:
    python app.py

Building to .exe:
    pyinstaller --onefile --windowed --name "IG_DRONES_GeoTIFF_Viewer" app.py
"""

import sys
import os
from typing import Optional
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

# Windows-specific: Fix taskbar icon
if sys.platform == 'win32':
    import ctypes
    # Set AppUserModelID to make Windows use our custom icon in taskbar
    myappid = 'igdrones.geotiff.viewer.8.1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QStatusBar, QMessageBox,
    QSizePolicy, QFrame, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsEllipseItem, QComboBox, QGroupBox, QSplitter, QScrollArea
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import (
    QPixmap, QImage, QWheelEvent, QMouseEvent, QColor, QPainter, 
    QPen, QBrush, QIcon, QLinearGradient, QFont
)


class DataQualityValidator:
    """
    Validates GeoTIFF temperature data quality (v8.0 Enhanced).
    
    Handles:
    - NoData value masking
    - Multi-level temperature validation (Impossible/Unusual/Normal)
    - Metadata scale/offset application
    - Data quality reporting
    """
    
    # Temperature range levels (v8.0 Enhanced)
    # Level 1: NORMAL - Typical earth surface temperatures (most data should be here)
    NORMAL_MIN = 0.0     # 0°C - Freezing point
    NORMAL_MAX = 50.0    # 50°C - Hot but common
    
    # Level 2: UNUSUAL - Valid but rare (extreme weather, special conditions)
    UNUSUAL_MIN = -60.0  # -60°C - Extreme cold (Antarctica, Arctic)
    UNUSUAL_MAX = 70.0   # 70°C - Extreme hot (Death Valley, desert surfaces)
    
    # Level 3: IMPOSSIBLE - Likely NoData or errors (reject these)
    IMPOSSIBLE_MIN = -100.0  # Below this = definitely NoData
    IMPOSSIBLE_MAX = 100.0   # Above this = definitely NoData or error
    
    # Kelvin equivalents
    KELVIN_NORMAL_MIN = 273.15  # 0°C
    KELVIN_NORMAL_MAX = 323.15  # 50°C
    KELVIN_UNUSUAL_MIN = 213.15  # -60°C
    KELVIN_UNUSUAL_MAX = 343.15  # 70°C
    
    def __init__(self, dataset: rasterio.DatasetReader, band_index: int = 1):
        """
        Initialize validator with GeoTIFF dataset.
        
        Args:
            dataset: Rasterio dataset object
            band_index: Band number (1-indexed)
        """
        self.dataset = dataset
        self.band_index = band_index
        
        # Read metadata
        self.nodata_value = dataset.nodata
        self.scale = dataset.scales[band_index - 1] if dataset.scales else 1.0
        self.offset = dataset.offsets[band_index - 1] if dataset.offsets else 0.0
        
        # Data quality stats
        self.valid_percentage = 0.0
        self.quality_level = "Unknown"
        self.total_pixels = 0
        self.valid_pixels = 0
        
    def apply_metadata_transforms(self, data: np.ndarray) -> np.ndarray:
        """
        Apply scale and offset from GeoTIFF metadata.
        
        Formula: value = (raw_value × scale) + offset
        
        Args:
            data: Raw data array
            
        Returns:
            Transformed data array
        """
        if self.scale != 1.0 or self.offset != 0.0:
            return (data * self.scale) + self.offset
        return data
    
    def create_valid_mask(self, data: np.ndarray) -> np.ndarray:
        """
        Create boolean mask for valid temperature data (v8.0 Enhanced).
        
        Only masks out IMPOSSIBLE values (likely NoData markers).
        Accepts UNUSUAL values (-48°C, 65°C, etc.) as valid.
        
        Masks out:
        - NoData values from file metadata
        - NaN and Inf values
        - IMPOSSIBLE temperatures (< -100°C or > 100°C - definitely errors)
        
        Args:
            data: Temperature data array
            
        Returns:
            Boolean mask (True = valid, False = invalid/impossible)
        """
        mask = np.ones_like(data, dtype=bool)
        
        # Mask NoData values from metadata
        if self.nodata_value is not None:
            tolerance = 0.01  # For floating point comparison
            mask &= ~np.isclose(data, self.nodata_value, atol=tolerance)
        
        # Mask NaN and Inf
        mask &= np.isfinite(data)
        
        # Only mask IMPOSSIBLE temperatures (not unusual ones!)
        # Check if data is in Kelvin or Celsius range
        data_min = np.nanmin(data[mask]) if np.any(mask) else 0
        data_max = np.nanmax(data[mask]) if np.any(mask) else 0
        
        if data_min > 100:  # Likely Kelvin
            # Only reject truly impossible Kelvin values
            mask &= (data >= 150.0) & (data <= 400.0)  # Very wide range
        else:  # Likely Celsius
            # Only reject impossible Celsius (NoData markers like -9999, etc.)
            mask &= (data >= self.IMPOSSIBLE_MIN) & (data <= self.IMPOSSIBLE_MAX)
        
        return mask
    
    def get_valid_data(self, data: np.ndarray) -> np.ndarray:
        """
        Get only valid temperature values from data.
        
        Args:
            data: Temperature data array
            
        Returns:
            1D array of valid temperature values
        """
        mask = self.create_valid_mask(data)
        return data[mask]
    
    def calculate_quality_stats(self, data: np.ndarray) -> dict:
        """
        Calculate data quality statistics.
        
        Args:
            data: Temperature data array
            
        Returns:
            Dictionary with quality metrics
        """
        mask = self.create_valid_mask(data)
        
        self.total_pixels = data.size
        self.valid_pixels = np.sum(mask)
        self.valid_percentage = (self.valid_pixels / self.total_pixels * 100) if self.total_pixels > 0 else 0.0
        
        # Determine quality level
        if self.valid_percentage >= 95:
            self.quality_level = "Excellent"
        elif self.valid_percentage >= 80:
            self.quality_level = "Good"
        elif self.valid_percentage >= 60:
            self.quality_level = "Fair"
        elif self.valid_percentage >= 30:
            self.quality_level = "Poor"
        else:
            self.quality_level = "Very Poor"
        
        return {
            'valid_percentage': self.valid_percentage,
            'quality_level': self.quality_level,
            'valid_pixels': self.valid_pixels,
            'total_pixels': self.total_pixels,
            'has_nodata': self.nodata_value is not None,
            'nodata_value': self.nodata_value,
            'scale': self.scale,
            'offset': self.offset
        }
    
    def detect_temperature_unit(self, data: np.ndarray) -> str:
        """
        Intelligently detect if data is in Kelvin or Celsius.
        
        Args:
            data: Temperature data array
            
        Returns:
            'Kelvin', 'Celsius', or 'Unknown'
        """
        valid_data = self.get_valid_data(data)
        
        if len(valid_data) == 0:
            return "Unknown"
        
        data_min = np.min(valid_data)
        data_max = np.max(valid_data)
        data_mean = np.mean(valid_data)
        
        # Kelvin range check
        if self.KELVIN_MIN <= data_min and data_max <= self.KELVIN_MAX:
            if data_mean > 200:  # Strong indicator of Kelvin
                return "Kelvin"
        
        # Celsius range check  
        if self.CELSIUS_MIN <= data_min and data_max <= self.CELSIUS_MAX:
            if data_mean < 100:  # Strong indicator of Celsius
                return "Celsius"
        
        # Ambiguous case - use heuristics
        if data_min > 100:
            return "Kelvin (assumed)"
        else:
            return "Celsius (assumed)"
    
    def classify_temperature_level(self, value: float) -> str:
        """
        Classify temperature into Normal/Unusual/Impossible (v8.0 Enhanced).
        
        Args:
            value: Temperature value
            
        Returns:
            'normal', 'unusual', or 'impossible'
        """
        # Detect if Kelvin or Celsius
        if value > 100:  # Likely Kelvin
            if self.KELVIN_NORMAL_MIN <= value <= self.KELVIN_NORMAL_MAX:
                return "normal"
            elif self.KELVIN_UNUSUAL_MIN <= value <= self.KELVIN_UNUSUAL_MAX:
                return "unusual"
            else:
                return "impossible"
        else:  # Likely Celsius
            if self.NORMAL_MIN <= value <= self.NORMAL_MAX:
                return "normal"
            elif self.UNUSUAL_MIN <= value <= self.UNUSUAL_MAX:
                return "unusual"
            else:
                return "impossible"
    
    def validate_single_value(self, value: float) -> tuple[bool, str, str]:
        """
        Validate a single temperature value with multi-level classification (v8.0 Enhanced).
        
        Now returns 3 values: (is_usable, message, level)
        - is_usable: True if we should display it (Normal or Unusual), False if Impossible
        - message: Description for user
        - level: 'normal', 'unusual', or 'impossible'
        
        Args:
            value: Temperature value to validate
            
        Returns:
            Tuple of (is_usable, message, level)
        """
        # Check for NoData from metadata
        if self.nodata_value is not None and np.isclose(value, self.nodata_value, atol=0.01):
            return False, "NoData value (from metadata)", "impossible"
        
        # Check for NaN/Inf
        if not np.isfinite(value):
            return False, "Invalid (NaN or Inf)", "impossible"
        
        # Classify temperature level
        level = self.classify_temperature_level(value)
        
        if level == "normal":
            # Typical temperature - show with checkmark
            return True, "Normal range", "normal"
        
        elif level == "unusual":
            # Extreme but valid - show with warning
            if value < 0:
                return True, f"Extreme cold ({value:.1f}°C - Arctic/Antarctic)", "unusual"
            else:
                return True, f"Extreme hot ({value:.1f}°C - Desert surface)", "unusual"
        
        else:  # impossible
            # Likely NoData or error - reject
            return False, f"Impossible value ({value:.1f}) - likely NoData", "impossible"
    
    def interpolate_from_neighbors(self, data: np.ndarray, row: int, col: int, 
                                   max_radius: int = 15) -> tuple[bool, float, int, int]:
        """
        Interpolate temperature from nearby NORMAL pixels (v8.1 - CONSERVATIVE Approach).
        
        Searches in expanding circles to find NORMAL range neighbors ONLY (0-50°C).
        Uses inverse distance weighting for more accurate interpolation.
        
        CONSERVATIVE VALIDATION - ONLY NORMAL RANGE:
        - Only uses neighbors with temperatures between 0°C and 50°C (NORMAL range)
        - Rejects UNUSUAL temps (-46°C, 65°C) - these are treated as suspect
        - Rejects IMPOSSIBLE values (-9999, -127, etc.)
        - Validates the interpolated result is also within NORMAL range (0-50°C)
        - Gives balanced, typical temperatures from normal neighbors only
        
        Args:
            data: Temperature data array
            row: Row index of pixel to interpolate
            col: Column index of pixel to interpolate
            max_radius: Maximum search radius in pixels (default: 15)
            
        Returns:
            Tuple of (success, interpolated_value, valid_neighbors_found, search_radius_used)
        """
        height, width = data.shape
        
        # Try expanding search radius
        for radius in range(1, max_radius + 1):
            valid_values = []
            distances = []
            
            # Search in a square around the point
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if dr == 0 and dc == 0:
                        continue  # Skip center pixel
                    
                    r = row + dr
                    c = col + dc
                    
                    # Check bounds
                    if 0 <= r < height and 0 <= c < width:
                        value = data[r, c]
                        
                        # STRICT VALIDATION: Only use physically reasonable neighbors
                        
                        # 1. Check NoData value
                        if self.nodata_value is not None:
                            if np.isclose(value, self.nodata_value, atol=0.01):
                                continue
                        
                        # 2. Check NaN/Inf
                        if not np.isfinite(value):
                            continue
                        
                        # 3. CONSERVATIVE range check - ONLY accept NORMAL temperatures
                        # Convert to Celsius for checking
                        if value > 100:  # Likely Kelvin
                            temp_celsius = value - 273.15
                        else:
                            temp_celsius = value
                        
                        # ONLY accept NORMAL temperatures (0°C to 50°C) for interpolation
                        # This gives balanced, typical temperatures
                        # Rejects: NoData (-9999), extreme cold (-46°C), extreme hot (65°C), etc.
                        if temp_celsius < self.NORMAL_MIN or temp_celsius > self.NORMAL_MAX:
                            continue  # Skip - not in NORMAL range
                        
                        # Valid pixel found!
                        valid_values.append(value)
                        distance = np.sqrt(dr**2 + dc**2)
                        distances.append(distance)
            
            # If we found valid neighbors, interpolate
            if len(valid_values) >= 3:  # Need at least 3 valid neighbors for good estimate
                # Inverse distance weighting (closer pixels have more influence)
                weights = 1.0 / np.array(distances)
                weights = weights / np.sum(weights)  # Normalize
                
                interpolated = np.average(valid_values, weights=weights)
                
                # VALIDATE THE INTERPOLATED RESULT!
                # Convert to Celsius for final check
                if interpolated > 100:  # Kelvin
                    result_celsius = interpolated - 273.15
                else:
                    result_celsius = interpolated
                
                # Final sanity check - result must be within NORMAL range (0 to 50°C)
                # This ensures we only return balanced, typical temperatures
                if result_celsius < self.NORMAL_MIN or result_celsius > self.NORMAL_MAX:
                    # Interpolated result is outside normal range - reject it!
                    continue  # Try larger radius
                
                # Result is valid and NORMAL!
                return True, interpolated, len(valid_values), radius
        
        # No valid neighbors found within max_radius
        return False, np.nan, 0, max_radius


class ColorLegendWidget(QWidget):
    """Custom widget to display temperature color legend with gradient."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setMaximumHeight(220)
        
        # Temperature ranges (will be updated dynamically)
        self.cold_range = (0, 10)
        self.average_range = (10, 25)
        self.hot_range = (25, 50)
        
        # Color definitions matching thermal visualization
        self.cold_color = QColor(0, 0, 255)  # Blue
        self.average_color = QColor(0, 255, 0)  # Green
        self.hot_color = QColor(255, 0, 0)  # Red
        
        self.has_data = False
        
    def update_ranges(self, min_temp: float, max_temp: float):
        """Update temperature ranges based on actual data."""
        self.has_data = True
        temp_span = max_temp - min_temp
        
        # Intelligent categorization
        # Cold: min to 33rd percentile
        # Average: 33rd to 67th percentile  
        # Hot: 67th percentile to max
        
        third = temp_span / 3.0
        self.cold_range = (min_temp, min_temp + third)
        self.average_range = (min_temp + third, min_temp + 2 * third)
        self.hot_range = (min_temp + 2 * third, max_temp)
        
        self.update()  # Trigger repaint
        
    def paintEvent(self, event):
        """Custom paint event to draw gradient and labels."""
        if not self.has_data:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Define gradient bar dimensions
        bar_x = 20
        bar_width = self.width() - 40
        bar_y = 40
        bar_height = 80
        
        # Create gradient
        gradient = QLinearGradient(bar_x, bar_y, bar_x + bar_width, bar_y)
        gradient.setColorAt(0.0, self.cold_color)
        gradient.setColorAt(0.5, self.average_color)
        gradient.setColorAt(1.0, self.hot_color)
        
        # Draw gradient bar
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(85, 85, 85), 2))
        painter.drawRoundedRect(bar_x, bar_y, bar_width, bar_height, 5, 5)
        
        # Draw temperature labels
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Segoe UI", 9, QFont.Bold)
        painter.setFont(font)
        
        # Cold label (left)
        cold_text = f"COLD\n{self.cold_range[0]:.1f}°C - {self.cold_range[1]:.1f}°C"
        painter.drawText(bar_x - 5, bar_y + bar_height + 15, cold_text.replace('\n', ' '))
        
        # Average label (center)
        avg_x = bar_x + bar_width // 2 - 40
        avg_text = f"AVERAGE\n{self.average_range[0]:.1f}°C - {self.average_range[1]:.1f}°C"
        painter.drawText(avg_x, bar_y + bar_height + 35, avg_text.replace('\n', ' '))
        
        # Hot label (right)
        hot_x = bar_x + bar_width - 80
        hot_text = f"HOT\n{self.hot_range[0]:.1f}°C - {self.hot_range[1]:.1f}°C"
        painter.drawText(hot_x, bar_y + bar_height + 55, hot_text.replace('\n', ' '))
        
        # Draw color indicators
        indicator_size = 15
        painter.setBrush(QBrush(self.cold_color))
        painter.drawEllipse(bar_x, bar_y - 20, indicator_size, indicator_size)
        
        painter.setBrush(QBrush(self.average_color))
        painter.drawEllipse(bar_x + bar_width // 2 - indicator_size // 2, bar_y - 20, indicator_size, indicator_size)
        
        painter.setBrush(QBrush(self.hot_color))
        painter.drawEllipse(bar_x + bar_width - indicator_size, bar_y - 20, indicator_size, indicator_size)


class InteractiveGraphicsView(QGraphicsView):
    """Custom QGraphicsView with zoom and pan capabilities for raster display."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setBackgroundBrush(QColor(37, 37, 37))
        
        self._zoom = 0
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._pin_marker: Optional[QGraphicsEllipseItem] = None
        
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        if event.angleDelta().y() > 0:
            factor = 1.25
            self._zoom += 1
        else:
            factor = 0.8
            self._zoom -= 1
        
        # Limit zoom levels
        if self._zoom > 15:
            self._zoom = 15
            return
        elif self._zoom < -10:
            self._zoom = -10
            return
            
        self.scale(factor, factor)
        
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for click-to-sample and panning."""
        if event.button() == Qt.LeftButton:
            # Check if clicking on the image (not just panning)
            scene_pos = self.mapToScene(event.pos())
            if self._pixmap_item and self._pixmap_item.contains(scene_pos):
                # Convert scene coordinates to image pixel coordinates
                item_pos = self._pixmap_item.mapFromScene(scene_pos)
                pixel_x = int(item_pos.x())
                pixel_y = int(item_pos.y())
                
                # Notify parent widget for temperature sampling
                if self.parent_widget and hasattr(self.parent_widget, 'on_image_click'):
                    self.parent_widget.on_image_click(pixel_x, pixel_y)
        
        # Call parent for drag functionality
        super().mousePressEvent(event)
        
    def set_image(self, pixmap: QPixmap):
        """Set the image to display in the view."""
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._pin_marker = None  # Reset marker reference
        self._scene.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
        self._zoom = 0
    
    def add_pin_marker(self, x: float, y: float):
        """Add a visual pin marker at the specified coordinates."""
        # Remove existing marker if any
        if self._pin_marker:
            self._scene.removeItem(self._pin_marker)
        
        # Create a red circular marker
        radius = 8
        pen = QPen(QColor(255, 0, 0), 3)  # Red outline
        brush = QBrush(QColor(255, 100, 100, 180))  # Semi-transparent red fill
        
        self._pin_marker = self._scene.addEllipse(
            x - radius, y - radius, 
            radius * 2, radius * 2,
            pen, brush
        )
        # Keep marker on top
        self._pin_marker.setZValue(1000)
    
    def clear_pin_marker(self):
        """Remove the pin marker from the scene."""
        if self._pin_marker:
            self._scene.removeItem(self._pin_marker)
            self._pin_marker = None
        
    def reset_view(self):
        """Reset zoom and pan to original state."""
        if self._pixmap_item:
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
            self._zoom = 0
        self.clear_pin_marker()


class GeoTIFFViewer(QMainWindow):
    """Main application window for IG DRONES GeoTIFF Temperature Viewer."""
    
    def __init__(self):
        super().__init__()
        self.geotiff_path: Optional[Path] = None
        self.dataset: Optional[rasterio.DatasetReader] = None
        self.raster_data: Optional[np.ndarray] = None  # Full resolution data (can be 2D or 3D)
        self.preview_data: Optional[np.ndarray] = None  # Downsampled preview
        self.transform = None
        self.crs = None
        self.preview_scale_x: float = 1.0  # Scale factor from preview to full res
        self.preview_scale_y: float = 1.0
        
        # Multi-band support (v6.0)
        self.band_count: int = 0
        self.current_band: int = 1  # Currently selected band for temperature sampling
        self.display_mode: str = "SINGLE_BAND"  # SINGLE_BAND, RGB_COMPOSITE, or THERMAL_MULTIBAND
        self.band_descriptions: dict = {}  # Store band metadata
        
        # Grid-based sampling (v6.1)
        self.grid_enabled: bool = True  # Enable intelligent grid-based averaging
        self.grid_size: int = 50  # Default grid cell size in pixels (adaptive)
        self.show_grid_overlay: bool = False  # Toggle grid visualization
        self.grid_rows: int = 0
        self.grid_cols: int = 0
        
        # Neighborhood averaging (v6.1)
        self.neighborhood_averaging: bool = True  # Use 9-grid (3x3) neighborhood averaging
        self.grid_averages: dict = {}  # Cache grid averages for performance
        
        # Temperature range tracking (v7.0)
        self.current_min_temp: Optional[float] = None
        self.current_max_temp: Optional[float] = None
        
        # Data quality validation (v8.0)
        self.validator: Optional[DataQualityValidator] = None  # Data quality validator
        self.data_quality_stats: dict = {}  # Quality statistics
        
        # UI elements that need to be referenced
        self.info_panel: Optional[QFrame] = None  # Sidebar panel reference
        
        # Last clicked location for band switching re-sampling (v6.1 enhancement)
        self.last_click_preview_x: Optional[int] = None
        self.last_click_preview_y: Optional[int] = None
        self.last_click_raster_x: Optional[int] = None
        self.last_click_raster_y: Optional[int] = None
        
        # Floating info label for showing temperature on click
        self.floating_label: Optional[QLabel] = None
        self.floating_timer: Optional[QTimer] = None
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("IG DRONES - GeoTIFF Temperature Viewer v8.1")
        self.setGeometry(100, 100, 1400, 900)
        
        # Set IG DRONES custom icon (works for both dev and .exe)
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = Path(__file__).parent
        
        icon_path = Path(base_path) / "logo" / "igdrones.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            # Fallback: try PNG if ICO not found
            icon_path_png = Path(base_path) / "logo" / "igdrones.png"
            if icon_path_png.exists():
                self.setWindowIcon(QIcon(str(icon_path_png)))
        
        # Apply Fusion style for modern look
        QApplication.setStyle("Fusion")
        self.apply_dark_theme()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Top control bar
        control_layout = QHBoxLayout()
        
        self.upload_btn = QPushButton("Upload GeoTIFF")
        self.upload_btn.setToolTip("Load a GeoTIFF (.tif) file for temperature analysis")
        self.upload_btn.clicked.connect(self.upload_geotiff)
        self.upload_btn.setMinimumHeight(40)
        
        self.reset_btn = QPushButton("Reset View")
        self.reset_btn.setToolTip("Reset zoom and pan to fit image")
        self.reset_btn.clicked.connect(self.reset_view)
        self.reset_btn.setEnabled(False)
        self.reset_btn.setMinimumHeight(40)
        
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setToolTip("Close the application")
        self.exit_btn.clicked.connect(self.close)
        self.exit_btn.setMinimumHeight(40)
        
        # Instructions label
        instructions_label = QLabel("Mouse Wheel: Zoom | Left Click & Drag: Pan | Click: Sample Temperature")
        instructions_label.setStyleSheet("color: #14FFEC; font-size: 11px; padding: 5px;")
        
        control_layout.addWidget(self.upload_btn)
        control_layout.addWidget(self.reset_btn)
        control_layout.addWidget(instructions_label)
        control_layout.addStretch()
        control_layout.addWidget(self.exit_btn)
        
        main_layout.addLayout(control_layout)
        
        # Content area with RESIZABLE splitter (v6.1 - IDE-style resizing)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(6)  # Draggable handle width
        
        # Interactive graphics view for image display
        self.graphics_view = InteractiveGraphicsView(self)
        self.graphics_view.setMinimumSize(600, 500)
        self.splitter.addWidget(self.graphics_view)
        
        # Info panel (resizable by dragging divider)
        self.info_panel = QFrame()
        self.info_panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.info_panel.setMinimumWidth(250)  # Minimum width
        self.info_panel.setMaximumWidth(800)  # Maximum width (flexible)
        self.info_panel.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555;")
        
        # Scrollable container for sidebar content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #2b2b2b;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #14FFEC;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #0d7377;
            }
        """)
        
        scroll_content = QWidget()
        info_layout = QVBoxLayout()
        info_layout.setSpacing(12)
        info_layout.setContentsMargins(10, 10, 10, 10)
        scroll_content.setLayout(info_layout)
        scroll_area.setWidget(scroll_content)
        
        # Set scroll area as panel layout
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(0, 0, 0, 0)
        self.info_panel.setLayout(panel_layout)
        panel_layout.addWidget(scroll_area)
        
        # Modern card style CSS
        card_style = """
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                stop:0 #323232, stop:1 #2b2b2b);
            border: 1px solid #404040;
            border-radius: 8px;
            padding: 12px;
        """
        
        # Company branding - Modern header
        brand_container = QFrame()
        brand_container.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0d7377, stop:0.5 #14FFEC, stop:1 #0d7377);
            border-radius: 8px;
            padding: 2px;
        """)
        brand_layout = QVBoxLayout()
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_container.setLayout(brand_layout)
        
        brand_inner = QFrame()
        brand_inner.setStyleSheet("background-color: #1e1e1e; border-radius: 6px;")
        brand_inner_layout = QVBoxLayout()
        brand_inner.setLayout(brand_inner_layout)
        
        brand_label = QLabel("IG DRONES")
        brand_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #14FFEC; padding: 8px;")
        brand_label.setAlignment(Qt.AlignCenter)
        brand_inner_layout.addWidget(brand_label)
        
        brand_subtitle = QLabel("GeoTIFF Temperature Viewer v8.1")
        brand_subtitle.setStyleSheet("font-size: 10px; color: #aaa; padding-bottom: 5px;")
        brand_subtitle.setAlignment(Qt.AlignCenter)
        brand_inner_layout.addWidget(brand_subtitle)
        
        brand_layout.addWidget(brand_inner)
        info_layout.addWidget(brand_container)
        
        # File Info Card
        file_card = QFrame()
        file_card.setStyleSheet(card_style)
        file_card_layout = QVBoxLayout()
        file_card_layout.setSpacing(8)
        file_card.setLayout(file_card_layout)
        
        file_header = QLabel("FILE INFORMATION")
        file_header.setStyleSheet("font-size: 12px; font-weight: bold; color: #4CAF50; letter-spacing: 1px;")
        file_card_layout.addWidget(file_header)
        
        self.file_name_label = QLabel("No file loaded")
        self.file_name_label.setWordWrap(True)
        self.file_name_label.setStyleSheet("color: #ddd; font-size: 11px; padding: 4px 0;")
        file_card_layout.addWidget(self.file_name_label)
        
        self.dimensions_label = QLabel("Dimensions: -")
        self.dimensions_label.setStyleSheet("color: #bbb; font-size: 10px;")
        file_card_layout.addWidget(self.dimensions_label)
        
        # Band selector for multi-band files
        self.band_selector_label = QLabel("Select Band:")
        self.band_selector_label.setStyleSheet("color: #14FFEC; font-weight: bold; font-size: 11px; margin-top: 5px;")
        self.band_selector_label.setVisible(False)
        file_card_layout.addWidget(self.band_selector_label)
        
        self.band_selector = QComboBox()
        self.band_selector.setStyleSheet("""
            QComboBox {
                background-color: #1e1e1e;
                color: #fff;
                border: 1px solid #14FFEC;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
            }
            QComboBox:hover {
                background-color: #252525;
                border: 1px solid #0d7377;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #14FFEC;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                color: #fff;
                selection-background-color: #0d7377;
                selection-color: #14FFEC;
                border: 1px solid #14FFEC;
                padding: 4px;
            }
        """)
        self.band_selector.currentIndexChanged.connect(self.on_band_changed)
        self.band_selector.setVisible(False)
        file_card_layout.addWidget(self.band_selector)
        
        info_layout.addWidget(file_card)
        
        # Temperature Data Card
        temp_card = QFrame()
        temp_card.setStyleSheet(card_style)
        temp_card_layout = QVBoxLayout()
        temp_card_layout.setSpacing(6)
        temp_card.setLayout(temp_card_layout)
        
        temp_header = QLabel("CLICKED LOCATION")
        temp_header.setStyleSheet("font-size: 12px; font-weight: bold; color: #FF9800; letter-spacing: 1px;")
        temp_card_layout.addWidget(temp_header)
        
        # Coordinates in compact format
        coords_frame = QFrame()
        coords_frame.setStyleSheet("background-color: #1e1e1e; border-radius: 4px; padding: 6px;")
        coords_layout = QVBoxLayout()
        coords_layout.setSpacing(3)
        coords_frame.setLayout(coords_layout)
        
        self.lat_label = QLabel("Lat: -")
        self.lat_label.setStyleSheet("color: #bbb; font-size: 10px;")
        coords_layout.addWidget(self.lat_label)
        
        self.lon_label = QLabel("Lon: -")
        self.lon_label.setStyleSheet("color: #bbb; font-size: 10px;")
        coords_layout.addWidget(self.lon_label)
        
        temp_card_layout.addWidget(coords_frame)
        
        # Temperature display - prominent
        temp_display_frame = QFrame()
        temp_display_frame.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2d2d2d, stop:1 #1e1e1e);
            border: 1px solid #4CAF50;
            border-radius: 6px;
            padding: 8px;
        """)
        temp_display_layout = QVBoxLayout()
        temp_display_layout.setSpacing(4)
        temp_display_frame.setLayout(temp_display_layout)
        
        self.temp_label = QLabel("Temperature: -")
        self.temp_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #4CAF50;")
        self.temp_label.setAlignment(Qt.AlignCenter)
        temp_display_layout.addWidget(self.temp_label)
        
        temp_card_layout.addWidget(temp_display_frame)
        info_layout.addWidget(temp_card)
        
        info_layout.addStretch()
        
        # Add info panel to splitter
        self.splitter.addWidget(self.info_panel)
        
        # Set initial sizes: 70% for image, 30% for sidebar
        self.splitter.setSizes([1000, 400])
        
        # Add splitter to main layout
        main_layout.addWidget(self.splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Upload a GeoTIFF file to begin. | IG DRONES v8.1")
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
    def apply_dark_theme(self):
        """Apply dark theme to the application."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QPushButton {
                background-color: #0d7377;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #14FFEC;
                color: #000;
            }
            QPushButton:pressed {
                background-color: #0a5254;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
            QStatusBar {
                background-color: #2b2b2b;
                color: #ddd;
                border-top: 1px solid #555;
            }
            QGraphicsView {
                border: 2px solid #555;
                border-radius: 4px;
            }
            QSplitter::handle {
                background-color: #555;
                width: 6px;
            }
            QSplitter::handle:hover {
                background-color: #14FFEC;
            }
            QSplitter::handle:pressed {
                background-color: #0d7377;
            }
        """)
        
    def dragEnterEvent(self, event):
        """Handle drag enter event for file drop."""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """Handle drop event for file drop."""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0]
            if file_path.lower().endswith(('.tif', '.tiff')):
                self.load_geotiff(file_path)
            else:
                QMessageBox.warning(self, "Invalid File", "Please drop a .tif or .tiff file.")
        
    def upload_geotiff(self):
        """Open file dialog to upload a GeoTIFF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select GeoTIFF File",
            "",
            "GeoTIFF Files (*.tif *.tiff);;All Files (*.*)"
        )
        
        if file_path:
            self.load_geotiff(file_path)
            
    def load_geotiff(self, file_path: str):
        """Load and display a GeoTIFF file with multi-band support (v6.0)."""
        try:
            self.status_bar.showMessage(f"Loading {Path(file_path).name}...")
            QApplication.processEvents()  # Update UI
            
            # Close previous dataset if any
            if self.dataset:
                self.dataset.close()
            
            # Open GeoTIFF with rasterio
            self.dataset = rasterio.open(file_path)
            self.geotiff_path = Path(file_path)
            
            # Get basic metadata
            self.transform = self.dataset.transform
            self.crs = self.dataset.crs
            self.band_count = self.dataset.count
            full_width = self.dataset.width
            full_height = self.dataset.height
            
            # Check file size and use smart loading for large files
            total_pixels = full_width * full_height * self.band_count
            self.status_bar.showMessage(f"Opened | {self.band_count} bands | {full_width}x{full_height}px")
            QApplication.processEvents()
            
            # Memory-efficient loading for large files
            max_pixels_to_load = 50_000_000  # ~50M pixels (~200MB for single band)
            if total_pixels > max_pixels_to_load:
                # Large file - use downsampling
                scale_factor = int(np.ceil(np.sqrt(total_pixels / max_pixels_to_load)))
                
                # Show warning for very large files and ask for confirmation
                file_size_mb = (total_pixels * 4) / (1024 * 1024)  # Estimate in MB (float32)
                reply = QMessageBox.question(
                    self,
                    "Large File Detected",
                    f"Large file detected: {full_width}x{full_height} pixels x {self.band_count} bands\n"
                    f"Estimated size: ~{file_size_mb:.0f} MB\n\n"
                    f"The file will be downsampled {scale_factor}x to prevent memory issues.\n"
                    f"Loaded size will be: {full_width//scale_factor}x{full_height//scale_factor} pixels\n\n"
                    f"Do you want to proceed?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                # Check if user cancelled
                if reply != QMessageBox.Yes:
                    # User cancelled - close dataset and abort
                    self.dataset.close()
                    self.dataset = None
                    self.status_bar.showMessage("File loading cancelled | IG DRONES")
                    return
                
                self.status_bar.showMessage(f"Large file | Downsampling {scale_factor}x...")
                QApplication.processEvents()
            else:
                scale_factor = 1
            
            if self.band_count == 1:
                # Single band
                self.display_mode = "SINGLE_BAND"
                if scale_factor > 1:
                    # Downsample large file
                    self.raster_data = self.dataset.read(
                        1,
                        out_shape=(full_height // scale_factor, full_width // scale_factor),
                        resampling=rasterio.enums.Resampling.average
                    )
                else:
                    self.raster_data = self.dataset.read(1)
                self.current_band = 1
                height, width = self.raster_data.shape
                
                # Hide band selector
                self.band_selector_label.setVisible(False)
                self.band_selector.setVisible(False)
                
            elif self.band_count >= 3:
                # Multi-band file - detect if RGB or thermal
                self.display_mode = self._detect_display_mode()
                
                if self.display_mode == "RGB_COMPOSITE":
                    # Read RGB bands for display
                    if scale_factor > 1:
                        # Downsample large file
                        self.raster_data = self.dataset.read(
                            out_shape=(self.band_count, full_height // scale_factor, full_width // scale_factor),
                            resampling=rasterio.enums.Resampling.average
                        )
                    else:
                        self.raster_data = self.dataset.read()
                    height, width = self.raster_data.shape[1], self.raster_data.shape[2]
                    
                    # INTELLIGENT BAND SELECTION (v8.1) - Auto-select best band even for RGB
                    print("\nWarning: RGB Composite detected - may not be thermal/temperature data")
                    print("Will attempt to find best band for temperature analysis...\n")
                    # Update band count from actual loaded data
                    self.band_count = self.raster_data.shape[0]
                    self.status_bar.showMessage(f"RGB detected | Analyzing {self.band_count} bands...")
                    QApplication.processEvents()
                    self.current_band = self.select_best_temperature_band()
                    
                    # Hide band selector - no manual switching
                    self.band_selector_label.setVisible(False)
                    self.band_selector.setVisible(False)
                    
                else:  # THERMAL_MULTIBAND
                    # Read all bands with smart memory management
                    self.status_bar.showMessage(f"Loading {self.band_count} bands...")
                    QApplication.processEvents()
                    if scale_factor > 1:
                        # Downsample large file
                        self.raster_data = self.dataset.read(
                            out_shape=(self.band_count, full_height // scale_factor, full_width // scale_factor),
                            resampling=rasterio.enums.Resampling.average
                        )
                    else:
                        self.raster_data = self.dataset.read()
                    height, width = self.raster_data.shape[1], self.raster_data.shape[2]
                    
                    # Update band count from actual loaded data
                    self.band_count = self.raster_data.shape[0]
                    
                    # INTELLIGENT BAND SELECTION (v8.1) - Auto-select BEST band
                    self.status_bar.showMessage(f"Analyzing {self.band_count} bands...")
                    QApplication.processEvents()
                    self.current_band = self.select_best_temperature_band()
                    
                    # Hide band selector - no need for user to switch bands
                    self.band_selector_label.setVisible(False)
                    self.band_selector.setVisible(False)
            else:
                # 2-band file
                self.display_mode = "SINGLE_BAND"
                if scale_factor > 1:
                    # Downsample large file
                    self.raster_data = self.dataset.read(
                        out_shape=(self.band_count, full_height // scale_factor, full_width // scale_factor),
                        resampling=rasterio.enums.Resampling.average
                    )
                else:
                    self.raster_data = self.dataset.read()
                
                # Update band count from actual loaded data
                self.band_count = self.raster_data.shape[0]
                
                # INTELLIGENT BAND SELECTION (v8.1)
                self.current_band = self.select_best_temperature_band()
                height, width = self.raster_data.shape[1], self.raster_data.shape[2]
                
                # Hide band selector
                self.band_selector_label.setVisible(False)
                self.band_selector.setVisible(False)
            
            # Initialize data quality validator (v8.0)
            self.status_bar.showMessage(f"Band {self.current_band} selected | Validating...")
            QApplication.processEvents()
            self.validator = DataQualityValidator(self.dataset, self.current_band)
            
            # Update info panel
            self.file_name_label.setText(f"File: {self.geotiff_path.name}")
            self.dimensions_label.setText(f"Dimensions: {width} x {height} pixels")
            
            # Data range removed from UI for cleaner interface
            
            # Calculate adaptive grid system (v6.1)
            self._calculate_grid_system(width, height)
            
            # Generate efficient preview
            self.status_bar.showMessage(f"Generating preview...")
            QApplication.processEvents()
            self.display_raster()
            
            # Enable reset button
            self.reset_btn.setEnabled(True)
            
            # Final status message
            if scale_factor > 1:
                self.status_bar.showMessage(
                    f"Ready | {self.geotiff_path.name} | Band {self.current_band}/{self.band_count} | {width}x{height}px (downsampled {scale_factor}x) | IG DRONES"
                )
            else:
                self.status_bar.showMessage(
                    f"Ready | {self.geotiff_path.name} | Band {self.current_band}/{self.band_count} | {width}x{height}px | IG DRONES"
                )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading GeoTIFF",
                f"Failed to load GeoTIFF file:\n\n{str(e)}"
            )
            self.status_bar.showMessage("Error loading file | IG DRONES")
    
    def _detect_display_mode(self) -> str:
        """Intelligently detect display mode for any multi-band file (v6.1 Enhanced).
        
        Works with:
        - Any Landsat version (5, 7, 8, 9, future versions)
        - Small or large area files
        - RGB composites
        - Multi-spectral imagery
        """
        # INTELLIGENT LANDSAT DETECTION: Check for thermal band presence
        # Landsat 8/9: 11 bands (Band 10/11 thermal)
        # Landsat 7: 8 bands (Band 6 thermal)
        # Landsat 5: 7 bands (Band 6 thermal)
        # Future Landsat: >= 6 bands with thermal capability
        
        if self.band_count >= 7:
            # Likely Landsat or similar multi-spectral with thermal
            # Check if data looks like reflectance (0-1) or digital numbers (0-65535)
            sample_band = self.dataset.read(1, window=((0, min(100, self.dataset.height)), 
                                                       (0, min(100, self.dataset.width))))
            sample_band = sample_band[~np.isnan(sample_band)]
            
            if len(sample_band) > 0:
                max_val = sample_band.max()
                # Landsat typically has high digital number values or reflectance
                if max_val > 10:  # Not RGB range, likely multi-spectral
                    return "THERMAL_MULTIBAND"
        
        # Check for typical RGB structure (3-4 bands)
        if 3 <= self.band_count <= 4:
            # Read first band to check data range
            sample_band = self.dataset.read(1, window=((0, min(100, self.dataset.height)), 
                                                       (0, min(100, self.dataset.width))))
            sample_band = sample_band[~np.isnan(sample_band)]
            if len(sample_band) > 0:
                max_val = sample_band.max()
                # If values are in range 0-255 or 0-1, likely RGB
                if max_val <= 1.0 or (max_val <= 255 and sample_band.min() >= 0):
                    return "RGB_COMPOSITE"
        
        # Default to thermal multiband for any other multi-band file
        return "THERMAL_MULTIBAND"
    
    def select_best_temperature_band(self) -> int:
        """Automatically select the BEST temperature band (v8.1 - Intelligent Selection).
        
        Analyzes all bands and selects the one with:
        1. Most data in NORMAL range (0-50°C)
        2. Highest valid data percentage
        3. Looks like temperature data
        
        Returns:
            Band number (1-indexed) of the best temperature band
        """
        if self.raster_data.ndim == 2:
            return 1  # Single band
        
        best_band = 1
        best_score = -1
        
        print("\nAnalyzing bands for best temperature data...")
        
        for band_idx in range(self.band_count):
            band_num = band_idx + 1
            
            try:
                # Get band data
                band_data = self.raster_data[band_idx].copy()
                
                # Apply metadata transforms
                if self.validator:
                    band_data = self.validator.apply_metadata_transforms(band_data)
                
                # Get valid data
                valid_mask = np.isfinite(band_data)
                valid_data = band_data[valid_mask]
                
                if len(valid_data) == 0:
                    print(f"Band {band_num}: No valid data - SKIP")
                    continue
                
                # Calculate percentage in NORMAL range (0-50°C)
                normal_count = 0
                for val in valid_data:
                    if val > 100:  # Kelvin
                        temp_c = val - 273.15
                    else:
                        temp_c = val
                    
                    if self.validator and self.validator.NORMAL_MIN <= temp_c <= self.validator.NORMAL_MAX:
                        normal_count += 1
                
                normal_percentage = (normal_count / len(valid_data)) * 100
                valid_percentage = (len(valid_data) / band_data.size) * 100
                
                # Calculate score (prioritize normal range data)
                score = (normal_percentage * 0.7) + (valid_percentage * 0.3)
                
                print(f"Band {band_num}: {normal_percentage:.1f}% normal, {valid_percentage:.1f}% valid, Score: {score:.1f}")
                
                # Update best band
                if score > best_score:
                    best_score = score
                    best_band = band_num
                    
            except Exception as e:
                print(f"Band {band_num}: Error analyzing - {e}")
                continue
        
        print(f"Selected Band {best_band} (Score: {best_score:.1f})\n")
        return best_band
    
    def _detect_thermal_band(self) -> int:
        """Intelligently detect thermal band for any Landsat version (v6.1 Enhanced).
        
        Works with:
        - Landsat 8/9: Band 10 (TIRS 1, primary) or Band 11 (TIRS 2)
        - Landsat 7: Band 6 (Thermal)
        - Landsat 5/4: Band 6 (Thermal)
        - Future versions: Adaptive detection
        - Small or large area files
        """
        # INTELLIGENT THERMAL DETECTION based on band count
        
        if self.band_count >= 11:
            # Landsat 8/9 full product: 11 bands
            # Band 10 = TIRS 1 (primary thermal, 100m resolution)
            # Band 11 = TIRS 2 (secondary thermal, 100m resolution)
            return 10  # Primary thermal band
            
        elif self.band_count == 10:
            # Landsat 8/9 without one TIRS band
            return 10  # Still try band 10
            
        elif self.band_count >= 8:
            # Landsat 7 ETM+ or partial Landsat 8/9
            # Band 6 for Landsat 7 (Thermal, 60m resolution)
            # Check if band 8 exists (panchromatic in L8/9)
            try:
                # Try to read a small sample from band 8 to verify it exists
                sample = self.dataset.read(8, window=((0, 1), (0, 1)))
                # If band 8 exists, might be Landsat 8/9 partial, try band 10
                if self.band_count >= 10:
                    return 10
                else:
                    return 6  # Likely Landsat 7, band 6 is thermal
            except:
                return 6  # Default to band 6 for Landsat 7
                
        elif self.band_count == 7:
            # Landsat 5 TM or Landsat 7 without pan
            # Band 6 = Thermal (120m for L5, 60m for L7)
            return 6
            
        elif self.band_count >= 6:
            # At least 6 bands, band 6 likely thermal
            return 6
            
        elif self.band_count >= 2:
            # Multi-band but not standard Landsat
            # Try last band (often thermal in custom composites)
            return self.band_count
            
        else:
            # Single band - use it
            return 1
    
    def _populate_band_selector(self):
        """Intelligently populate band selector for any Landsat version (v6.1 Enhanced).
        
        Works with:
        - Landsat 8/9: 11 bands with OLI + TIRS names
        - Landsat 7: 8 bands with ETM+ names
        - Landsat 5/4: 7 bands with TM names
        - Any multi-band file: Generic or custom names
        """
        self.band_selector.blockSignals(True)  # Prevent triggering change event
        self.band_selector.clear()
        
        # INTELLIGENT BAND NAMING based on band count
        
        if self.band_count >= 11:
            # Landsat 8/9 OLI + TIRS (11 bands)
            landsat_89_names = {
                1: "Band 1 - Coastal/Aerosol",
                2: "Band 2 - Blue",
                3: "Band 3 - Green",
                4: "Band 4 - Red",
                5: "Band 5 - NIR",
                6: "Band 6 - SWIR 1",
                7: "Band 7 - SWIR 2",
                8: "Band 8 - Panchromatic",
                9: "Band 9 - Cirrus",
                10: "Band 10 - Thermal (TIRS 1)",
                11: "Band 11 - Thermal (TIRS 2)",
            }
            for i in range(1, self.band_count + 1):
                self.band_selector.addItem(landsat_89_names.get(i, f"Band {i}"), i)
                
        elif self.band_count >= 8:
            # Landsat 7 ETM+ (8 bands)
            landsat_7_names = {
                1: "Band 1 - Blue",
                2: "Band 2 - Green",
                3: "Band 3 - Red",
                4: "Band 4 - NIR",
                5: "Band 5 - SWIR 1",
                6: "Band 6 - Thermal",
                7: "Band 7 - SWIR 2",
                8: "Band 8 - Panchromatic",
            }
            for i in range(1, self.band_count + 1):
                self.band_selector.addItem(landsat_7_names.get(i, f"Band {i}"), i)
                
        elif self.band_count >= 7:
            # Landsat 5/4 TM (7 bands)
            landsat_5_names = {
                1: "Band 1 - Blue",
                2: "Band 2 - Green",
                3: "Band 3 - Red",
                4: "Band 4 - NIR",
                5: "Band 5 - SWIR 1",
                6: "Band 6 - Thermal",
                7: "Band 7 - SWIR 2",
            }
            for i in range(1, self.band_count + 1):
                self.band_selector.addItem(landsat_5_names.get(i, f"Band {i}"), i)
                
        else:
            # Generic multi-band or custom composite
            for i in range(1, self.band_count + 1):
                # Mark thermal band with star if detected
                if i == self.current_band and "THERMAL" in self.display_mode:
                    self.band_selector.addItem(f"Band {i}", i)
                else:
                    self.band_selector.addItem(f"Band {i}", i)
        
        # Set current band
        index = self.band_selector.findData(self.current_band)
        if index >= 0:
            self.band_selector.setCurrentIndex(index)
        
        self.band_selector.blockSignals(False)
    
    def _update_data_range(self):
        """Data range UI removed - method kept for compatibility."""
        pass
    
    def _update_quality_ui(self):
        """Update data quality UI labels (v8.0) - DEPRECATED - Quality widgets removed."""
        # Quality widgets removed from sidebar for cleaner UI
        pass
    
    def on_band_changed(self, index):
        """Handle band selection change with intelligent re-sampling (v8.0 Enhanced)."""
        if index < 0:
            return
        
        self.current_band = self.band_selector.itemData(index)
        self.status_bar.showMessage(f"Switched to Band {self.current_band} | Updating measurements... | IG DRONES")
        
        # Reinitialize validator for new band (v8.0)
        if self.dataset:
            self.validator = DataQualityValidator(self.dataset, self.current_band)
        
        # Clear grid averages cache for new band
        self.grid_averages = {}
        
        # Data range removed from UI
        
        # INTELLIGENT RE-SAMPLING: If user previously clicked a location,
        # automatically re-sample that same location with the new band
        if (self.last_click_preview_x is not None and 
            self.last_click_preview_y is not None):
            
            # Re-sample the last clicked location with new band data
            self.on_image_click(self.last_click_preview_x, self.last_click_preview_y)
            
            self.status_bar.showMessage(
                f"Band {self.current_band} selected | Location re-sampled | IG DRONES"
            )
        else:
            self.status_bar.showMessage(f"Switched to Band {self.current_band} | IG DRONES")
    
    def _calculate_grid_system(self, width: int, height: int):
        """Calculate adaptive grid system based on image resolution (v6.1).
        
        Enhanced with finer granularity for neighborhood averaging.
        """
        # Adaptive grid sizing with FINER GRANULARITY for better accuracy:
        # - Small images (< 1000px): 20px cells (finer)
        # - Medium images (1000-5000px): 40px cells (finer)
        # - Large images (5000-10000px): 80px cells (finer)
        # - Very large images (> 10000px): 150px cells (finer)
        
        max_dim = max(width, height)
        
        if max_dim < 1000:
            self.grid_size = 20  # Finer for small images
        elif max_dim < 5000:
            self.grid_size = 40  # Finer for medium
        elif max_dim < 10000:
            self.grid_size = 80  # Finer for large
        else:
            self.grid_size = 150  # Finer for huge
        
        # Calculate grid dimensions - MORE GRIDS for better averaging
        self.grid_cols = int(np.ceil(width / self.grid_size))
        self.grid_rows = int(np.ceil(height / self.grid_size))
        
        # Clear grid averages cache when recalculating
        self.grid_averages = {}
            
    def _get_grid_average(self, grid_row: int, grid_col: int, width: int, height: int) -> float:
        """Calculate average temperature for a specific grid cell (v6.1).
        
        Args:
            grid_row: Grid row index
            grid_col: Grid column index
            width: Image width
            height: Image height
            
        Returns:
            Average temperature for the grid cell, or NaN if no valid data
        """
        # Check cache first
        cache_key = f"{self.current_band}_{grid_row}_{grid_col}"
        if cache_key in self.grid_averages:
            return self.grid_averages[cache_key]
        
        # Calculate grid cell boundaries
        cell_x_start = grid_col * self.grid_size
        cell_x_end = min(cell_x_start + self.grid_size, width)
        cell_y_start = grid_row * self.grid_size
        cell_y_end = min(cell_y_start + self.grid_size, height)
        
        # Extract all pixels in the grid cell
        if self.raster_data.ndim == 2:
            cell_data = self.raster_data[cell_y_start:cell_y_end, cell_x_start:cell_x_end]
        else:
            cell_data = self.raster_data[self.current_band - 1, cell_y_start:cell_y_end, cell_x_start:cell_x_end]
        
        # Filter out NaN values and calculate average
        valid_data = cell_data[~np.isnan(cell_data)]
        
        # CONSERVATIVE APPROACH: Only use NORMAL range pixels (0-50°C) for grid averaging
        if len(valid_data) > 0 and self.validator:
            # Convert to Celsius for filtering
            normal_data = []
            for val in valid_data:
                if val > 100:  # Kelvin
                    temp_celsius = val - 273.15
                else:  # Celsius
                    temp_celsius = val
                
                # Only accept NORMAL range (0-50°C)
                if self.validator.NORMAL_MIN <= temp_celsius <= self.validator.NORMAL_MAX:
                    normal_data.append(val)
            
            # Only average NORMAL range values
            if len(normal_data) > 0:
                avg = np.mean(normal_data)
                # Cache the result
                self.grid_averages[cache_key] = avg
                return avg
        
        return np.nan
    
    def _get_neighborhood_average(self, grid_row: int, grid_col: int, width: int, height: int) -> tuple:
        """Calculate neighborhood average using 9-grid (3x3) system (v8.1 Enhanced).
        
        Takes the clicked grid plus all 8 surrounding grids, calculates average for each,
        then averages those 9 averages.
        
        CONSERVATIVE APPROACH (v8.1):
        - Only uses pixels with NORMAL range temperatures (0-50°C)
        - Filters out unusual/extreme values before averaging
        - Returns balanced, typical temperatures only
        
        Grid pattern:
        ┌───┬───┬───┐
        │ 1 │ 2 │ 3 │  Each number is a grid cell
        ├───┼───┼───┤
        │ 4 │ 5 │ 6 │  5 = clicked position
        ├───┼───┼───┤
        │ 7 │ 8 │ 9 │  Average all 9 grids!
        └───┴───┴───┘
        
        Args:
            grid_row: Clicked grid row
            grid_col: Clicked grid column
            width: Image width
            height: Image height
            
        Returns:
            (neighborhood_avg, total_pixels, min_val, max_val, std_val, num_grids_used)
        """
        # Define 3x3 neighborhood offsets (including center)
        neighborhood_offsets = [
            (-1, -1), (-1, 0), (-1, 1),  # Top row
            (0, -1),  (0, 0),  (0, 1),   # Middle row (includes center)
            (1, -1),  (1, 0),  (1, 1)    # Bottom row
        ]
        
        grid_averages_list = []
        all_valid_data = []
        grids_used = 0
        
        for row_offset, col_offset in neighborhood_offsets:
            neighbor_row = grid_row + row_offset
            neighbor_col = grid_col + col_offset
            
            # Check if neighbor is within bounds
            if 0 <= neighbor_row < self.grid_rows and 0 <= neighbor_col < self.grid_cols:
                grid_avg = self._get_grid_average(neighbor_row, neighbor_col, width, height)
                
                if not np.isnan(grid_avg):
                    grid_averages_list.append(grid_avg)
                    grids_used += 1
                    
                    # Also collect raw data for statistics
                    cell_x_start = neighbor_col * self.grid_size
                    cell_x_end = min(cell_x_start + self.grid_size, width)
                    cell_y_start = neighbor_row * self.grid_size
                    cell_y_end = min(cell_y_start + self.grid_size, height)
                    
                    if self.raster_data.ndim == 2:
                        cell_data = self.raster_data[cell_y_start:cell_y_end, cell_x_start:cell_x_end]
                    else:
                        cell_data = self.raster_data[self.current_band - 1, cell_y_start:cell_y_end, cell_x_start:cell_x_end]
                    
                    valid_pixels = cell_data[~np.isnan(cell_data)]
                    if len(valid_pixels) > 0:
                        all_valid_data.extend(valid_pixels.tolist())
        
        # Calculate neighborhood average from grid averages
        if len(grid_averages_list) > 0:
            # Average of averages - ULTRA ACCURATE!
            neighborhood_avg = np.mean(grid_averages_list)
            
            # Statistics from all pixels in neighborhood
            all_valid_array = np.array(all_valid_data)
            total_pixels = len(all_valid_array)
            min_val = np.min(all_valid_array)
            max_val = np.max(all_valid_array)
            std_val = np.std(all_valid_array)
            
            return neighborhood_avg, total_pixels, min_val, max_val, std_val, grids_used
        else:
            return np.nan, 0, np.nan, np.nan, np.nan, 0
    
    def display_raster(self):
        """Display the raster data with multi-band support (v6.0)."""
        try:
            # Handle different display modes
            if self.display_mode == "RGB_COMPOSITE" and self.raster_data.ndim == 3:
                self._display_rgb_composite()
            else:
                self._display_single_band()
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Display Error",
                f"Failed to display raster:\n\n{str(e)}"
            )
    
    def _display_rgb_composite(self):
        """Display multi-band file as RGB composite (v6.0)."""
        # Get dimensions
        height, width = self.raster_data.shape[1], self.raster_data.shape[2]
        
        self.status_bar.showMessage(f"Preparing RGB preview...")
        QApplication.processEvents()
        
        # Select RGB bands (try different combinations)
        if self.band_count >= 10:
            # Landsat: Use bands 4,3,2 for natural color (Red, Green, Blue)
            rgb_bands = [3, 2, 1]  # 0-indexed: bands 4,3,2
        elif self.band_count >= 3:
            # Standard RGB or try first 3 bands
            rgb_bands = [0, 1, 2]
        else:
            raise ValueError("Not enough bands for RGB composite")
        
        # Stack RGB bands
        rgb_array = np.dstack([
            self.raster_data[rgb_bands[0]],
            self.raster_data[rgb_bands[1]],
            self.raster_data[rgb_bands[2]]
        ])
        
        # Normalize each band independently for better visualization
        self.status_bar.showMessage(f"Normalizing RGB...")
        QApplication.processEvents()
        
        rgb_normalized = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(3):
            band_data = rgb_array[:, :, i]
            valid_data = band_data[~np.isnan(band_data)]
            
            if len(valid_data) > 0:
                # Apply percentile clipping
                p_low = np.percentile(valid_data, 2)
                p_high = np.percentile(valid_data, 98)
                
                # Normalize to 0-255
                band_clipped = np.clip(band_data, p_low, p_high)
                with np.errstate(invalid='ignore'):
                    rgb_normalized[:, :, i] = ((band_clipped - p_low) / (p_high - p_low) * 255).astype(np.uint8)
        
        # Handle preview scaling
        max_preview_size = 2048
        if width > max_preview_size or height > max_preview_size:
            scale = min(max_preview_size / width, max_preview_size / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            self.status_bar.showMessage(f"Resizing {width}x{height} → {new_width}x{new_height}...")
            QApplication.processEvents()
            
            # Resize RGB image
            img = Image.fromarray(rgb_normalized, mode='RGB')
            img = img.resize((new_width, new_height), Image.LANCZOS)
            preview_rgb = np.array(img)
            
            self.preview_scale_x = width / new_width
            self.preview_scale_y = height / new_height
        else:
            preview_rgb = rgb_normalized
            self.preview_scale_x = 1.0
            self.preview_scale_y = 1.0
        
        # Convert to RGBA for transparency support
        preview_height, preview_width = preview_rgb.shape[:2]
        rgba = np.dstack([preview_rgb, np.full((preview_height, preview_width), 255, dtype=np.uint8)])
        
        # Convert to QImage
        self.status_bar.showMessage(f"Rendering preview...")
        QApplication.processEvents()
        
        bytes_per_line = 4 * preview_width
        qimage = QImage(rgba.data, preview_width, preview_height, bytes_per_line, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        
        # Display in graphics view
        self.graphics_view.set_image(pixmap)
    
    def _display_single_band(self):
        """Display single band or selected band from multi-band file (v6.0)."""
        # Get data for current band
        if self.raster_data.ndim == 2:
            data = self.raster_data.copy()
        else:
            # Multi-band - extract current band
            self.status_bar.showMessage(f"Extracting band {self.current_band}...")
            QApplication.processEvents()
            data = self.raster_data[self.current_band - 1].copy()
        
        height, width = data.shape
        
        # Handle NaN values
        mask = np.isnan(data)
        valid_data = data[~mask]
        
        if len(valid_data) == 0:
            raise ValueError("No valid data in selected band")
        
        # Apply percentile clipping for better contrast
        self.status_bar.showMessage(f"Applying contrast...")
        QApplication.processEvents()
        
        p_low = np.percentile(valid_data, 2)
        p_high = np.percentile(valid_data, 98)
        
        # Clip and normalize to 0-255
        data_clipped = np.clip(data, p_low, p_high)
        with np.errstate(invalid='ignore'):
            data_normalized = ((data_clipped - p_low) / (p_high - p_low) * 255).astype(np.uint8)
        
        # Set NaN values to 0 (will be made transparent)
        data_normalized[mask] = 0
        
        # Generate preview at appropriate resolution
        max_preview_size = 2048
        if width > max_preview_size or height > max_preview_size:
            # Calculate scale to fit within max_preview_size
            scale = min(max_preview_size / width, max_preview_size / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            self.status_bar.showMessage(f"Downsampling {width}x{height} → {new_width}x{new_height}...")
            QApplication.processEvents()
            
            # Create preview using PIL for high-quality downsampling
            img = Image.fromarray(data_normalized, mode='L')
            img = img.resize((new_width, new_height), Image.LANCZOS)
            preview_array = np.array(img)
            
            # Store scale factors for coordinate mapping
            self.preview_scale_x = width / new_width
            self.preview_scale_y = height / new_height
        else:
            # Use full resolution if small enough
            preview_array = data_normalized
            self.preview_scale_x = 1.0
            self.preview_scale_y = 1.0
        
        # Store preview data
        self.preview_data = preview_array
        preview_height, preview_width = preview_array.shape
        
        # Apply colormap for better visualization
        self.status_bar.showMessage(f"Applying colormap...")
        QApplication.processEvents()
        
        from matplotlib import colormaps
        colormap = colormaps.get_cmap('RdYlBu_r')  # Red-Yellow-Blue reversed
        
        # Normalize to 0-1 for colormap
        preview_normalized = preview_array.astype(float) / 255.0
        rgba = colormap(preview_normalized)
        rgba = (rgba * 255).astype(np.uint8)
        
        # Make NaN/NoData transparent
        preview_mask = (preview_array == 0) & mask[:preview_height, :preview_width]
        rgba[preview_mask, 3] = 0
        
        # Convert to QImage
        height_q, width_q = rgba.shape[:2]
        bytes_per_line = 4 * width_q
        qimage = QImage(rgba.data, width_q, height_q, bytes_per_line, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        
        # Display in graphics view
        self.graphics_view.set_image(pixmap)
            
    def on_image_click(self, preview_x: int, preview_y: int):
        """Handle click with intelligent grid-based temperature sampling (v6.1 Enhanced)."""
        if self.dataset is None or self.raster_data is None:
            return
        
        try:
            # Store last clicked location for intelligent band switching
            self.last_click_preview_x = preview_x
            self.last_click_preview_y = preview_y
            
            # Convert preview coordinates to full resolution raster coordinates
            raster_x = int(preview_x * self.preview_scale_x)
            raster_y = int(preview_y * self.preview_scale_y)
            
            # Store raster coordinates as well
            self.last_click_raster_x = raster_x
            self.last_click_raster_y = raster_y
            
            # Get dimensions based on data shape
            if self.raster_data.ndim == 2:
                height, width = self.raster_data.shape
            else:
                height, width = self.raster_data.shape[1], self.raster_data.shape[2]
            
            # Ensure within bounds
            if 0 <= raster_x < width and 0 <= raster_y < height:
                # Add visual pin marker at the clicked position (preview coordinates)
                self.graphics_view.add_pin_marker(preview_x, preview_y)
                
                # Get geographic coordinates using the transform (center of click)
                lon, lat = self.dataset.xy(raster_y, raster_x)
                
                # Neighborhood averaging (v6.1)
                # Uses 9-grid (3x3) system
                if self.grid_enabled and self.grid_size > 0:
                    # Determine which grid cell was clicked
                    grid_col = raster_x // self.grid_size
                    grid_row = raster_y // self.grid_size
                    
                    if self.neighborhood_averaging:
                        # Average of 9 grids (clicked + 8 neighbors)
                        value, total_pixels, cell_min, cell_max, cell_std, grids_used = \
                            self._get_neighborhood_average(grid_row, grid_col, width, height)
                        
                        if np.isnan(value):
                            # No valid data
                            value = np.nan
                    else:
                        # Single grid averaging (old method)
                        cell_x_start = grid_col * self.grid_size
                        cell_x_end = min(cell_x_start + self.grid_size, width)
                        cell_y_start = grid_row * self.grid_size
                        cell_y_end = min(cell_y_start + self.grid_size, height)
                        
                        if self.raster_data.ndim == 2:
                            cell_data = self.raster_data[cell_y_start:cell_y_end, cell_x_start:cell_x_end]
                        else:
                            cell_data = self.raster_data[self.current_band - 1, cell_y_start:cell_y_end, cell_x_start:cell_x_end]
                        
                        valid_cell_data = cell_data[~np.isnan(cell_data)]
                        
                        if len(valid_cell_data) > 0:
                            value = np.mean(valid_cell_data)
                        else:
                            value = np.nan
                else:
                    # Single pixel sampling (grid disabled)
                    if self.raster_data.ndim == 2:
                        value = self.raster_data[raster_y, raster_x]
                    else:
                        value = self.raster_data[self.current_band - 1, raster_y, raster_x]
                
                # Validate clicked temperature value (v8.0 Enhanced - Multi-level)
                validation_icon = ""
                validation_level = "normal"
                
                if self.validator:
                    is_usable, validation_msg, validation_level = self.validator.validate_single_value(value)
                    original_validation_level = validation_level  # Save for message
                    
                    # CONSERVATIVE APPROACH: Only show NORMAL temps directly
                    # If UNUSUAL or IMPOSSIBLE, interpolate from NORMAL neighbors
                    if not is_usable or validation_level == "unusual":
                        # UNUSUAL/IMPOSSIBLE value - TRY INTELLIGENT INTERPOLATION! (v8.1 Enhanced)
                        
                        # Get current band data
                        if self.raster_data.ndim == 2:
                            band_data = self.raster_data
                        else:
                            band_data = self.raster_data[self.current_band - 1]
                        
                        # Apply metadata transforms
                        band_data = self.validator.apply_metadata_transforms(band_data)
                        
                        # Try to interpolate from nearby valid pixels (with strict validation)
                        success, interpolated_value, num_neighbors, search_radius = \
                            self.validator.interpolate_from_neighbors(band_data, raster_y, raster_x, max_radius=15)
                        
                        if success:
                            # INTERPOLATION SUCCESSFUL! Use estimated value
                            value = interpolated_value  # Override with interpolated value
                            validation_level = "estimated"
                            
                            # Show as estimated temperature
                            if value > 100:  # Kelvin
                                temp_celsius = value - 273.15
                                temp_kelvin = value
                            else:  # Celsius
                                temp_celsius = value
                                temp_kelvin = value + 273.15
                            
                            temp_display = f"{temp_celsius:.1f} °C (Estimated)"
                            value_display = f"Estimated from surrounding area"
                            
                            # Show success in status bar
                            if original_validation_level == "unusual":
                                self.status_bar.showMessage(
                                    f"Adjusted value: {temp_celsius:.1f}°C | IG DRONES"
                                )
                            else:
                                self.status_bar.showMessage(
                                    f"Estimated: {temp_celsius:.1f}°C | IG DRONES"
                                )
                            
                            # Continue processing with interpolated value...
                            # Don't return here, let it display the estimated temperature
                            
                        else:
                            # INTERPOLATION FAILED - Cannot validate
                            # Show error message
                            if value > 100:  # Kelvin
                                temp_celsius = value - 273.15
                                temp_kelvin = value
                                if original_validation_level == "unusual":
                                    temp_display = f"{temp_celsius:.1f} °C (Extreme - Unvalidated)"
                                    value_display = f"{temp_kelvin:.1f} K = {temp_celsius:.1f} °C (Cannot validate)"
                                else:
                                    temp_display = f"{temp_celsius:.1f} °C (No Data)"
                                    value_display = f"{temp_kelvin:.1f} K = {temp_celsius:.1f} °C (No data available)"
                            else:  # Celsius
                                temp_celsius = value
                                temp_kelvin = value + 273.15
                                if original_validation_level == "unusual":
                                    temp_display = f"{temp_celsius:.1f} °C (Extreme - Unvalidated)"
                                    value_display = f"{temp_celsius:.1f} °C = {temp_kelvin:.1f} K (Cannot validate)"
                                else:
                                    temp_display = f"{temp_celsius:.1f} °C (No Data)"
                                    value_display = f"{temp_celsius:.1f} °C = {temp_kelvin:.1f} K (No data available)"
                            
                            # Show error in status bar
                            if original_validation_level == "unusual":
                                self.status_bar.showMessage(f"Extreme value: {temp_celsius:.1f}°C | Unable to validate | IG DRONES")
                            else:
                                self.status_bar.showMessage(f"No data available at this location | IG DRONES")
                            
                            # Update labels with error indication
                            self.temp_label.setText(f"Temperature: {temp_display}")
                            self.lat_label.setText(f"Lat: {lat:.6f}°")
                            self.lon_label.setText(f"Lon: {lon:.6f}°")
                            return  # Don't process impossible data further
                    
                    # Set icon based on level
                    if validation_level == "normal":
                        validation_icon = ""  # Normal
                    elif validation_level == "unusual":
                        validation_icon = ""  # Unusual but valid
                    elif validation_level == "estimated":
                        validation_icon = ""  # Interpolated/estimated
                
                # Prepare display strings - ALWAYS show BOTH Celsius AND Kelvin
                if np.isnan(value):
                    temp_display = "No Data Available"
                    value_display = "NaN"
                    temp_short = "No Data"
                elif validation_level == "estimated":
                    # Already set in interpolation logic above
                    # temp_display and value_display are already defined
                    # Just need to update coordinates
                    pass
                else:
                    # Automatic temperature unit detection and conversion
                    if value > 100:  # Source data is in Kelvin
                        temp_celsius = value - 273.15
                        temp_kelvin = value
                        
                        # Add validation note (use .1f for cleaner display)
                        if validation_level == "unusual":
                            temp_display = f"{temp_celsius:.1f} °C (Extreme)"
                            self.status_bar.showMessage(f"Extreme temperature: {temp_celsius:.1f}°C | IG DRONES")
                        else:
                            temp_display = f"{temp_celsius:.1f} °C"
                            self.status_bar.showMessage(f"Temperature: {temp_celsius:.1f}°C | IG DRONES")
                        
                        value_display = f"{temp_kelvin:.1f} K ({temp_celsius:.1f} °C)"
                        temp_short = f"{temp_celsius:.1f}°C"
                        
                    else:  # Source data is in Celsius
                        temp_celsius = value
                        temp_kelvin = value + 273.15
                        
                        # Add validation note (use .1f for cleaner display)
                        if validation_level == "unusual":
                            temp_display = f"{temp_celsius:.1f} °C (Extreme)"
                            self.status_bar.showMessage(f"Extreme temperature: {temp_celsius:.1f}°C | IG DRONES")
                        else:
                            temp_display = f"{temp_celsius:.1f} °C"
                            self.status_bar.showMessage(f"Temperature: {temp_celsius:.1f}°C | IG DRONES")
                        
                        value_display = f"{temp_celsius:.1f} °C ({temp_kelvin:.1f} K)"
                        temp_short = f"{temp_celsius:.1f}°C"
                
                # Update info panel
                self.lat_label.setText(f"Lat: {lat:.6f}°")
                self.lon_label.setText(f"Lon: {lon:.6f}°")
                self.temp_label.setText(f"Temperature: {temp_display}")
                
                # Update status bar
                self.status_bar.showMessage(
                    f"Lat {lat:.6f}, Lon {lon:.6f} | {temp_short} | IG DRONES"
                )
                
                # Show floating info label near the click point
                if self.grid_enabled and self.neighborhood_averaging:
                    sampling_mode = "9-Grid Avg"
                elif self.grid_enabled:
                    sampling_mode = "Grid Avg"
                else:
                    sampling_mode = "Pixel"
                self.show_floating_label(preview_x, preview_y, value, lat, lon, sampling_mode)
                
        except Exception as e:
            self.status_bar.showMessage(f"Error sampling point: {str(e)} | IG DRONES")
    
    def show_floating_label(self, x: int, y: int, temp_value: float, lat: float, lon: float, mode: str = "Single Pixel"):
        """Display a floating info label near the clicked point (v6.1 - Updated UI)."""
        # Remove existing floating label if any
        if self.floating_label:
            self.floating_label.deleteLater()
        
        # Format temperature display - ALWAYS show BOTH Celsius AND Kelvin
        if np.isnan(temp_value):
            temp_text = "Temperature: No Data"
        else:
            if temp_value > 100:  # Source data is in Kelvin
                temp_celsius = temp_value - 273.15
                temp_kelvin = temp_value
                temp_text = f"Temperature: {temp_celsius:.2f} C (Kelvin: {temp_kelvin:.2f} K)"
            else:  # Source data is in Celsius - convert to Kelvin for display
                temp_celsius = temp_value
                temp_kelvin = temp_value + 273.15
                temp_text = f"Temperature: {temp_celsius:.2f} C (Kelvin: {temp_kelvin:.2f} K)"
        
        # Create floating label with clean format (no emoji)
        self.floating_label = QLabel(self)
        info_text = f"{temp_text}\nLat: {lat:.6f}, Lon: {lon:.6f}"
        self.floating_label.setText(info_text)
        self.floating_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 125, 125, 220);
                color: white;
                border: 2px solid #14FFEC;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        self.floating_label.setAlignment(Qt.AlignCenter)
        self.floating_label.adjustSize()
        
        # Position the label near the graphics view
        view_pos = self.graphics_view.mapFromScene(QPointF(x, y))
        global_pos = self.graphics_view.mapToGlobal(view_pos)
        local_pos = self.mapFromGlobal(global_pos)
        
        # Offset to avoid covering the marker
        offset_x = 20
        offset_y = -40
        
        # Ensure label stays within window bounds
        label_x = min(local_pos.x() + offset_x, self.width() - self.floating_label.width() - 10)
        label_y = max(local_pos.y() + offset_y, 10)
        
        self.floating_label.move(label_x, label_y)
        self.floating_label.show()
        self.floating_label.raise_()
        
        # Auto-hide after 4 seconds
        if self.floating_timer:
            self.floating_timer.stop()
        
        self.floating_timer = QTimer()
        self.floating_timer.setSingleShot(True)
        self.floating_timer.timeout.connect(self.hide_floating_label)
        self.floating_timer.start(4000)  # 4 seconds
    
    def hide_floating_label(self):
        """Hide and remove the floating info label."""
        if self.floating_label:
            self.floating_label.deleteLater()
            self.floating_label = None
    
    def reset_view(self):
        """Reset the zoom and pan to original state."""
        if self.graphics_view:
            self.graphics_view.reset_view()
            
            # Clear temperature info
            self.lat_label.setText("Lat: -")
            self.lon_label.setText("Lon: -")
            self.temp_label.setText("Temp: -")
            
            # Clear last clicked location (v6.1 enhancement)
            self.last_click_preview_x = None
            self.last_click_preview_y = None
            self.last_click_raster_x = None
            self.last_click_raster_y = None
            
            # Hide floating label if visible
            self.hide_floating_label()
            
            self.status_bar.showMessage(
                "View reset | Grid-Based Sampling Active | IG DRONES"
            )
            
    def closeEvent(self, event):
        """Handle application close event."""
        if self.dataset:
            self.dataset.close()
        event.accept()


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Running in development mode
        base_path = Path(__file__).parent
    
    return Path(base_path) / relative_path


def main():
    """Main entry point for the IG DRONES GeoTIFF Temperature Viewer application."""
    app = QApplication(sys.argv)
    app.setApplicationName("IG DRONES - GeoTIFF Temperature Viewer v6.1")
    
    # Set application icon globally (for taskbar, title bar, etc.)
    # Works for both development and .exe
    icon_path = get_resource_path("logo/igdrones.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        # Fallback to PNG if ICO not found
        icon_path_png = get_resource_path("logo/igdrones.png")
        if icon_path_png.exists():
            app.setWindowIcon(QIcon(str(icon_path_png)))
    
    viewer = GeoTIFFViewer()
    viewer.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
