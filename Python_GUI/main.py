#!/usr/bin/env python3
"""
GUI v8 - Dual Camera with Temperature Range Filter

Dual-camera GUI for simultaneous RGB and thermal camera display:
- RGB camera (USB) - External webcam with optimized threading
- HT301 thermal camera (USB) - With configurable temperature range filtering
- Side-by-side display layout for real-time comparison

Temperature filtering controlled from configuration section below.
"""

# Temperature Filter Configuration
ENABLE_TEMP_FILTER = True
FILTER_TEMP_MIN = 10.0
FILTER_TEMP_MAX = 50.0

import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from gui_window import SensorFusionGUI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Check if all required dependencies are available."""
    missing_deps = []
    
    try:
        import cv2
        logger.info(f"OpenCV version: {cv2.__version__}")
    except ImportError:
        missing_deps.append("opencv-python")
    
    try:
        import numpy as np
        logger.info(f"NumPy version: {np.__version__}")
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        import PyQt5
        logger.info("PyQt5 available")
    except ImportError:
        missing_deps.append("PyQt5")
    
    return missing_deps


def main():
    """Main application entry point."""
    print("=" * 50)
    print("GUI v8 - Dual Camera with Temperature Range Filter")
    if ENABLE_TEMP_FILTER:
        print(f"Temperature Filter: {FILTER_TEMP_MIN}°C to {FILTER_TEMP_MAX}°C")
    print("=" * 50)
    
    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        logger.error(f"Missing dependencies: {missing_deps}")
        return 1
    
    # Create and run application
    app = QApplication(sys.argv)
    window = SensorFusionGUI(ENABLE_TEMP_FILTER, FILTER_TEMP_MIN, FILTER_TEMP_MAX)
    window.show()
    
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main()) 