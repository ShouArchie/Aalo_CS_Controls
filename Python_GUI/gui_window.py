"""
GUI Window Module for GUI v8 - Dual Camera Display

PyQt5-based dual-camera GUI with temperature range filtering:
1. RGB Camera (left panel) - External USB webcam with optimized threading
2. Thermal Camera (right panel) - HT301 with configurable temperature filtering

Features:
- Side-by-side camera layout for real-time comparison
- Temperature range filtering with min/max detection
- Enhanced thermal visualization with overlay markers
- Configurable temperature filtering from main.py
"""

import logging
import numpy as np
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QGroupBox, QGridLayout, QInputDialog)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QColor, QKeySequence

# Import sensor capture modules
from capture_rgb import RGBCameraCapture
from capture_thermal import ThermalCameraCapture

# Configure logging
logger = logging.getLogger(__name__)


class SensorFusionGUI(QMainWindow):
    """Main GUI window for dual-camera display - RGB and thermal cameras side-by-side."""
    
    def __init__(self, temp_filter_enabled=True, temp_filter_min=0.0, temp_filter_max=50.0):
        super().__init__()
        self.setWindowTitle("GUI v8 - Dual Camera with Temperature Range Filter")
        self.setGeometry(100, 100, 1600, 900)  # Larger window for bigger text
        
        # Store settings
        self.temp_filter_enabled = temp_filter_enabled
        self.temp_filter_min = temp_filter_min
        self.temp_filter_max = temp_filter_max
        self.rgb_camera = None
        self.thermal_camera = None
        
        # Setup UI and cameras
        self.setup_ui_style()
        self.init_ui()
        self.start_sensors()
        self.setup_keyboard_shortcuts()
        
        # Start update loop
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(33)  # 30 Hz
        
        logger.info("GUI initialized - Ctrl+T: Temp range, Ctrl+F: Toggle filter, Ctrl+P: Color palette")
    
    def init_ui(self):
        """Initialize dual-camera layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setSpacing(10)
        
        # Create both camera panels
        layout.addWidget(self.create_camera_panel("RGB"))
        layout.addWidget(self.create_camera_panel("Thermal"))
    
    def create_camera_panel(self, camera_type: str) -> QGroupBox:
        """Create a camera panel (RGB or Thermal)."""
        config = {
            'RGB': {'title': 'RGB Camera', 'placeholder': 'No RGB feed', 'enhanced': False},
            'Thermal': {'title': 'Thermal Camera', 'placeholder': 'No thermal feed', 'enhanced': True}
        }
        
        cfg = config[camera_type]
        panel = QGroupBox(cfg['title'])
        panel.setFont(self.fonts['header'])
        layout = QVBoxLayout(panel)
        
        # Camera display
        camera_label = QLabel(cfg['placeholder'])
        camera_label.setAlignment(Qt.AlignCenter)
        camera_label.setMinimumSize(700, 520)
        camera_label.setStyleSheet(self.get_style('camera'))
        layout.addWidget(camera_label)
        
        # Status row
        status_layout = QHBoxLayout()
        status_label = QLabel("Status: Disconnected")
        status_label.setStyleSheet(self.get_style('status'))
        
        if cfg['enhanced']:  # Thermal camera gets extra info
            status_label.setAlignment(Qt.AlignLeft)
            status_layout.addWidget(status_label)
            
            min_max_label = QLabel("Min/Max: -- / -- C")
            min_max_label.setAlignment(Qt.AlignCenter)
            min_max_label.setStyleSheet(self.get_style('temp'))
            status_layout.addWidget(min_max_label)
            
            range_label = QLabel("Range: -- C")
            range_label.setAlignment(Qt.AlignRight)
            range_label.setStyleSheet(self.get_style('range'))
            status_layout.addWidget(range_label)
            
            layout.addLayout(status_layout)
            
            # Filter row for thermal
            filter_layout = QHBoxLayout()
            filter_status_label = QLabel("Filter: Initializing...")
            filter_status_label.setAlignment(Qt.AlignLeft)
            filter_status_label.setStyleSheet(self.get_style('filter_disabled'))
            filter_layout.addWidget(filter_status_label)
            
            filter_range_label = QLabel("Range: -- C")
            filter_range_label.setAlignment(Qt.AlignRight)
            filter_range_label.setStyleSheet(self.get_style('filter_disabled'))
            filter_layout.addWidget(filter_range_label)
            
            layout.addLayout(filter_layout)
            
            # Store thermal references
            self.thermal_label = camera_label
            self.thermal_status = status_label
            self.thermal_min_max = min_max_label
            self.thermal_range = range_label
            self.thermal_filter_status = filter_status_label
            self.thermal_filter_range = filter_range_label
        else:  # RGB camera - simple layout
            status_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(status_label)
            self.rgb_label = camera_label
            self.rgb_status = status_label
            
        return panel
    
    def setup_ui_style(self):
        """Apply theme and fonts in one simple function."""
        # Dark theme
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        self.setPalette(palette)
        
        # Font system - one place for all fonts
        self.fonts = {
            'main': self.create_font(18),
            'status': self.create_font(26), 
            'temp': self.create_font(28),
            'header': self.create_font(24)
        }
        self.setFont(self.fonts['main'])
    
    def create_font(self, size):
        """Create a bold font of specified size."""
        font = QFont()
        font.setPointSize(size)
        font.setBold(True)
        return font
    
    def get_style(self, element_type):
        """Get CSS style for different UI elements."""
        styles = {
            'camera': "border: 1px solid gray; background-color: #2a2a2a; font-size: 18px; font-weight: bold;",
            'status': "font-size: 26px; font-weight: bold;",
            'temp': "font-size: 28px; font-weight: bold; color: #4CAF50;",
            'range': "font-size: 26px; font-weight: bold; color: #2196F3;",
            'filter_enabled': "font-size: 28px; font-weight: bold; color: #4CAF50;",
            'filter_disabled': "font-size: 28px; font-weight: bold; color: #FF9800;"
        }
        return styles.get(element_type, "")
    
    def start_sensors(self):
        """Start both cameras."""
        # Try RGB cameras (external USB first)
        for camera_idx in [0, 1, 3, 4]:
            try:
                self.rgb_camera = RGBCameraCapture(camera_index=camera_idx, target_fps=30)
                if self.rgb_camera.start():
                    logger.info(f"RGB camera started on index {camera_idx}")
                    break
                self.rgb_camera = None
            except Exception as e:
                logger.debug(f"RGB camera index {camera_idx} failed: {e}")
                self.rgb_camera = None
        
        # Start thermal camera
        try:
            self.thermal_camera = ThermalCameraCapture(
                target_fps=15,
                temp_filter_enabled=self.temp_filter_enabled,
                temp_filter_min=self.temp_filter_min,
                temp_filter_max=self.temp_filter_max
            )
            if not self.thermal_camera.start():
                logger.warning("Thermal camera failed to start")
                self.thermal_camera = None
        except Exception as e:
            logger.error(f"Thermal camera error: {e}")
            self.thermal_camera = None
    
    def update_displays(self):
        """Update both camera displays - RGB and thermal with enhanced min/max info."""
        self.update_rgb_display()  # Now active for dual camera mode
        self.update_thermal_display()
    
    def update_rgb_display(self):
        """Update RGB camera display - active in dual camera mode."""
        if not self.rgb_camera or not self.rgb_camera.is_running():
            self.rgb_status.setText("Status: Disconnected")
            return
        
        # Get latest frame
        frame = self.rgb_camera.get_latest_frame()
        if frame is not None:
            # Convert to QPixmap and display
            height, width, channels = frame.shape
            bytes_per_line = channels * width
            qt_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # Scale to fit display
            scaled_pixmap = pixmap.scaled(self.rgb_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.rgb_label.setPixmap(scaled_pixmap)
            self.rgb_status.setText("Status: Connected")
        else:
            self.rgb_status.setText("Status: No Frame")
    
    def update_thermal_display(self):
        """Update thermal camera display with enhanced min/max information and filter status."""
        if not self.thermal_camera or not self.thermal_camera.is_running():
            self.thermal_status.setText("Status: Disconnected")
            self.thermal_min_max.setText("Min/Max: -- / -- C")
            self.thermal_range.setText("Range: -- C")
            self.thermal_filter_status.setText("Filter: Disconnected")
            self.thermal_filter_range.setText("Range: -- C")
            return
        
        # Update filter status display
        if self.temp_filter_enabled:
            self.thermal_filter_status.setText("🎯 Filter: ENABLED (Ctrl+F to toggle)")
            self.thermal_filter_range.setText(f"Range: {self.temp_filter_min}°C-{self.temp_filter_max}°C (Ctrl+T to change)")
            style = self.get_style('filter_enabled')
        else:
            self.thermal_filter_status.setText("🔄 Filter: DISABLED (Ctrl+F to toggle)")
            self.thermal_filter_range.setText("Range: All Temps (Ctrl+R to reload config)")
            style = self.get_style('filter_disabled')
            
        self.thermal_filter_status.setStyleSheet(style)
        self.thermal_filter_range.setStyleSheet(style)
        
        # Get latest frame (with min/max overlay if enabled)
        frame = self.thermal_camera.get_latest_frame()
        if frame is not None:
            # Convert to QPixmap and display
            height, width, channels = frame.shape
            bytes_per_line = channels * width
            qt_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # Scale to fit display
            scaled_pixmap = pixmap.scaled(self.thermal_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thermal_label.setPixmap(scaled_pixmap)
            
            # Update status based on filtering
            if hasattr(self.thermal_camera, 'enable_temp_filter') and self.thermal_camera.enable_temp_filter:
                self.thermal_status.setText("Status: Connected - Filtered Min/Max")
            else:
                self.thermal_status.setText("Status: Connected - Full Range Min/Max")
            
            # Update min/max information display
            min_max_data = self.thermal_camera.get_last_min_max_data()
            if min_max_data is not None:
                min_temp = min_max_data['min_temp']
                max_temp = min_max_data['max_temp']
                temp_range = min_max_data['temp_range']
                
                # Update status labels with color coding
                self.thermal_min_max.setText(f"🔵 {min_temp:.1f}C / 🔴 {max_temp:.1f}C")
                self.thermal_range.setText(f"Range: {temp_range:.1f}C")
                
                # Color code the range based on temperature spread
                if temp_range > 20:
                    self.thermal_range.setStyleSheet("color: #FF5722; font-weight: bold;")  # High range - red
                elif temp_range > 10:
                    self.thermal_range.setStyleSheet("color: #FF9800; font-weight: bold;")  # Medium range - orange
                else:
                    self.thermal_range.setStyleSheet("color: #4CAF50; font-weight: bold;")  # Low range - green
            else:
                if hasattr(self.thermal_camera, 'enable_temp_filter') and self.thermal_camera.enable_temp_filter:
                    self.thermal_min_max.setText("Min/Max: No temps in range")
                    self.thermal_range.setText("Range: No data")
                else:
                    self.thermal_min_max.setText("Min/Max: Processing...")
                    self.thermal_range.setText("Range: Processing...")
        else:
            self.thermal_status.setText("Status: No Frame")
            self.thermal_min_max.setText("Min/Max: -- / -- C")
            self.thermal_range.setText("Range: -- C")
    
    def update_temperature_filter_range(self, min_temp, max_temp, enabled=None):
        """
        Dynamically update the temperature filter range without restarting the application.
        
        Args:
            min_temp: New minimum temperature
            max_temp: New maximum temperature  
            enabled: Optional - whether to enable/disable the filter
        """
        logger.info(f"Updating temperature filter range: {min_temp}°C to {max_temp}°C")
        
        # Update GUI settings
        self.temp_filter_min = min_temp
        self.temp_filter_max = max_temp
        if enabled is not None:
            self.temp_filter_enabled = enabled
        
        # Update thermal camera settings if it exists
        if self.thermal_camera and hasattr(self.thermal_camera, 'set_temperature_filter_range'):
            self.thermal_camera.set_temperature_filter_range(min_temp, max_temp)
            if enabled is not None:
                self.thermal_camera.enable_temp_filter = enabled
                
        logger.info(f"Temperature filter updated successfully")
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for runtime temperature control."""
        from PyQt5.QtWidgets import QShortcut
        
        # Ctrl+T: Update temperature range
        self.temp_range_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        self.temp_range_shortcut.activated.connect(self.prompt_temperature_range_update)
        
        # Ctrl+R: Reload config from main.py  
        self.reload_config_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.reload_config_shortcut.activated.connect(self.reload_config_from_main)
        
        # Ctrl+F: Toggle temperature filter
        self.toggle_filter_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.toggle_filter_shortcut.activated.connect(self.toggle_temperature_filter)
        
        # Ctrl+P: Cycle color palette
        self.palette_shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        self.palette_shortcut.activated.connect(self.cycle_color_palette)
    
    def prompt_temperature_range_update(self):
        """Show dialog to update temperature range."""
        try:
            # Get current values
            current_min = self.temp_filter_min
            current_max = self.temp_filter_max
            
            # Create dialogs with larger fonts
            dialog_font = QFont()
            dialog_font.setPointSize(14)
            dialog_font.setBold(True)
            
            # Prompt for new minimum temperature
            min_dialog = QInputDialog(self)
            min_dialog.setFont(dialog_font)
            min_dialog.setWindowTitle("Update Temperature Range")
            min_dialog.setLabelText(f"Enter minimum temperature (°C):\nCurrent: {current_min}°C")
            min_dialog.setDoubleValue(current_min)
            min_dialog.setDoubleRange(-50.0, 200.0)
            min_dialog.setDoubleDecimals(1)
            
            if not min_dialog.exec_():
                return
            min_temp = min_dialog.doubleValue()
                
            # Prompt for new maximum temperature  
            max_dialog = QInputDialog(self)
            max_dialog.setFont(dialog_font)
            max_dialog.setWindowTitle("Update Temperature Range")
            max_dialog.setLabelText(f"Enter maximum temperature (°C):\nCurrent: {current_max}°C")
            max_dialog.setDoubleValue(current_max)
            max_dialog.setDoubleRange(min_temp + 0.1, 200.0)
            max_dialog.setDoubleDecimals(1)
            
            if not max_dialog.exec_():
                return
            max_temp = max_dialog.doubleValue()
                
            # Validate range
            if min_temp >= max_temp:
                logger.error(f"Invalid range: {min_temp}°C >= {max_temp}°C")
                return
                
            # Apply the update
            self.update_temperature_filter_range(min_temp, max_temp)
            logger.info(f"Temperature range updated via keyboard shortcut: {min_temp}°C to {max_temp}°C")
            
        except Exception as e:
            logger.error(f"Error updating temperature range: {e}")
    
    def reload_config_from_main(self):
        """Reload configuration values from main.py without restarting."""
        try:
            # Re-import main module to get fresh values
            import importlib
            import main
            importlib.reload(main)
            
            # Get fresh config
            config = main.get_current_config()
            
            # Update our settings
            self.temp_filter_enabled = config['enable_temp_filter']
            self.temp_filter_min = config['filter_temp_min'] 
            self.temp_filter_max = config['filter_temp_max']
            
            # Update thermal camera if available
            if self.thermal_camera:
                self.thermal_camera.enable_temp_filter = self.temp_filter_enabled
                self.thermal_camera.filter_temp_min = self.temp_filter_min
                self.thermal_camera.filter_temp_max = self.temp_filter_max
                
            logger.info(f"Config reloaded from main.py:")
            logger.info(f"   Filter enabled: {self.temp_filter_enabled}")
            logger.info(f"   Range: {self.temp_filter_min}°C to {self.temp_filter_max}°C")
            
        except Exception as e:
            logger.error(f"Error reloading config: {e}")
    
    def toggle_temperature_filter(self):
        """Toggle temperature filter on/off."""
        try:
            self.temp_filter_enabled = not self.temp_filter_enabled
            
            # Update thermal camera if available
            if self.thermal_camera:
                self.thermal_camera.enable_temp_filter = self.temp_filter_enabled
                
            status = "ENABLED" if self.temp_filter_enabled else "DISABLED"
            logger.info(f"Temperature filter {status}")
            
        except Exception as e:
            logger.error(f"Error toggling temperature filter: {e}")
    
    def cycle_color_palette(self):
        """Cycle through thermal color palettes."""
        try:
            if self.thermal_camera and self.thermal_camera.is_running():
                palette_name = self.thermal_camera.cycle_color_palette()
                logger.info(f"Switched to {palette_name} color palette")
            else:
                logger.warning("Thermal camera not available for palette change")
                
        except Exception as e:
            logger.error(f"Error cycling color palette: {e}")
    
    def closeEvent(self, event):
        """Handle GUI close event."""
        logger.info("Shutting down GUI v8 Dual Camera...")
        
        # Stop both cameras
        if self.rgb_camera:
            self.rgb_camera.stop()
        if self.thermal_camera:
            self.thermal_camera.stop()
        
        # Stop timer
        self.update_timer.stop()
        
        logger.info("GUI v8 Dual Camera shutdown complete")
        event.accept() 
