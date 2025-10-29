"""
Build script for IG DRONES GeoTIFF Temperature Viewer v8.1
Creates standalone Windows executable with all dependencies
"""

import PyInstaller.__main__

PyInstaller.__main__.run([
    'app.py',
    '--onefile',
    '--windowed',
    '--name=IG_DRONES_GeoTIFF_Viewer_v8.1',
    
    # Custom icon for .exe file
    '--icon=logo/igdrones.ico',
    
    # Include logo files in the bundle (CRITICAL - for runtime icon display)
    '--add-data=logo/igdrones.ico;logo',
    '--add-data=logo/igdrones.png;logo',
    
    # Rasterio hidden imports (CRITICAL - fixes ModuleNotFoundError)
    '--hidden-import=rasterio._shim',
    '--hidden-import=rasterio.sample',
    '--hidden-import=rasterio._features',
    '--hidden-import=rasterio._env',
    '--hidden-import=rasterio.vrt',
    '--hidden-import=rasterio.control',
    '--hidden-import=rasterio._version',
    
    # PyQt5 hidden imports
    '--hidden-import=PyQt5.QtPrintSupport',
    
    # Matplotlib backend
    '--hidden-import=matplotlib.backends.backend_qt5agg',
    
    # NumPy hidden imports
    '--hidden-import=numpy.core._dtype_ctypes',
    
    # Collect all rasterio data files
    '--collect-data=rasterio',
    '--collect-binaries=rasterio',
    
    # Clean build
    '--clean',
])

print("\n" + "="*60)
print("BUILD COMPLETE!")
print("="*60)
print(f"\nYour .exe is ready at:")
print(f"dist/IG_DRONES_GeoTIFF_Viewer_v8.1.exe")
print("\nTest it before distributing!")
print("="*60)
