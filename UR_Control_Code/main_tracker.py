"""
Main Face and Thermal Tracking Application
Integrates all components for a clean, modular tracking system
"""

import cv2
import numpy as np
import time
from camera_manager import CameraManager
from detection_algorithms import FaceDetector, ThermalDetector
from robot_controller import RobotController
from spacemouse_controller import SpaceMouseController
from config import *


class FaceThermalTracker:
    """Main application class that coordinates all components"""
    
    def __init__(self):
        # Initialize components
        self.camera_manager = CameraManager()
        self.face_detector = FaceDetector()
        self.thermal_detector = ThermalDetector()
        self.robot_controller = RobotController()
        self.spacemouse_controller = SpaceMouseController(self.robot_controller)
        
        # Running state
        self.running = False
        
        # Position smoothing for face tracking
        self.face_history = []
    
    def smooth_face_position(self, face_x, face_y):
        """Apply moving average filter to face position."""
        now = time.time()
        
        # Add current position to history
        self.face_history.append((now, face_x, face_y))
        
        # Remove old entries outside filter window
        self.face_history = [(t, x, y) for (t, x, y) in self.face_history 
                           if now - t <= FILTER_WINDOW]
        
        # Calculate average
        if len(self.face_history) > 0:
            avg_x = sum(x for (_, x, _) in self.face_history) / len(self.face_history)
            avg_y = sum(y for (_, _, y) in self.face_history) / len(self.face_history)
            return avg_x, avg_y
        
        return face_x, face_y
    
    def initialize_system(self):
        """Initialize all system components."""
        print("\n=== FACE & THERMAL TRACKER ===")
        print("F: Toggle face tracking, T: Toggle thermal tracking, SPACE: EMERGENCY STOP")
        
        # Initialize robot
        if not self.robot_controller.connect():
            return False
        
        if not self.robot_controller.move_to_starting_position():
            self.robot_controller.cleanup()
            return False
        
        # Initialize cameras
        if not self.camera_manager.init_regular_camera():
            self.robot_controller.cleanup()
            return False
        
        if not self.camera_manager.init_thermal_camera():
            self.robot_controller.cleanup()
            return False
        
        # Initialize space mouse (optional - won't fail if not connected)
        spacemouse_status = self.spacemouse_controller.connect_spacemouse()
        if spacemouse_status:
            print("✓ Space Mouse connected!")
        else:
            print("⚠ Space Mouse not found - manual controls available via arrows only")
        
        print("\n✓ All systems ready!")
        print("Controls:")
        print("  F: Toggle face tracking ON/OFF")
        print("  T: Toggle thermal tracking ON/OFF")
        print("  H: Return to starting position")
        print("  SPACE: EMERGENCY STOP")
        print("  UP/DOWN arrows: Move forward/backward (X-axis) - works only when both tracking modes are OFF")
        print("  ESC: Exit")
        print("\nBoth tracking modes start OFF - press F for face tracking or T for thermal tracking!")
        print("Note: Only one tracking mode can be active at a time. Max speed: Face=2.5m/s, Thermal=0.5m/s")
        print("Space Mouse: Automatically active when both tracking modes are OFF")
        
        return True
    
    def process_frame_data(self, regular_frame, thermal_frame):
        """Process both camera frames and update detection data."""
        # Process face detection on regular camera
        face_data = self.face_detector.detect(regular_frame)
        if face_data:
            face_x, face_y = face_data[0], face_data[1]
            # Apply smoothing for face tracking
            smooth_x, smooth_y = self.smooth_face_position(face_x, face_y)
            self.robot_controller.last_face_position = (smooth_x, smooth_y)
            
            # Draw face detection
            self.face_detector.draw_detection(regular_frame, face_data)
        else:
            self.robot_controller.last_face_position = None
        
        # Process thermal detection on thermal camera
        thermal_data = self.thermal_detector.find_hottest_point(thermal_frame)
        if thermal_data:
            hot_x, hot_y = thermal_data[0], thermal_data[1]
            self.robot_controller.last_thermal_position = (hot_x, hot_y)
            
            # Update robot controller with thermal center coordinates
            thermal_center_x, thermal_center_y = self.camera_manager.get_thermal_center()
            self.robot_controller.thermal_center_x = thermal_center_x
            self.robot_controller.thermal_center_y = thermal_center_y
            
            # Draw thermal detection
            self.thermal_detector.draw_detection(thermal_frame, thermal_data)
        else:
            self.robot_controller.last_thermal_position = None
    
    def draw_ui_elements(self, regular_frame, thermal_frame):
        """Draw UI elements on both frames."""
        # Get center coordinates
        regular_center_x, regular_center_y = self.camera_manager.get_regular_center()
        thermal_center_x, thermal_center_y = self.camera_manager.get_thermal_center()
        
        # Draw crosshairs and deadzones
        self.camera_manager.draw_crosshair_and_deadzone(regular_frame, regular_center_x, regular_center_y)
        self.camera_manager.draw_crosshair_and_deadzone(thermal_frame, thermal_center_x, thermal_center_y)
        
        # Add tracking status indicators to each frame
        # Regular camera frame
        face_color = (0, 255, 0) if self.robot_controller.face_tracking_active else (128, 128, 128)
        cv2.putText(regular_frame, "FACE CAMERA", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, face_color, 2)
        if self.robot_controller.face_tracking_active:
            cv2.putText(regular_frame, "ACTIVE", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.rectangle(regular_frame, (0, 0), (regular_frame.shape[1]-1, regular_frame.shape[0]-1), 
                         (0, 255, 0), 3)
        
        # Thermal camera frame
        thermal_color = (0, 0, 255) if self.robot_controller.thermal_tracking_active else (128, 128, 128)
        cv2.putText(thermal_frame, "THERMAL CAMERA", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, thermal_color, 2)
        if self.robot_controller.thermal_tracking_active:
            cv2.putText(thermal_frame, "ACTIVE", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.rectangle(thermal_frame, (0, 0), (thermal_frame.shape[1]-1, thermal_frame.shape[0]-1), 
                         (0, 0, 255), 3)
    
    def create_combined_display(self, regular_frame, thermal_frame):
        """Create the combined side-by-side display."""
        # Combine frames side by side
        combined_frame = np.hstack((regular_frame, thermal_frame))
        
        # Add overall status
        if self.robot_controller.face_tracking_active:
            status_text = "FACE TRACKING ACTIVE (Max Speed: 2.5 m/s)"
            status_color = (0, 255, 0)
        elif self.robot_controller.thermal_tracking_active:
            status_text = "THERMAL TRACKING ACTIVE (Max Speed: 0.5 m/s)"
            status_color = (0, 0, 255)
        elif self.spacemouse_controller.spacemouse_active:
            status_text = f"SPACE MOUSE CONTROL ACTIVE - Max Speed: {SPACEMOUSE_MAX_TRANSLATION_SPEED} m/s"
            status_color = (255, 0, 255)  # Magenta for space mouse
        else:
            if self.spacemouse_controller.spacemouse_connected:
                status_text = f"TRACKING OFF - Space Mouse Active (Max: {SPACEMOUSE_MAX_TRANSLATION_SPEED} m/s)"
            else:
                status_text = "TRACKING OFF - Arrow keys available"
            status_color = (255, 255, 0)
        
        cv2.putText(combined_frame, status_text, (10, combined_frame.shape[0] - 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
        
        # Controls info
        cv2.putText(combined_frame, "F: Face | T: Thermal | H: Home | SPACE: Emergency Stop | UP/DOWN: X move | ESC: Exit", 
                   (10, combined_frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                   (255, 255, 255), 2)
        
        return combined_frame
    
    def handle_key_input(self, key):
        """Handle keyboard input."""
        if key == 27:  # ESC
            print("Exiting...")
            return False
        elif key == ord('f') or key == ord('F'):  # F - Face tracking toggle
            new_state = not self.robot_controller.face_tracking_active
            self.robot_controller.set_face_tracking(new_state)
            status_text = "ACTIVATED" if new_state else "DEACTIVATED"
            print(f"Face tracking {status_text}")
        elif key == ord(' '):  # SPACE - Emergency Stop
            self.robot_controller.emergency_stop()
        elif key == ord('t') or key == ord('T'):  # T - Thermal tracking toggle
            new_state = not self.robot_controller.thermal_tracking_active
            self.robot_controller.set_thermal_tracking(new_state)
            status_text = "ACTIVATED" if new_state else "DEACTIVATED"
            print(f"Thermal tracking {status_text}")
        elif key == ord('h') or key == ord('H'):  # H - Return to starting position
            print("H pressed - Returning to starting position...")
            self.robot_controller.return_to_starting_position()
        
        return True
    
    def run(self):
        """Main execution loop."""
        if not self.initialize_system():
            return
        
        # Start robot control threads
        self.robot_controller.start_control_threads()
        
        # Start space mouse thread if connected
        if self.spacemouse_controller.spacemouse_connected:
            self.spacemouse_controller.start_spacemouse_thread()
        
        self.running = True
        
        try:
            while self.running:
                # Capture from both cameras
                ret_regular, regular_frame = self.camera_manager.capture_regular_frame()
                ret_thermal, thermal_frame = self.camera_manager.capture_thermal_frame()
                
                if not ret_regular or not ret_thermal:
                    print("Failed to capture frames")
                    continue
                
                # Process detection algorithms
                self.process_frame_data(regular_frame, thermal_frame)
                
                # Draw UI elements
                self.draw_ui_elements(regular_frame, thermal_frame)
                
                # Create combined display
                combined_frame = self.create_combined_display(regular_frame, thermal_frame)
                
                # Show frame
                cv2.imshow('Face & Thermal Tracker', combined_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if not self.handle_key_input(key):
                    break
                
        except Exception as e:
            print(f"Main loop error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up all resources."""
        print("Cleaning up...")
        self.running = False
        
        # Cleanup components
        self.robot_controller.cleanup()
        self.camera_manager.cleanup()
        self.spacemouse_controller.cleanup()
        
        # Close OpenCV windows
        cv2.destroyAllWindows()
        
        print("✓ Cleanup complete")


# ===============================================
# MAIN EXECUTION
# ===============================================
if __name__ == "__main__":
    tracker = FaceThermalTracker()
    try:
        tracker.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        tracker.cleanup()
    except Exception as e:
        print(f"Error: {e}")
        tracker.cleanup()