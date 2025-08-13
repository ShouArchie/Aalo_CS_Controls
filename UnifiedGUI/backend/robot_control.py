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

# Add UR_Cold_Spray_Code to path for robot_functions
UR_COLD_SPRAY_PATH = Path(__file__).resolve().parents[2] / 'UR_Cold_Spray_Code'
sys.path.insert(0, str(UR_COLD_SPRAY_PATH))

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

# Import robot_functions for conical spray paths
try:
    import robot_functions as rf
    print("✓ Successfully imported robot_functions")
except ImportError as e:
    print(f"✗ Failed to import robot_functions: {e}")
    rf = None


class UnifiedRobotController:
    
    def __init__(self):
        self.robot_controller = None
        self.thermal_detector = None
        self.spacemouse_controller = None
        self.robot_ip = "192.168.10.205"
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
        try:
            if RobotController is None:
                return {"connected": False, "error": "Robot controller not available"}
            
            self.robot_ip = ip
            self.robot_controller = RobotController()
            
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
                
                if ThermalDetector:
                    self.thermal_detector = ThermalDetector()
                if SpaceMouseController:
                    self.spacemouse_controller = SpaceMouseController(self.robot_controller)
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
        try:
            if self.robot_controller:
                self.stop_thermal_tracking()
                
                if self.spacemouse_controller:
                    self.spacemouse_controller.running = False
                
                self.robot_controller.disconnect()
                
            self.connected = False
            self.robot_controller = None
            self.thermal_detector = None
            self.spacemouse_controller = None
            
            return {"success": True, "message": "Robot disconnected"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_to_home(self, speed_percent: float = 100.0) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            from UR_Control_Code.config import START_JOINTS
            
            base_velocity = 0.3
            base_acceleration = 0.5
            adjusted_velocity = base_velocity * (speed_percent / 100.0)
            adjusted_acceleration = base_acceleration * (speed_percent / 100.0)
            
            print(f"🏠 Moving to home position with {speed_percent}% speed (vel={adjusted_velocity:.3f}, acc={adjusted_acceleration:.3f})")
            
            joints_str = ", ".join(f"{j:.6f}" for j in START_JOINTS)
            urscript_cmd = f"movej([{joints_str}], a={adjusted_acceleration:.6f}, v={adjusted_velocity:.6f})"
            self.robot_controller.robot.send_program(urscript_cmd)
            
            print(f"✅ URScript home command sent: {urscript_cmd}")
            return {"success": True, "message": f"Moving to home position at {speed_percent}% speed"}
        except Exception as e:
            print(f"❌ Home movement error: {e}")
            return {"success": False, "error": str(e)}
    
    def move_to_joint_angles(self, joint_angles_deg: list[float], speed_percent: float = 100.0) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            if len(joint_angles_deg) != 6:
                return {"success": False, "error": "Must provide exactly 6 joint angles"}
            
            import math
            joint_angles_rad = [math.radians(angle) for angle in joint_angles_deg]
            
            base_velocity = 0.1
            base_acceleration = 0.1
            adjusted_velocity = base_velocity * (speed_percent / 100.0)
            adjusted_acceleration = base_acceleration * (speed_percent / 100.0)
            
            print(f"🎯 Moving to joint angles with {speed_percent}% speed (vel={adjusted_velocity:.3f}, acc={adjusted_acceleration:.3f})")
            
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
        try:
            if len(joint_angles_deg) != 6:
                return {"success": False, "error": "Must provide exactly 6 joint angles"}
            
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
    
    def get_current_joint_angles(self) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            current_joints_rad = self.robot_controller.robot.getj()
            
            import math
            current_joints_deg = [math.degrees(angle) for angle in current_joints_rad]
            
            return {
                "success": True,
                "joints_deg": current_joints_deg,
                "joints_rad": current_joints_rad
            }
                
        except Exception as e:
            print(f"❌ Error getting current joint angles: {e}")
            return {"success": False, "error": str(e)}
    
    def save_current_joints_as_home(self) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            current_joints_rad = self.robot_controller.robot.getj()
            
            import math
            current_joints_deg = [math.degrees(angle) for angle in current_joints_rad]
            
            print(f"📍 Current joint angles: {[f'{angle:.1f}°' for angle in current_joints_deg]}")
            
            update_result = self.update_home_joints_config(current_joints_deg)
            
            if update_result["success"]:
                return {
                    "success": True,
                    "message": f"Current position saved as new home: {[f'{angle:.1f}°' for angle in current_joints_deg]}",
                    "joints_deg": current_joints_deg,
                    "joints_rad": current_joints_rad
                }
            else:
                return update_result
                
        except Exception as e:
            print(f"❌ Error saving current joints as home: {e}")
            return {"success": False, "error": str(e)}
    
    def move_manual(self, direction: str, distance: float, speed_percent: float = 100.0, base_speed: float = 0.1) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                print("❌ Robot not connected for movement")
                return {"success": False, "error": "Robot not connected"}
            
            speed = base_speed * (speed_percent / 100.0)
            
            print(f"🔧 Speed calculation: base_speed={base_speed}, speed_percent={speed_percent}%, final_speed={speed}")
            
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
            
            base_acceleration = 0.5  # Base acceleration
            acceleration = base_acceleration * (speed_percent / 100.0)
            urscript_cmd = f"speedl([{velocity[0]:.6f}, {velocity[1]:.6f}, {velocity[2]:.6f}, {velocity[3]:.6f}, {velocity[4]:.6f}, {velocity[5]:.6f}], {acceleration:.6f}, 0.4)"
            self.robot_controller.robot.send_program(urscript_cmd)
            
            print(f"✅ URScript speedl command sent: {urscript_cmd}")
            return {"success": True, "message": f"Moving {direction} at {speed:.3f} m/s ({speed_percent}%) in tool coordinates"}
            
        except Exception as e:
            print(f"❌ Movement error: {e}")
            return {"success": False, "error": str(e)}

    def stop_movement(self) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                print("❌ Robot not connected for stop")
                return {"success": False, "error": "Robot not connected"}
            
            urscript_cmd = "stopl(0.5)"
            
            self.robot_controller.robot.send_program(urscript_cmd)
            self.robot_controller.robot.send_program(urscript_cmd)  # Redundant immediate stop
            
            print(f"🛑 URScript stop commands sent (2x): {urscript_cmd}")
            
            return {"success": True, "message": "Robot movement stopped"}
            
        except Exception as e:
            print(f"❌ Stop movement error: {e}")
            return {"success": False, "error": str(e)}
    
    def move_fine(self, direction: str, step_size_mm: float = None, velocity: float = 0.1, acceleration: float = 0.1) -> dict:

        try:
            if not self.connected or not self.robot_controller:
                print("❌ Robot not connected for fine movement")
                return {"success": False, "error": "Robot not connected"}
            
            if step_size_mm is None:
                step_size_mm = self.fine_step_size_mm
            
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
            
            current_pose = self.robot_controller.robot.getl()
            x, y, z, rx, ry, rz = current_pose
            
            import math
            
            dx_m = dx_mm / 1000.0
            dy_m = dy_mm / 1000.0
            dz_m = dz_mm / 1000.0
            
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
            
            pose_str = ", ".join(f"{v:.6f}" for v in new_pose)
            urscript_cmd = f"movel(p[{pose_str}], a={acceleration:.6f}, v={velocity:.6f})"
            self.robot_controller.robot.send_program(urscript_cmd)
            
            print(f"✅ Fine movement URScript sent: {urscript_cmd}")
            return {"success": True, "message": f"Fine movement {direction} by {step_size_mm}mm (v={velocity:.3f}, a={acceleration:.3f})"}
            
        except Exception as e:
            print(f"❌ Fine movement error: {e}")
            return {"success": False, "error": str(e)}
    
    def set_fine_step_size(self, step_size_mm: float) -> dict:
        try:
            if step_size_mm <= 0:
                return {"success": False, "error": "Step size must be positive"}
            
            self.fine_step_size_mm = step_size_mm
            print(f"🎯 Fine step size set to {step_size_mm}mm")
            return {"success": True, "step_size_mm": step_size_mm}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_rotation(self, axis: str, angle_deg: float, angular_velocity: float = 0.1, speed_percent: float = 100.0) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                print("❌ Robot not connected for rotation")
                return {"success": False, "error": "Robot not connected"}
            
            print(f"🔄 Rotation: axis={axis}, angle={angle_deg}°, angular_velocity={angular_velocity}, speed={speed_percent}%")
            
            current_pose = self.robot_controller.robot.getl()
            x, y, z, rx, ry, rz = current_pose
            
            import math
            angle_rad = math.radians(angle_deg)
            
            adjusted_angular_velocity = angular_velocity * (speed_percent / 100.0)
            adjusted_acceleration = 0.1 * (speed_percent / 100.0)  # Base angular acceleration
            
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
            
            new_pose = [x, y, z, new_rx, new_ry, new_rz]
            
            pose_str = ", ".join(f"{v:.6f}" for v in new_pose)
            urscript_cmd = f"movel(p[{pose_str}], a={adjusted_acceleration:.6f}, v={adjusted_angular_velocity:.6f})"
            self.robot_controller.robot.send_program(urscript_cmd)
            
            print(f"✅ Rotation URScript sent: {urscript_cmd}")
            return {"success": True, "message": f"Rotating {axis} by {angle_deg}° at {speed_percent}% speed"}
            
        except Exception as e:
            print(f"❌ Rotation error: {e}")
            return {"success": False, "error": str(e)}
    

    def set_tcp_offset(self, tcp_offset: list[float], tcp_id: int, tcp_name: str) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                print("❌ Robot not connected for TCP setting")
                return {"success": False, "error": "Robot not connected"}
            
            if len(tcp_offset) != 6:
                return {"success": False, "error": "TCP offset must have exactly 6 values [X, Y, Z, Rx, Ry, Rz]"}
            
            print(f"🔧 Setting TCP {tcp_id} ({tcp_name}): [{', '.join(f'{v:.3f}' for v in tcp_offset)}]")
            
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
        try:
            self.thermal_tracking_active = False
            if self.thermal_tracking_thread:
                self.thermal_tracking_thread.join(timeout=2)
            
            return {"success": True, "message": "Thermal tracking stopped"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _thermal_tracking_loop(self):
        try:
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
    
    def execute_tool_alignment(self) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            print(f"🔧 Executing tool alignment for spray pattern")
            
            urscript = """
# Align the tool to the spray pattern
def align_tool():
    # Step 1: Translate 20mm in tool Y direction (dy_mm=20, acc=0.5, vel=0.5)
    current_pose = get_actual_tcp_pose()
    # Move 20mm in tool Y direction using pose_trans
    target_pose1 = pose_trans(current_pose, p[0, 0.025, 0, 0, 0, 0])
    movel(target_pose1, a=0.5, v=0.5)
    
    # Step 2: Rotate 13.5° around tool Y axis (ry_deg=13.5, acc=0.1, vel=0.1)
    current_pose = get_actual_tcp_pose()
    # Rotate 3.4 degrees (0.0593412 radians) around tool Y axis
    target_pose2 = pose_trans(current_pose, p[0, 0, 0, 0, -0.0593412, 0])
    movel(target_pose2, a=0.1, v=0.1)
end

align_tool()
"""
            
            self.robot_controller.robot.send_program(urscript)
            
            return {
                "success": True, 
                "message": "Tool alignment executed: 20mm Y translation + 13.5° Y rotation"
            }
        except Exception as e:
            print(f"❌ Tool alignment error: {e}")
            return {"success": False, "error": str(e)}

    def execute_cold_spray_pattern(self, acc: float = 0.1, vel: float = 0.1, blend_r: float = 0.001, iterations: int = 7) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            urscript = self._generate_cold_spray_urscript(acc, vel, blend_r, iterations)
            
            print(f"🧊 Executing blended spray pattern: acc={acc}, vel={vel}, blend_r={blend_r}, iterations={iterations}")
            print(f"📜 URScript length: {len(urscript)} characters")
            
            spray_thread = threading.Thread(
                target=self._execute_cold_spray_background,
                args=(urscript, acc, vel, blend_r, iterations),
                daemon=True
            )
            spray_thread.start()
            
            return {
                "success": True, 
                "message": f"Started blended spray pattern with {iterations} iterations in background - camera will continue streaming",
                "parameters": {
                    "acceleration": acc,
                    "velocity": vel,
                    "blend_radius": blend_r,
                    "iterations": iterations
                }
            }
        except Exception as e:
            print(f"❌ Blended spray pattern error: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_cold_spray_background(self, urscript: str, acc: float, vel: float, blend_r: float, iterations: int):
        try:
            print(f"🧊 Executing blended spray pattern in background thread")

            self.robot_controller.robot.send_program(urscript)
            
            print(f"🎯 Cold spray pattern with {iterations} iterations completed successfully!")
            
        except Exception as e:
            print(f"❌ Background cold spray error: {e}")
    
    def _generate_cold_spray_urscript(self, acc: float, vel: float, blend_r: float, iterations: int) -> str:
        dz_step = 0.050  # 50mm stepping along tool Z-axis (Z+ is up, Z- is down in tool frame)
        rz_step = 0.0237  # ≈1.36 degrees per incremental rotation around tool Z-axis (blue arrow)
        cycles = 5  # forward & reverse passes
        
        return f"""
def blended_spray():
    # Blended spray pattern with forward/reverse cycles
    # Parameters: acc={acc}, vel={vel}, blend_r={blend_r}, iterations={iterations}
    # Pattern: DZ_STEP={dz_step}m, RZ_STEP={rz_step}rad, CYCLES={cycles}
    # Moving along tool Z-axis (blue arrow): Z+ is up, Z- is down
    # Rotating around tool Z-axis (blue arrow)
    
    j = 0
    while j < {iterations}:
        # Forward cycles - stepping down along tool Z-axis (Z-)
        i = 0
        while i < {cycles}:
            movel(pose_trans(get_actual_tcp_pose(), p[0, 0, -{dz_step}, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})
            movel(pose_trans(get_actual_tcp_pose(), p[0, 0, 0, 0, 0, {rz_step}]), a={acc}, v={vel}, r={blend_r})
            movel(pose_trans(get_actual_tcp_pose(), p[0, 0, {dz_step}, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})
            if i < {cycles - 1}:
                movel(pose_trans(get_actual_tcp_pose(), p[0, 0, 0, 0, 0, {rz_step}]), a={acc}, v={vel}, r={blend_r})
            end
            i = i + 1
        end

        # Reverse cycles - stepping up along tool Z-axis (Z+)
        i = 0
        while i < {cycles}:
            if i > 0:
                movel(pose_trans(get_actual_tcp_pose(), p[0, 0, 0, 0, 0, -{rz_step}]), a={acc}, v={vel}, r={blend_r})
            end
            movel(pose_trans(get_actual_tcp_pose(), p[0, 0, -{dz_step}, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})
            movel(pose_trans(get_actual_tcp_pose(), p[0, 0, 0, 0, 0, -{rz_step}]), a={acc}, v={vel}, r={blend_r})

            movel(pose_trans(get_actual_tcp_pose(), p[0, 0, {dz_step}, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})

            i = i + 1
        end
        j = j + 1
    end
end

blended_spray()
"""

    def execute_conical_spray_paths(self, spray_paths: list) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            if rf is None:
                return {"success": False, "error": "robot_functions module not available"}
            
            spray_thread = threading.Thread(
                target=self._execute_conical_spray_background,
                args=(spray_paths,),
                daemon=True
            )
            spray_thread.start()
            
            return {
                "success": True,
                "message": f"Started {len(spray_paths)} conical spray path(s) in background - camera will continue streaming",
                "paths_to_execute": len(spray_paths)
            }
            
        except Exception as e:
            print(f"❌ Conical spray paths error: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_conical_spray_background(self, spray_paths: list):
        try:
            print(f"🌀 Executing {len(spray_paths)} conical spray path(s) in background thread")
            tilt = 0
            for i, path in enumerate(spray_paths, 1):
                tilt_deg = path['tilt']
                tilt = tilt_deg
                revolutions = path['rev'] 
                cycle_s = path['cycle']
                steps = int(180 * revolutions)  # Always 180 steps per revolution
                
                print(f"   ↳ Sweep {i}: tilt={tilt_deg}°, rev={revolutions}, cycle={cycle_s}, steps={steps}")
                
                rf.conical_motion_servoj_script(
                    self.robot_controller.robot,
                    tilt_deg=tilt_deg,
                    revolutions=revolutions,
                    steps=steps,
                    cycle_s=cycle_s,
                    lookahead_time=0.1,
                    gain=2800,  
                    sing_tol_deg=0.5,
                    approach_time_s=path.get('approach_time', 0.5) if i == 0 else None
                )
                
                time.sleep(1.5)
                rf.wait_until_idle(self.robot_controller.robot)
                
                print(f"   ✓ Sweep {i} completed")
            
            rf.rotate_tcp(self.robot_controller.robot, ry_deg=-tilt, acc=1.5, vel=1)
            print(f"🎯 All {len(spray_paths)} conical spray paths completed successfully!")
            
        except Exception as e:
            print(f"❌ Background conical spray error: {e}")

    def execute_spiral_spray(self, spiral_params: dict) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            if rf is None:
                return {"success": False, "error": "robot_functions module not available"}
            
            spiral_thread = threading.Thread(
                target=self._execute_spiral_spray_background,
                args=(spiral_params,),
                daemon=True
            )
            spiral_thread.start()
            
            return {
                "success": True,
                "message": f"Started spiral spray pattern in background - camera will continue streaming",
                "params": spiral_params
            }
            
        except Exception as e:
            print(f"❌ Spiral spray error: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_spiral_spray_background(self, spiral_params: dict):
        try:
            print(f"🌀 Executing spiral spray pattern in background thread")
            print(f"   ↳ Tilt: {spiral_params['tilt_start_deg']}° → {spiral_params['tilt_end_deg']}°")
            print(f"   ↳ Revolutions: {spiral_params['revs']}")
            print(f"   ↳ Radius: {spiral_params['r_start_mm']}mm → {spiral_params['r_end_mm']}mm")
            print(f"   ↳ Cycle time: {spiral_params['cycle_s']}s")
            
            rf.spiral_cold_spray(
                self.robot_controller.robot,
                tilt_start_deg=spiral_params['tilt_start_deg'],
                tilt_end_deg=spiral_params['tilt_end_deg'],
                revs=spiral_params['revs'],
                r_start_mm=spiral_params['r_start_mm'],
                r_end_mm=spiral_params['r_end_mm'],
                steps_per_rev=spiral_params['steps_per_rev'],
                cycle_s=spiral_params['cycle_s'],
                lookahead_s=spiral_params['lookahead_s'],
                gain=spiral_params['gain'],
                sing_tol_deg=spiral_params['sing_tol_deg'],
                phase_offset_deg=spiral_params.get('phase_offset_deg', 0.0),
                cycle_s_start=spiral_params.get('cycle_s_start'),
                cycle_s_end=spiral_params.get('cycle_s_end'),
                invert_tilt=spiral_params.get('invert_tilt', False),
                approach_time_s=spiral_params.get('approach_time_s', 0.5),
                delta_x_mm=spiral_params.get('delta_x_mm', 0.0)
            )
            
            time.sleep(1.5)
            rf.wait_until_idle(self.robot_controller.robot)
            
            print(f"🎯 Spiral spray pattern completed successfully!")
            
        except Exception as e:
            print(f"❌ Background spiral spray error: {e}")

    def execute_custom_pattern(self, pattern_params: dict) -> dict:
        try:
            if not self.robot_controller or not self.robot_controller.robot:
                return {"success": False, "error": "Robot not connected"}

            print(f"🔧 Starting custom movement pattern...")
            
            # Execute in background thread
            thread = threading.Thread(target=self._execute_custom_pattern_background, args=(pattern_params,))
            thread.daemon = True
            thread.start()
            
            return {"success": True, "message": "Custom pattern execution started"}
            
        except Exception as e:
            print(f"❌ Custom pattern execution error: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_custom_pattern_background(self, pattern_params: dict):
        try:
            print(f"🔧 Executing custom movement pattern in background thread")
            print(f"   ↳ Initial cycles: {pattern_params['initial_cycles']}")
            print(f"   ↳ Tilt angle: {pattern_params['tilt_angle_deg']}°")
            print(f"   ↳ Initial vel/acc: {pattern_params['initial_velocity']}/{pattern_params['initial_acceleration']}")
            print(f"   ↳ Tilted vel/acc: {pattern_params['tilted_velocity']}/{pattern_params['tilted_acceleration']}")
            print(f"   ↳ Tilted cycles: {pattern_params['tilted_cycles']}")
            
            rf.custom_movement_pattern(
                self.robot_controller.robot,
                initial_cycles=pattern_params['initial_cycles'],
                tilt_angle_deg=pattern_params['tilt_angle_deg'],
                initial_velocity=pattern_params['initial_velocity'],
                initial_acceleration=pattern_params['initial_acceleration'],
                tilted_velocity=pattern_params['tilted_velocity'],
                tilted_acceleration=pattern_params['tilted_acceleration'],
                tilted_cycles=pattern_params['tilted_cycles']
            )
            
            time.sleep(1.5)
            rf.wait_until_idle(self.robot_controller.robot)
            
            print(f"🎯 Custom movement pattern completed successfully!")
            
        except Exception as e:
            print(f"❌ Background custom pattern error: {e}")

    def get_status(self) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                return {
                    "connected": False,
                    "position": "UNKNOWN",
                    "thermal_tracking": False,
                    "spacemouse_connected": False
                }
            
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
    
    def get_tcp_position(self) -> dict:
        try:
            if not self.connected or not self.robot_controller:
                return {"success": False, "error": "Robot not connected"}
            
            tcp_pose = self.robot_controller.robot.getl()
            x, y, z, rx, ry, rz = tcp_pose
            
            position_mm = [x * 1000, y * 1000, z * 1000]
            
            import math
            rotation_deg = [math.degrees(rx), math.degrees(ry), math.degrees(rz)]
            
            return {
                "success": True,
                "position_mm": position_mm,  
                "rotation_deg": rotation_deg,  
                "raw_pose": tcp_pose  
            }
            
        except Exception as e:
            print(f"❌ TCP position error: {e}")
            return {"success": False, "error": str(e)}


# Global robot controller instance
robot_controller = UnifiedRobotController()