"""
HT301 Thermal Camera Capture Module

Optimized thermal camera interface with temperature range filtering.
Configuration controlled from main.py for easy adjustment.
"""

import sys
import os
import logging
from typing import Optional, Tuple, Dict
import numpy as np
import cv2

# Configure logging
logger = logging.getLogger(__name__)

# Add HT301 library path - relative to this script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
thermal_lib_path = os.path.join(script_dir, "Python Context HT301 Thermal Stack", "IR-Py-Thermal-master")
sys.path.insert(0, thermal_lib_path)

try:
    import irpythermal
    HT301_AVAILABLE = True
    logger.info("HT301 thermal camera module available")
except ImportError as e:
    HT301_AVAILABLE = False
    logger.error(f"HT301 thermal camera not available: {e}")


class ThermalCameraCapture:
    """HT301 Thermal Camera Capture with configurable temperature range filtering."""
    
    def __init__(self, target_fps=25, temp_filter_enabled=True, temp_filter_min=0.0, temp_filter_max=50.0):
        self.running = False
        self.camera = None
        self.target_fps = target_fps
        
        # Display settings
        self.colormap = cv2.COLORMAP_PLASMA
        self.auto_exposure = True
        self.temp_min = 0
        self.temp_max = 50
        
        # Min/Max detection settings
        self.show_min_max = True
        self.last_min_max_data = None
        
        # Temperature filter configuration (from main.py)
        self.enable_temp_filter = temp_filter_enabled
        self.filter_temp_min = temp_filter_min
        self.filter_temp_max = temp_filter_max
        
        logger.info(f"HT301 thermal camera initialized (target_fps={target_fps})")
        if self.enable_temp_filter:
            logger.info(f"Temperature filter enabled: {self.filter_temp_min}C to {self.filter_temp_max}C")
        else:
            logger.info("Temperature filter disabled - showing all temperatures")
    
    def start(self) -> bool:
        """Start HT301 thermal camera using our working solution."""
        if not HT301_AVAILABLE:
            logger.error("HT301 thermal camera not available")
            return False
        
        try:
            logger.info("Starting HT301 thermal camera...")
            
            # Initialize camera using proven approach
            self.camera = irpythermal.Camera()
            logger.info(f"HT301 camera initialized: {self.camera.width}x{self.camera.height}")
            
            self.running = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to start HT301 thermal camera: {e}")
            return False
    
    def stop(self):
        """Stop HT301 thermal camera."""
        if not self.running:
            return
            
        logger.info("Stopping HT301 thermal camera...")
        self.running = False
        
        if self.camera:
            try:
                self.camera.release()
            except Exception as e:
                logger.warning(f"Warning during camera release: {e}")
                
        self.camera = None
        logger.info("HT301 thermal camera stopped")
    
    def apply_temperature_filter(self, temp_frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply temperature range filter to the thermal frame.
        
        Args:
            temp_frame: Raw temperature data array
            
        Returns:
            Tuple of (filtered_temp_frame, mask) where:
            - filtered_temp_frame: Temperature data with out-of-range values set to NaN
            - mask: Boolean mask indicating which pixels are within range
        """
        if not self.enable_temp_filter:
            # No filtering - return original data with all-True mask
            mask = np.ones_like(temp_frame, dtype=bool)
            return temp_frame, mask
        
        # Create mask for pixels within the temperature range
        mask = (temp_frame >= self.filter_temp_min) & (temp_frame <= self.filter_temp_max)
        
        # Create filtered temperature frame
        filtered_temp_frame = temp_frame.copy()
        filtered_temp_frame[~mask] = np.nan  # Set out-of-range values to NaN
        
        return filtered_temp_frame, mask
    
    def get_min_max_temperatures(self) -> Optional[Dict]:
        """
        Get minimum and maximum temperatures with their pixel coordinates.
        Only considers temperatures within the filter range if enabled.
        
        Returns:
            Dict with keys: 'min_temp', 'max_temp', 'min_coords', 'max_coords'
            or None if no data available
        """
        if not self.running or not self.camera:
            return None
            
        try:
            # Get raw frame and temperature data
            ret, frame = self.camera.read()
            if not ret:
                return None
            
            info, temp_lut = self.camera.info()
            temp_frame = temp_lut[frame]
            
            # Apply temperature filter
            filtered_temp_frame, mask = self.apply_temperature_filter(temp_frame)
            
            # Check if any pixels are within range
            if not np.any(mask):
                logger.warning(f"No temperatures found in range {self.filter_temp_min}C to {self.filter_temp_max}C")
                return None
            
            # Find min and max temperatures only within the filtered range
            valid_temps = filtered_temp_frame[mask]
            min_temp = np.min(valid_temps)
            max_temp = np.max(valid_temps)
            
            # Find coordinates of min and max temperatures within the filtered data
            min_idx = np.unravel_index(np.nanargmin(filtered_temp_frame), filtered_temp_frame.shape)
            max_idx = np.unravel_index(np.nanargmax(filtered_temp_frame), filtered_temp_frame.shape)
            
            # Convert to (x, y) coordinates (note: numpy is (row, col) = (y, x))
            min_coords = (int(min_idx[1]), int(min_idx[0]))  # (x, y)
            max_coords = (int(max_idx[1]), int(max_idx[0]))  # (x, y)
            
            min_max_data = {
                'min_temp': round(float(min_temp), 1),
                'max_temp': round(float(max_temp), 1),
                'min_coords': min_coords,
                'max_coords': max_coords,
                'temp_range': round(float(max_temp - min_temp), 1),
                'filtered': self.enable_temp_filter,
                'filter_range': f"{self.filter_temp_min}C-{self.filter_temp_max}C" if self.enable_temp_filter else "All"
            }
            
            # Cache for GUI display
            self.last_min_max_data = min_max_data
            
            return min_max_data
            
        except Exception as e:
            logger.error(f"Error getting min/max temperatures: {e}")
            return None
    
    def draw_min_max_overlay(self, display_frame: np.ndarray, min_max_data: Dict) -> np.ndarray:
        """Draw min/max temperature overlays on the display frame."""
        if min_max_data is None:
            return display_frame
        
        overlay_frame = display_frame.copy()
        
        # Extract temperature data and coordinates
        min_temp = min_max_data['min_temp']
        max_temp = min_max_data['max_temp']
        min_coords = min_max_data['min_coords']
        max_coords = min_max_data['max_coords']
        
        # Drawing parameters
        marker_size = 4
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        
        # Draw cold spot (blue)
        cv2.circle(overlay_frame, min_coords, marker_size, (0, 100, 255), thickness)
        cv2.circle(overlay_frame, min_coords, marker_size + 2, (255, 255, 255), 1)
        
        min_label = f"COLD: {min_temp:.1f}C"
        label_pos = (min_coords[0] + 10, min_coords[1] - 8)
        
        # Keep labels within frame bounds
        if label_pos[0] + 100 > overlay_frame.shape[1]:
            label_pos = (min_coords[0] - 100, min_coords[1] - 8)
        if label_pos[1] < 15:
            label_pos = (label_pos[0], min_coords[1] + 20)
            
        cv2.putText(overlay_frame, min_label, label_pos, font, font_scale, (0, 100, 255), thickness)
        cv2.putText(overlay_frame, min_label, label_pos, font, font_scale, (255, 255, 255), 1)
        
        # Draw hot spot (red)
        cv2.circle(overlay_frame, max_coords, marker_size, (0, 0, 255), thickness)
        cv2.circle(overlay_frame, max_coords, marker_size + 2, (255, 255, 255), 1)
        
        max_label = f"HOT: {max_temp:.1f}C"
        label_pos = (max_coords[0] + 10, max_coords[1] - 8)
        
        # Keep labels within frame bounds
        if label_pos[0] + 100 > overlay_frame.shape[1]:
            label_pos = (max_coords[0] - 100, max_coords[1] - 8)
        if label_pos[1] < 15:
            label_pos = (label_pos[0], max_coords[1] + 20)
            
        cv2.putText(overlay_frame, max_label, label_pos, font, font_scale, (0, 0, 255), thickness)
        cv2.putText(overlay_frame, max_label, label_pos, font, font_scale, (255, 255, 255), 1)
        
        return overlay_frame
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get latest thermal frame - using our proven processing pipeline with optional min/max overlay and temperature filtering."""
        if not self.running or not self.camera:
            return None
            
        try:
            # Capture frame using proven method
            ret, frame = self.camera.read()
            if not ret:
                return None
            
            # Get temperature info using proven method
            info, temp_lut = self.camera.info()
            temp_frame = temp_lut[frame]
            
            # Apply temperature range filter
            filtered_temp_frame, temp_mask = self.apply_temperature_filter(temp_frame)
            
            # Get min/max data if enabled (from filtered data)
            min_max_data = None
            if self.show_min_max:
                # Calculate min/max from the filtered temp_frame
                if np.any(temp_mask):  # Only if there are valid temperatures in range
                    valid_temps = filtered_temp_frame[temp_mask]
                    min_temp = np.min(valid_temps)
                    max_temp = np.max(valid_temps)
                    min_idx = np.unravel_index(np.nanargmin(filtered_temp_frame), filtered_temp_frame.shape)
                    max_idx = np.unravel_index(np.nanargmax(filtered_temp_frame), filtered_temp_frame.shape)
                    
                    min_coords = (int(min_idx[1]), int(min_idx[0]))  # (x, y)
                    max_coords = (int(max_idx[1]), int(max_idx[0]))  # (x, y)
                    
                    min_max_data = {
                        'min_temp': round(float(min_temp), 1),
                        'max_temp': round(float(max_temp), 1),
                        'min_coords': min_coords,
                        'max_coords': max_coords,
                        'temp_range': round(float(max_temp - min_temp), 1),
                        'filtered': self.enable_temp_filter,
                        'filter_range': f"{self.filter_temp_min}C-{self.filter_temp_max}C" if self.enable_temp_filter else "All"
                    }
                    
                    # Cache for GUI display
                    self.last_min_max_data = min_max_data
            
            # Process for display using filtered data
            display_temp_frame = filtered_temp_frame.copy()
            
            if self.auto_exposure and np.any(temp_mask):
                # Auto-adjust temperature range from valid (filtered) temperatures only
                valid_temps = display_temp_frame[temp_mask]
                temp_min, temp_max = np.percentile(valid_temps, [1, 99])
                self.temp_min = temp_min
                self.temp_max = temp_max
            elif self.enable_temp_filter:
                # Use filter range for display normalization
                self.temp_min = self.filter_temp_min
                self.temp_max = self.filter_temp_max
            
            # Normalize temperature data for display
            # Handle NaN values (out-of-range temperatures)
            temp_norm = np.zeros_like(display_temp_frame)
            valid_mask = ~np.isnan(display_temp_frame)
            
            if np.any(valid_mask):
                temp_norm[valid_mask] = np.clip(
                    (display_temp_frame[valid_mask] - self.temp_min) / (self.temp_max - self.temp_min + 1e-6), 
                    0, 1
                )
            
            # Convert to 8-bit and apply colormap
            temp_norm_8bit = (temp_norm * 255).astype(np.uint8)
            
            # Apply colormap
            display_frame = cv2.applyColorMap(temp_norm_8bit, self.colormap)
            
            # Set out-of-range pixels to dark gray/black
            if self.enable_temp_filter:
                out_of_range_color = [20, 20, 20]  # Dark gray
                display_frame[~temp_mask] = out_of_range_color
            
            # Convert BGR to RGB for Qt display
            display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            
            # Add min/max overlay if enabled
            if self.show_min_max and min_max_data is not None:
                display_frame = self.draw_min_max_overlay(display_frame, min_max_data)
            
            return display_frame
            
        except Exception as e:
            logger.error(f"Error getting HT301 frame: {e}")
            return None
    
    def is_running(self) -> bool:
        """Check if camera is running."""
        return self.running and self.camera is not None
    
    def get_temperature_at_point(self, x: int, y: int) -> Optional[float]:
        """Get temperature at specific pixel coordinates - rounded to 1 decimal place."""
        if not self.running or not self.camera:
            return None
            
        try:
            ret, frame = self.camera.read()
            if not ret:
                return None
            
            info, temp_lut = self.camera.info()
            temp_frame = temp_lut[frame]
            
            if 0 <= y < temp_frame.shape[0] and 0 <= x < temp_frame.shape[1]:
                try:
                    temp_value = float(temp_frame[y, x])
                    return round(temp_value, 1)  # Cap at 1 decimal place
                except:
                    pass
        except:
            pass
        return None
    
    def calibrate_camera(self):
        """Calibrate the thermal camera."""
        if self.camera and self.running:
            try:
                logger.info("Calibrating HT301 camera...")
                self.camera.calibrate()
                logger.info("HT301 calibration complete")
                return True
            except Exception as e:
                logger.error(f"Calibration failed: {e}")
                return False
        return False
    
    def cycle_color_palette(self):
        """Cycle through selected color palettes: Plasma, Jet, and Viridis."""
        colormaps = [
            (cv2.COLORMAP_PLASMA, "PLASMA"),
            (cv2.COLORMAP_JET, "JET"),
            (cv2.COLORMAP_VIRIDIS, "VIRIDIS")
        ]
        
        # Find current index and cycle to next
        current_idx = 0
        for i, (cmap, name) in enumerate(colormaps):
            if cmap == self.colormap:
                current_idx = i
                break
        
        next_idx = (current_idx + 1) % len(colormaps)
        self.colormap, palette_name = colormaps[next_idx]
        
        logger.info(f"Switched to {palette_name} colormap")
        return palette_name
    
    def trigger_manual_ffc(self):
        """Trigger manual flat field correction (calibration)."""
        return self.calibrate_camera()

    def toggle_min_max_overlay(self) -> bool:
        """Toggle min/max overlay display on/off."""
        self.show_min_max = not self.show_min_max
        status = "enabled" if self.show_min_max else "disabled"
        logger.info(f"Min/Max overlay {status}")
        return self.show_min_max
    
    def get_last_min_max_data(self) -> Optional[Dict]:
        """Get the last cached min/max data for GUI display."""
        return self.last_min_max_data

    def toggle_temperature_filter(self) -> bool:
        """Toggle temperature range filter on/off."""
        self.enable_temp_filter = not self.enable_temp_filter
        status = "enabled" if self.enable_temp_filter else "disabled"
        if self.enable_temp_filter:
            logger.info(f"Temperature filter {status}: {self.filter_temp_min}C to {self.filter_temp_max}C")
        else:
            logger.info(f"Temperature filter {status} - showing all temperatures")
        return self.enable_temp_filter
    
    def set_temperature_filter_range(self, min_temp: float, max_temp: float) -> bool:
        """
        Update the temperature filter range.
        
        Args:
            min_temp: Minimum temperature for filter
            max_temp: Maximum temperature for filter
            
        Returns:
            True if range was updated successfully
        """
        if min_temp >= max_temp:
            logger.error(f"Invalid temperature range: {min_temp}C >= {max_temp}C")
            return False
        
        self.filter_temp_min = float(min_temp)
        self.filter_temp_max = float(max_temp)
        
        logger.info(f"Temperature filter range updated: {self.filter_temp_min}C to {self.filter_temp_max}C")
        return True


if __name__ == "__main__":
    """Test HT301 thermal camera."""
    logging.basicConfig(level=logging.INFO)
    
    print("Testing HT301 Thermal Camera")
    
    # Test with temperature filtering
    camera = ThermalCameraCapture(
        target_fps=25,
        temp_filter_enabled=True,
        temp_filter_min=0.0,
        temp_filter_max=20.0
    )
    
    if camera.start():
        print("Camera started successfully")
        print("Press Ctrl+C to stop...")
        try:
            import time
            while True:
                frame = camera.get_latest_frame()
                min_max_data = camera.get_last_min_max_data()
                if min_max_data:
                    print(f"Min: {min_max_data['min_temp']}C, Max: {min_max_data['max_temp']}C")
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️ Stopping...")
        
        camera.stop()
        print("Test complete")
    else:
        print("Failed to start camera") 