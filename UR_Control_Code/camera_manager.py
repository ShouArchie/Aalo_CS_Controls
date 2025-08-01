"""
Camera Manager for Face and Thermal Tracking System
Handles initialization and management of both regular and thermal cameras
"""

import cv2
import numpy as np
from config import *


class CameraManager:
    """Manages regular and thermal cameras"""
    
    def __init__(self):
        self.regular_cap = None
        self.thermal_cap = None
        self.thermal_center_x = FRAME_WIDTH // 2
        self.thermal_center_y = FRAME_HEIGHT // 2
        self.regular_center_x = FRAME_WIDTH // 2
        self.regular_center_y = FRAME_HEIGHT // 2
    
    def init_regular_camera(self):
        """Initialize regular camera with specified FPS."""
        try:
            print("Initializing regular camera...")
            self.regular_cap = cv2.VideoCapture(REGULAR_CAMERA_INDEX)
            
            if not self.regular_cap.isOpened():
                print(f"✗ Could not open regular camera at index {REGULAR_CAMERA_INDEX}")
                return False
            
            # Set camera properties
            self.regular_cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            self.regular_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            self.regular_cap.set(cv2.CAP_PROP_FPS, REGULAR_CAMERA_FPS)
            
            # Get actual properties
            actual_width = int(self.regular_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.regular_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.regular_cap.get(cv2.CAP_PROP_FPS)
            
            print(f"✓ Regular camera ready: {actual_width}x{actual_height} @ {actual_fps} FPS")
            return True
            
        except Exception as e:
            print(f"✗ Regular camera failed: {e}")
            return False
    
    def init_thermal_camera(self):
        """Initialize thermal camera with specified FPS."""
        try:
            print("Initializing thermal camera...")
            self.thermal_cap = cv2.VideoCapture(THERMAL_CAMERA_INDEX)
            
            if not self.thermal_cap.isOpened():
                print(f"✗ Could not open thermal camera at index {THERMAL_CAMERA_INDEX}")
                return False
            
            # Set camera properties
            self.thermal_cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            self.thermal_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            self.thermal_cap.set(cv2.CAP_PROP_FPS, THERMAL_CAMERA_FPS)
            
            # Get actual properties
            actual_width = int(self.thermal_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.thermal_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.thermal_cap.get(cv2.CAP_PROP_FPS)
            
            print(f"✓ Thermal camera ready: {actual_width}x{actual_height} @ {actual_fps} FPS")
            return True
            
        except Exception as e:
            print(f"✗ Thermal camera failed: {e}")
            return False
    
    def capture_regular_frame(self):
        """Capture and return a frame from the regular camera."""
        if self.regular_cap is None:
            return False, None
        
        ret, frame = self.regular_cap.read()
        if ret:
            # Resize to target dimensions
            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        return ret, frame
    
    def capture_thermal_frame(self):
        """Capture, process, and return a frame from the thermal camera."""
        if self.thermal_cap is None:
            return False, None
        
        ret, frame = self.thermal_cap.read()
        if not ret:
            return False, None
        
        # Process thermal frame (flip and crop)
        frame = cv2.rotate(frame, cv2.ROTATE_180)
        frame = frame[THERMAL_CROP_TOP:, :-THERMAL_CROP_RIGHT]
        
        # Resize to target dimensions
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        
        # Update thermal center coordinates
        self.thermal_center_x = frame.shape[1] // 2
        self.thermal_center_y = frame.shape[0] // 2
        
        return True, frame
    
    def get_thermal_center(self):
        """Get the center coordinates of the thermal camera frame."""
        return self.thermal_center_x, self.thermal_center_y
    
    def get_regular_center(self):
        """Get the center coordinates of the regular camera frame."""
        return self.regular_center_x, self.regular_center_y
    
    def draw_crosshair_and_deadzone(self, frame, center_x, center_y, deadzone_radius=DEADZONE_RADIUS):
        """Draw center crosshair and deadzone circle on a frame."""
        # Center crosshair
        cv2.circle(frame, (center_x, center_y), 3, (0, 0, 255), -1)
        cv2.line(frame, (center_x-15, center_y), (center_x+15, center_y), (0, 0, 255), 2)
        cv2.line(frame, (center_x, center_y-15), (center_x, center_y+15), (0, 0, 255), 2)
        
        # Deadzone circle
        cv2.circle(frame, (center_x, center_y), deadzone_radius, (255, 255, 0), 2)
    
    def cleanup(self):
        """Release camera resources."""
        if self.regular_cap:
            self.regular_cap.release()
        if self.thermal_cap:
            self.thermal_cap.release()
        print("✓ Cameras released") 