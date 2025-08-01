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
        
        # Fine movement configuration
        self.fine_step_size_mm = 1.0  # Default 1mm steps
        
        # TCP configuration
        self.current_tcp = [0, 0, 0, 0, 0, 0]  # Default no TCP offset
        self.current_tcp_id = 4  # Default to "No TCP (Base)"
        self.current_tcp_name = "No TCP (Base)"
        
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
    
    def move_to_home(self, speed_percent: float = 100.0) -> dict:
        """Move robot to home position"""
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            # Use custom speed-controlled movement instead of original method
            # Get starting position from config
            from UR_Control_Code.config import START_JOINTS
            
            # Apply speed multiplier to default velocity and acceleration
            base_velocity = 0.3
            base_acceleration = 0.5
            adjusted_velocity = base_velocity * (speed_percent / 100.0)
            adjusted_acceleration = base_acceleration * (speed_percent / 100.0)
            
            print(f"🏠 Moving to home position with {speed_percent}% speed (vel={adjusted_velocity:.3f}, acc={adjusted_acceleration:.3f})")
            
            # Use URScript movej command with custom speed
            joints_str = ", ".join(f"{j:.6f}" for j in START_JOINTS)
            urscript_cmd = f"movej([{joints_str}], a={adjusted_acceleration:.6f}, v={adjusted_velocity:.6f})"
            self.robot_controller.robot.send_program(urscript_cmd)
            
            print(f"✅ URScript home command sent: {urscript_cmd}")
            return {"success": True, "message": f"Moving to home position at {speed_percent}% speed"}
        except Exception as e:
            print(f"❌ Home movement error: {e}")
            return {"success": False, "error": str(e)}
    
    def move_to_joint_angles(self, joint_angles_deg: list[float], speed_percent: float = 100.0) -> dict:
        """Move robot to specific joint angles (in degrees)"""
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            if len(joint_angles_deg) != 6:
                return {"success": False, "error": "Must provide exactly 6 joint angles"}
            
            # Convert degrees to radians
            import math
            joint_angles_rad = [math.radians(angle) for angle in joint_angles_deg]
            
            # Apply speed multiplier to default velocity and acceleration
            base_velocity = 0.1
            base_acceleration = 0.1
            adjusted_velocity = base_velocity * (speed_percent / 100.0)
            adjusted_acceleration = base_acceleration * (speed_percent / 100.0)
            
            print(f"🎯 Moving to joint angles with {speed_percent}% speed (vel={adjusted_velocity:.3f}, acc={adjusted_acceleration:.3f})")
            
            # Use URScript movej command with custom speed
            joints_str = ", ".join(f"{j:.6f}" for j in joint_angles_rad)
            urscript_cmd = f"movej([{joints_str}], a={adjusted_acceleration:.6f}, v={adjusted_velocity:.6f})"
            self.robot_controller.robot.send_program(urscript_cmd)
            
            print(f"✅ URScript joint movement command sent: {urscript_cmd}")
            return {
                "success": True, 
                "message": f"Moving to joint angles at {speed_percent}% speed: {joint_angles_deg}",
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
    
    def move_manual(self, direction: str, distance: float, speed_percent: float = 100.0, base_speed: float = 0.1) -> dict:
        """Manual robot movement using speedl in tool coordinate system"""
        try:
            if not self.connected or not self.robot_controller:
                print("❌ Robot not connected for movement")
                return {"success": False, "error": "Robot not connected"}
            
            # Use configurable base speed and apply global speed multiplier
            speed = base_speed * (speed_percent / 100.0)
            
            print(f"🔧 Speed calculation: base_speed={base_speed}, speed_percent={speed_percent}%, final_speed={speed}")
            
            # Define velocity vector in tool coordinates [x, y, z, rx, ry, rz]
            if direction == 'x+':
                velocity = [speed, 0, 0, 0, 0, 0]
            elif direction == 'x-':
                velocity = [-speed, 0, 0, 0, 0, 0]
            elif direction == 'y+':
                velocity = [0, speed, 0, 0, 0, 0]
            elif direction == 'y-':
                velocity = [0, -speed, 0, 0, 0, 0]
            elif direction == 'z+':
                velocity = [0, 0, speed, 0, 0, 0]
            elif direction == 'z-':
                velocity = [0, 0, -speed, 0, 0, 0]
            else:
                return {"success": False, "error": "Invalid direction"}
            
            print(f"🤖 Moving robot {direction} with velocity: {velocity} (speed: {speed_percent}%)")
            
            # Use URScript speedl command like spacemouse controller
            # speedl([x, y, z, rx, ry, rz], acceleration, time)
            # Apply speed multiplier to acceleration as well
            base_acceleration = 0.5  # Base acceleration
            acceleration = base_acceleration * (speed_percent / 100.0)
            urscript_cmd = f"speedl([{velocity[0]:.6f}, {velocity[1]:.6f}, {velocity[2]:.6f}, {velocity[3]:.6f}, {velocity[4]:.6f}, {velocity[5]:.6f}], {acceleration:.6f}, 1.0)"
            self.robot_controller.robot.send_program(urscript_cmd)
            
            print(f"✅ URScript speedl command sent: {urscript_cmd}")
            return {"success": True, "message": f"Moving {direction} at {speed:.3f} m/s ({speed_percent}%) in tool coordinates"}
            
        except Exception as e:
            print(f"❌ Movement error: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_movement(self) -> dict:
        """Stop all robot movement using URScript"""
        try:
            if not self.connected or not self.robot_controller:
                print("❌ Robot not connected for stop")
                return {"success": False, "error": "Robot not connected"}
            
            # Stop linear movement using URScript like spacemouse controller
            # Use immediate stop with very fast deceleration + redundant commands
            urscript_cmd = "stopl(0.5)"
            
            # Send multiple stop commands for immediate response
            self.robot_controller.robot.send_program(urscript_cmd)
            self.robot_controller.robot.send_program(urscript_cmd)  # Redundant immediate stop
            
            print(f"🛑 URScript stop commands sent (2x): {urscript_cmd}")
            
            return {"success": True, "message": "Robot movement stopped"}
            
        except Exception as e:
            print(f"❌ Stop movement error: {e}")
            return {"success": False, "error": str(e)}
    
    def move_fine(self, direction: str, step_size_mm: float = None, velocity: float = 0.1, acceleration: float = 0.1) -> dict:
        """Fine movement using translate_tcp method like Cold Spray Code"""
        try:
            if not self.connected or not self.robot_controller:
                print("❌ Robot not connected for fine movement")
                return {"success": False, "error": "Robot not connected"}
            
            # Use provided step size or default
            if step_size_mm is None:
                step_size_mm = self.fine_step_size_mm
            
            # Define movement vectors in TCP coordinates (mm)
            dx_mm = dy_mm = dz_mm = 0.0
            
            if direction == 'x+':
                dx_mm = step_size_mm
            elif direction == 'x-':
                dx_mm = -step_size_mm
            elif direction == 'y+':
                dy_mm = step_size_mm
            elif direction == 'y-':
                dy_mm = -step_size_mm
            elif direction == 'z+':
                dz_mm = step_size_mm
            elif direction == 'z-':
                dz_mm = -step_size_mm
            else:
                return {"success": False, "error": "Invalid direction"}
            
            print(f"🎯 Fine movement {direction}: dx={dx_mm}mm, dy={dy_mm}mm, dz={dz_mm}mm")
            
            # Get current TCP pose
            current_pose = self.robot_controller.robot.getl()
            x, y, z, rx, ry, rz = current_pose
            
            # Convert axis-angle to rotation matrix (simplified version)
            import math
            
            # Convert mm to meters for calculations
            dx_m = dx_mm / 1000.0
            dy_m = dy_mm / 1000.0
            dz_m = dz_mm / 1000.0
            
            # Create rotation matrix from axis-angle representation
            angle = math.sqrt(rx**2 + ry**2 + rz**2)
            if angle > 0:
                ux, uy, uz = rx/angle, ry/angle, rz/angle
                c = math.cos(angle)
                s = math.sin(angle)
                
                # Rodrigues' rotation formula
                R = [
                    [c + ux**2*(1-c), ux*uy*(1-c) - uz*s, ux*uz*(1-c) + uy*s],
                    [uy*ux*(1-c) + uz*s, c + uy**2*(1-c), uy*uz*(1-c) - ux*s],
                    [uz*ux*(1-c) - uy*s, uz*uy*(1-c) + ux*s, c + uz**2*(1-c)]
                ]
            else:
                # Identity matrix for zero rotation
                R = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
            
            # Transform tool coordinates to base coordinates
            d_tool = [dx_m, dy_m, dz_m]
            d_base = [
                sum(R[i][j] * d_tool[j] for j in range(3)) for i in range(3)
            ]
            
            # Calculate new pose
            new_pose = [
                x + d_base[0],
                y + d_base[1], 
                z + d_base[2],
                rx, ry, rz  # Keep same orientation
            ]
            
            # Send URScript movel command with custom velocity and acceleration
            pose_str = ", ".join(f"{v:.6f}" for v in new_pose)
            urscript_cmd = f"movel(p[{pose_str}], a={acceleration:.6f}, v={velocity:.6f})"
            self.robot_controller.robot.send_program(urscript_cmd)
            
            print(f"✅ Fine movement URScript sent: {urscript_cmd}")
            return {"success": True, "message": f"Fine movement {direction} by {step_size_mm}mm (v={velocity:.3f}, a={acceleration:.3f})"}
            
        except Exception as e:
            print(f"❌ Fine movement error: {e}")
            return {"success": False, "error": str(e)}
    
    def set_fine_step_size(self, step_size_mm: float) -> dict:
        """Set the fine movement step size"""
        try:
            if step_size_mm <= 0:
                return {"success": False, "error": "Step size must be positive"}
            
            self.fine_step_size_mm = step_size_mm
            print(f"🎯 Fine step size set to {step_size_mm}mm")
            return {"success": True, "step_size_mm": step_size_mm}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_rotation(self, axis: str, angle_deg: float, angular_velocity: float = 0.1, speed_percent: float = 100.0) -> dict:
        """Fine rotation movement in TCP coordinates (Rx, Ry, Rz)"""
        try:
            if not self.connected or not self.robot_controller:
                print("❌ Robot not connected for rotation")
                return {"success": False, "error": "Robot not connected"}
            
            print(f"🔄 Rotation: axis={axis}, angle={angle_deg}°, angular_velocity={angular_velocity}, speed={speed_percent}%")
            
            # Get current TCP pose
            current_pose = self.robot_controller.robot.getl()
            x, y, z, rx, ry, rz = current_pose
            
            # Convert angle to radians
            import math
            angle_rad = math.radians(angle_deg)
            
            # Apply global speed multiplier
            adjusted_angular_velocity = angular_velocity * (speed_percent / 100.0)
            adjusted_acceleration = 0.1 * (speed_percent / 100.0)  # Base angular acceleration
            
            # Calculate new orientation based on axis
            new_rx, new_ry, new_rz = rx, ry, rz
            
            if axis == 'rx+':
                new_rx += angle_rad
            elif axis == 'rx-':
                new_rx -= angle_rad
            elif axis == 'ry+':
                new_ry += angle_rad
            elif axis == 'ry-':
                new_ry -= angle_rad
            elif axis == 'rz+':
                new_rz += angle_rad
            elif axis == 'rz-':
                new_rz -= angle_rad
            else:
                return {"success": False, "error": "Invalid rotation axis"}
            
            # Create new pose with updated rotation
            new_pose = [x, y, z, new_rx, new_ry, new_rz]
            
            # Send URScript movel command for precise rotation
            pose_str = ", ".join(f"{v:.6f}" for v in new_pose)
            urscript_cmd = f"movel(p[{pose_str}], a={adjusted_acceleration:.6f}, v={adjusted_angular_velocity:.6f})"
            self.robot_controller.robot.send_program(urscript_cmd)
            
            print(f"✅ Rotation URScript sent: {urscript_cmd}")
            return {"success": True, "message": f"Rotating {axis} by {angle_deg}° at {speed_percent}% speed"}
            
        except Exception as e:
            print(f"❌ Rotation error: {e}")
            return {"success": False, "error": str(e)}
    
    def set_tcp_offset(self, tcp_offset: list[float], tcp_id: int, tcp_name: str) -> dict:
        """Set the TCP (Tool Center Point) offset for the robot"""
        try:
            if not self.connected or not self.robot_controller:
                print("❌ Robot not connected for TCP setting")
                return {"success": False, "error": "Robot not connected"}
            
            if len(tcp_offset) != 6:
                return {"success": False, "error": "TCP offset must have exactly 6 values [X, Y, Z, Rx, Ry, Rz]"}
            
            print(f"🔧 Setting TCP {tcp_id} ({tcp_name}): [{', '.join(f'{v:.3f}' for v in tcp_offset)}]")
            
            # Send URScript set_tcp command
            # TCP offset format: [x_mm, y_mm, z_mm, rx_rad, ry_rad, rz_rad]
            # Convert position from mm to m for URScript
            tcp_m = [
                tcp_offset[0] / 1000.0,  # X mm to m
                tcp_offset[1] / 1000.0,  # Y mm to m  
                tcp_offset[2] / 1000.0,  # Z mm to m
                tcp_offset[3],           # Rx already in radians
                tcp_offset[4],           # Ry already in radians
                tcp_offset[5]            # Rz already in radians
            ]
            
            tcp_str = ", ".join(f"{v:.6f}" for v in tcp_m)
            urscript_cmd = f"set_tcp(p[{tcp_str}])"
            
            print(f"📤 Sending URScript command: {urscript_cmd}")
            self.robot_controller.robot.send_program(urscript_cmd)
            print(f"📨 URScript command sent successfully")
            
            # Store current TCP for reference
            self.current_tcp = tcp_offset.copy()
            self.current_tcp_id = tcp_id
            self.current_tcp_name = tcp_name
            
            print(f"✅ TCP set successfully: {urscript_cmd}")
            return {
                "success": True, 
                "message": f"TCP {tcp_id} ({tcp_name}) set successfully",
                "tcp_offset": tcp_offset,
                "tcp_id": tcp_id,
                "tcp_name": tcp_name
            }
            
        except Exception as e:
            print(f"❌ TCP setting error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_current_tcp(self) -> dict:
        """Get the currently active TCP offset"""
        try:
            return {
                "success": True,
                "tcp_offset": self.current_tcp,
                "tcp_id": self.current_tcp_id,
                "tcp_name": self.current_tcp_name
            }
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