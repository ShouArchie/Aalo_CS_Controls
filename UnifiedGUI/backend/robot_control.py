"""
Robot Control Integration for UnifiedGUI
Integrates the UR Control Code system with FastAPI backend
"""

import sys
import os
import threading
import time
from pathlib import Path

# Add UR_Control_Code to path
UR_CONTROL_PATH = Path(__file__).resolve().parents[2] / 'UR_Control_Code'
sys.path.insert(0, str(UR_CONTROL_PATH))

try:
    from robot_controller import RobotController
    from detection_algorithms import ThermalDetector
    from spacemouse_controller import SpaceMouseController
    print("✓ Successfully imported UR control modules")
except ImportError as e:
    print(f"✗ Failed to import UR control modules: {e}")
    RobotController = None
    ThermalDetector = None
    SpaceMouseController = None


class UnifiedRobotController:
    """Unified robot controller for the GUI"""
    
    def __init__(self):
        self.robot_controller = None
        self.thermal_detector = None
        self.spacemouse_controller = None
        self.robot_ip = "192.168.10.255"
        self.connected = False
        self.thermal_tracking_active = False
        self.thermal_tracking_thread = None
        
        # Home joints configuration (in degrees)
        self.home_joints_deg = [206.06, -66.96, 104.35, 232.93, 269.26, 118.75]
        
    def connect(self, ip: str) -> dict:
        """Connect to the robot at specified IP"""
        try:
            if RobotController is None:
                return {"connected": False, "error": "Robot controller not available"}
            
            self.robot_ip = ip
            self.robot_controller = RobotController()
            
            # Connect directly with IP instead of using config
            print(f"Connecting to robot at {ip}...")
            import urx
            try:
                self.robot_controller.robot = urx.Robot(ip)
                print("✓ Robot connected!")
                success = True
            except Exception as e:
                print(f"✗ Robot connection failed: {e}")
                success = False
            if success:
                self.connected = True
                
                # Initialize thermal detector
                if ThermalDetector:
                    self.thermal_detector = ThermalDetector()
                
                # Initialize spacemouse controller
                if SpaceMouseController:
                    self.spacemouse_controller = SpaceMouseController(self.robot_controller)
                    # Try to connect spacemouse (non-blocking)
                    try:
                        self.spacemouse_controller.connect_spacemouse()
                    except Exception as e:
                        print(f"Spacemouse connection failed: {e}")
                
                return {"connected": True, "message": "Robot connected successfully"}
            else:
                return {"connected": False, "error": "Failed to connect to robot"}
                
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    def disconnect(self) -> dict:
        """Disconnect from the robot"""
        try:
            if self.robot_controller:
                # Stop thermal tracking
                self.stop_thermal_tracking()
                
                # Stop spacemouse
                if self.spacemouse_controller:
                    self.spacemouse_controller.running = False
                
                # Disconnect robot
                self.robot_controller.disconnect()
                
            self.connected = False
            self.robot_controller = None
            self.thermal_detector = None
            self.spacemouse_controller = None
            
            return {"success": True, "message": "Robot disconnected"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_to_home(self) -> dict:
        """Move robot to home position"""
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            self.robot_controller.move_to_starting_position()
            return {"success": True, "message": "Moving to home position"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_to_joint_angles(self, joint_angles_deg: list[float]) -> dict:
        """Move robot to specific joint angles (in degrees)"""
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            if len(joint_angles_deg) != 6:
                return {"success": False, "error": "Must provide exactly 6 joint angles"}
            
            # Convert degrees to radians
            import math
            joint_angles_rad = [math.radians(angle) for angle in joint_angles_deg]
            
            # Move to joint angles
            self.robot_controller.robot.movej(joint_angles_rad, acc=0.1, vel=0.1)
            
            return {
                "success": True, 
                "message": f"Moving to joint angles: {joint_angles_deg}",
                "joints_deg": joint_angles_deg,
                "joints_rad": joint_angles_rad
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_home_joints_config(self, joint_angles_deg: list[float]) -> dict:
        """Update the home joints configuration"""
        try:
            if len(joint_angles_deg) != 6:
                return {"success": False, "error": "Must provide exactly 6 joint angles"}
            
            # Validate joint angles are within reasonable bounds
            for i, angle in enumerate(joint_angles_deg):
                if not (-360 <= angle <= 360):
                    return {"success": False, "error": f"Joint {i+1} angle {angle}° is out of reasonable range (-360° to 360°)"}
            
            # Update configuration
            self.home_joints_deg = joint_angles_deg.copy()
            
            # Update config module if available
            try:
                import config
                config.HOME_DEG = joint_angles_deg.copy()
                import math
                config.START_JOINTS = [math.radians(a) for a in joint_angles_deg]
                print(f"Updated home joints config: {joint_angles_deg}")
            except ImportError:
                print("Config module not available, storing locally only")
            
            return {
                "success": True, 
                "message": "Home joints configuration updated",
                "joints": joint_angles_deg
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_manual(self, direction: str, distance: float) -> dict:
        """Manual robot movement"""
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            # Convert direction to movement
            current_pose = self.robot_controller.robot.getl()
            new_pose = current_pose.copy()
            
            if direction == 'x+':
                new_pose[0] += distance
            elif direction == 'x-':
                new_pose[0] -= distance
            elif direction == 'y+':
                new_pose[1] += distance
            elif direction == 'y-':
                new_pose[1] -= distance
            elif direction == 'z+':
                new_pose[2] += distance
            elif direction == 'z-':
                new_pose[2] -= distance
            else:
                return {"success": False, "error": "Invalid direction"}
            
            # Move robot
            self.robot_controller.robot.movel(new_pose, acc=0.1, vel=0.1)
            return {"success": True, "message": f"Moved {direction} by {distance}m"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start_thermal_tracking(self) -> dict:
        """Start thermal tracking"""
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            if not self.thermal_detector:
                return {"success": False, "error": "Thermal detector not available"}
            
            if self.thermal_tracking_active:
                return {"success": False, "error": "Thermal tracking already active"}
            
            self.thermal_tracking_active = True
            self.thermal_tracking_thread = threading.Thread(
                target=self._thermal_tracking_loop, 
                daemon=True
            )
            self.thermal_tracking_thread.start()
            
            return {"success": True, "message": "Thermal tracking started"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stop_thermal_tracking(self) -> dict:
        """Stop thermal tracking"""
        try:
            self.thermal_tracking_active = False
            if self.thermal_tracking_thread:
                self.thermal_tracking_thread.join(timeout=2)
            
            return {"success": True, "message": "Thermal tracking stopped"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _thermal_tracking_loop(self):
        """Thermal tracking main loop"""
        try:
            # This would need integration with the thermal camera feed
            # For now, we'll just set up the structure
            while self.thermal_tracking_active and self.connected:
                # In a real implementation, this would:
                # 1. Get latest thermal frame from camera stream
                # 2. Use thermal_detector.find_hottest_point(frame)
                # 3. Calculate movement needed
                # 4. Send movement commands to robot
                time.sleep(0.1)  # 10 Hz control loop
                
        except Exception as e:
            print(f"Thermal tracking error: {e}")
            self.thermal_tracking_active = False
    
    def get_status(self) -> dict:
        """Get current robot status"""
        try:
            if not self.connected or not self.robot_controller:
                return {
                    "connected": False,
                    "position": "UNKNOWN",
                    "thermal_tracking": False,
                    "spacemouse_connected": False
                }
            
            # Get current position
            try:
                pose = self.robot_controller.robot.getl()
                position = f"X:{pose[0]:.3f} Y:{pose[1]:.3f} Z:{pose[2]:.3f}"
            except:
                position = "ERROR"
            
            spacemouse_connected = (
                self.spacemouse_controller and 
                self.spacemouse_controller.spacemouse_connected
            )
            
            return {
                "connected": True,
                "position": position,
                "thermal_tracking": self.thermal_tracking_active,
                "spacemouse_connected": spacemouse_connected
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "position": "ERROR",
                "thermal_tracking": False,
                "spacemouse_connected": False
            }


# Global robot controller instance
robot_controller = UnifiedRobotController()