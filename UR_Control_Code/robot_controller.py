"""
Robot Controller for Face and Thermal Tracking System
Handles robot connection, movement commands, and PID control
"""

import urx
import time
import math
import threading
import keyboard
from config import *


class RobotController:
    """Handles robot connection and movement control"""
    
    def __init__(self):
        self.robot = None
        self.running = False
        self.control_running = False
        self.control_thread = None
        self.arrow_key_thread = None
        
        # PID state variables
        self.error_integral_y = 0.0
        self.error_integral_z = 0.0
        self.previous_error_y = 0.0
        self.previous_error_z = 0.0
        
        # Target positions
        self.last_face_position = None
        self.last_thermal_position = None
        
        # Tracking states
        self.face_tracking_active = False
        self.thermal_tracking_active = False
    
    def connect(self):
        """Connect to robot."""
        try:
            print(f"Connecting to robot at {ROBOT_IP}...")
            self.robot = urx.Robot(ROBOT_IP)
            print("✓ Robot connected!")
            return True
        except Exception as e:
            print(f"✗ Robot connection failed: {e}")
            return False
    
    def move_to_starting_position(self):
        """Move robot to starting position and wait for completion."""
        print("Moving to starting position...")
        print(f"Target joint angles (degrees): {[math.degrees(j) for j in START_JOINTS]}")
        
        try:
            self.robot.movej(START_JOINTS, acc=0.5, vel=0.3)
            print("Move command sent successfully")
        except Exception as e:
            if "Robot stopped" in str(e):
                print("Move command completed (URX 'Robot stopped' message is normal)")
            else:
                print(f"Move command warning: {e}")
        
        print("Waiting for robot to reach starting position...")
        
        # Wait and verify position is reached
        max_wait_time = 15
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                current_joints = self.robot.getj()
                if current_joints and len(current_joints) >= 6:
                    position_errors = []
                    for i in range(len(START_JOINTS)):
                        error = abs(current_joints[i] - START_JOINTS[i])
                        if error > math.pi:
                            error = 2 * math.pi - error
                        position_errors.append(error)
                    
                    max_error = max(position_errors)
                    max_error_deg = math.degrees(max_error)
                    
                    if max_error_deg < 3.0:
                        print(f"\n✓ Starting position reached! Max error: {max_error_deg:.1f}°")
                        return True
                    
                    print(f"Moving... Max error: {max_error_deg:.1f}°", end='\r')
                    
            except Exception as e:
                print(f"\nError checking position: {e}")
            
            time.sleep(0.2)
        
        print(f"\n✗ Timeout waiting for starting position after {max_wait_time} seconds")
        return False
    
    def calculate_pid_speeds(self, target_x, target_y, is_thermal=False, center_x=None, center_y=None):
        """Calculate Y and Z speeds using PID control."""
        # Use provided center coordinates or default
        if center_x is None:
            center_x = FRAME_WIDTH // 2
        if center_y is None:
            center_y = FRAME_HEIGHT // 2
        
        # Calculate errors (offset from center)
        error_x = target_x - center_x  # For Y movement (left/right)
        error_y = target_y - center_y  # For Z movement (up/down)
        
        # Check deadzone
        distance_from_center = math.sqrt(error_x**2 + error_y**2)
        if distance_from_center <= DEADZONE_RADIUS:
            # Reset PID state when in deadzone
            self.error_integral_y = 0.0
            self.error_integral_z = 0.0
            self.previous_error_y = 0.0
            self.previous_error_z = 0.0
            return 0.0, 0.0
        
        # Calculate adaptive gain multiplier based on distance from center
        max_distance = math.sqrt((FRAME_WIDTH//2)**2 + (FRAME_HEIGHT//2)**2)
        normalized_distance = min(distance_from_center / max_distance, 1.0)
        gain_multiplier = 1.0 + (normalized_distance ** 2) * 1.0
        
        # Select PID gains based on tracking mode
        if is_thermal:
            base_kp_y, base_ki_y, base_kd_y = THERMAL_PID_KP_Y, THERMAL_PID_KI_Y, THERMAL_PID_KD_Y
            base_kp_z, base_ki_z, base_kd_z = THERMAL_PID_KP_Z, THERMAL_PID_KI_Z, THERMAL_PID_KD_Z
        else:
            base_kp_y, base_ki_y, base_kd_y = FACE_PID_KP_Y, FACE_PID_KI_Y, FACE_PID_KD_Y
            base_kp_z, base_ki_z, base_kd_z = FACE_PID_KP_Z, FACE_PID_KI_Z, FACE_PID_KD_Z
        
        # Apply adaptive gains
        kp_y_adaptive = base_kp_y * gain_multiplier
        ki_y_adaptive = base_ki_y * gain_multiplier
        kd_y_adaptive = base_kd_y * gain_multiplier
        kp_z_adaptive = base_kp_z * gain_multiplier
        ki_z_adaptive = base_ki_z * gain_multiplier
        kd_z_adaptive = base_kd_z * gain_multiplier
        
        # PID calculation for Y (left/right movement)
        self.error_integral_y += error_x
        error_derivative_y = error_x - self.previous_error_y
        
        # Integral windup protection
        max_integral = 100
        self.error_integral_y = max(-max_integral, min(max_integral, self.error_integral_y))
        
        dy = (kp_y_adaptive * error_x + 
              ki_y_adaptive * self.error_integral_y + 
              kd_y_adaptive * error_derivative_y)
        
        # PID calculation for Z (up/down movement) - FLIPPED
        self.error_integral_z += error_y
        error_derivative_z = error_y - self.previous_error_z
        self.error_integral_z = max(-max_integral, min(max_integral, self.error_integral_z))
        
        dz = -(kp_z_adaptive * error_y +
               ki_z_adaptive * self.error_integral_z + 
               kd_z_adaptive * error_derivative_z)
        
        # Apply speed limits based on tracking mode
        if is_thermal:
            max_speed_y, max_speed_z = MAX_SPEED_Y_THERMAL, MAX_SPEED_Z_THERMAL
        else:
            max_speed_y, max_speed_z = MAX_SPEED_Y_FACE, MAX_SPEED_Z_FACE
        
        dy_limited = max(-max_speed_y, min(max_speed_y, dy))
        dz_limited = max(-max_speed_z, min(max_speed_z, dz))
        
        # Update previous errors
        self.previous_error_y = error_x
        self.previous_error_z = error_y
        
        return dy_limited, dz_limited
    
    def send_speed_command(self, dy, dz):
        """Send speedL command with appropriate parameters based on tracking mode."""
        try:
            if abs(dy) < 0.001 and abs(dz) < 0.001:
                self.robot.send_program("stopl(0.2)")
                return
            
            # Set parameters based on tracking mode
            if self.thermal_tracking_active:
                acceleration = THERMAL_ACCELERATION
                time_param = THERMAL_TIME_PARAM
            else:
                acceleration = FACE_ACCELERATION
                time_param = FACE_TIME_PARAM
                
            # Send speedL command
            urscript_cmd = f"speedl([0.0, {dy:.6f}, {dz:.6f}, 0, 0, 0], {acceleration}, {time_param})"
            self.robot.send_program(urscript_cmd)
            
        except Exception as e: 
            print(f"Error sending speed command: {e}")
    
    def emergency_stop(self):
        """Emergency stop - turn off all tracking and stop robot."""
        print("EMERGENCY STOP ACTIVATED!")
        self.face_tracking_active = False
        self.thermal_tracking_active = False
        
        # Reset PID state
        self.error_integral_y = 0.0
        self.error_integral_z = 0.0
        self.previous_error_y = 0.0
        self.previous_error_z = 0.0
        
        # Send emergency stop command
        self.robot.send_program("stopl(0.1)")
        print("All tracking stopped - Robot emergency stopped")
    
    def return_to_starting_position(self):
        """Return robot to starting position during runtime."""
        print("Returning to starting position...")
        
        # Turn off all tracking first
        was_face_active = self.face_tracking_active
        was_thermal_active = self.thermal_tracking_active
        
        self.face_tracking_active = False
        self.thermal_tracking_active = False
        self._reset_pid_state()
        
        try:
            # Stop current movement
            self.robot.send_program("stopl(0.5)")
            time.sleep(0.5)
            
            # Move to starting position
            print(f"Moving to starting position: {[math.degrees(j) for j in START_JOINTS]} degrees")
            self.robot.movej(START_JOINTS, acc=0.5, vel=0.3)
            print("✓ Returned to starting position!")
            
            # Restore previous tracking states if they were active
            if was_face_active:
                print("Reactivating face tracking...")
                self.face_tracking_active = True
            elif was_thermal_active:
                print("Reactivating thermal tracking...")
                self.thermal_tracking_active = True
            
            return True
            
        except Exception as e:
            print(f"Error returning to starting position: {e}")
            return False
    
    def set_face_tracking(self, active):
        """Set face tracking state."""
        if active and self.thermal_tracking_active:
            self.thermal_tracking_active = False
            print("Thermal tracking turned OFF")
        
        self.face_tracking_active = active
        self._reset_pid_state()
        
        if not active:
            self.robot.send_program("stopl(0.5)")
    
    def set_thermal_tracking(self, active):
        """Set thermal tracking state."""
        if active and self.face_tracking_active:
            self.face_tracking_active = False
            print("Face tracking turned OFF")
        
        self.thermal_tracking_active = active
        self._reset_pid_state()
        
        if not active:
            self.robot.send_program("stopl(0.5)")
    
    def _reset_pid_state(self):
        """Reset PID controller state."""
        self.error_integral_y = 0.0
        self.error_integral_z = 0.0
        self.previous_error_y = 0.0
        self.previous_error_z = 0.0
    
    def start_control_threads(self):
        """Start control and arrow key threads."""
        self.running = True
        self.control_running = True
        
        # Start control loop thread
        self.control_thread = threading.Thread(target=self._control_loop)
        self.control_thread.daemon = True
        self.control_thread.start()
        
        # Start arrow key handler thread
        self.arrow_key_thread = threading.Thread(target=self._handle_arrow_keys)
        self.arrow_key_thread.daemon = True
        self.arrow_key_thread.start()
    
    def _control_loop(self):
        """Main control loop for tracking."""
        try:
            while self.control_running and self.running:
                try:
                    if self.face_tracking_active or self.thermal_tracking_active:
                        target_position = None
                        is_thermal = False
                        thermal_center_x = thermal_center_y = None
                        
                        if self.face_tracking_active and self.last_face_position:
                            target_position = self.last_face_position
                            is_thermal = False
                        elif self.thermal_tracking_active and self.last_thermal_position:
                            target_position = self.last_thermal_position
                            is_thermal = True
                            thermal_center_x = getattr(self, 'thermal_center_x', FRAME_WIDTH // 2)
                            thermal_center_y = getattr(self, 'thermal_center_y', FRAME_HEIGHT // 2)
                        
                        if target_position:
                            target_x, target_y = target_position
                            dy, dz = self.calculate_pid_speeds(target_x, target_y, is_thermal, 
                                                             thermal_center_x, thermal_center_y)
                            self.send_speed_command(dy, dz)
                        else:
                            self.robot.send_program("stopl(0.2)")
                        
                        time.sleep(1.0 / CONTROL_LOOP_FREQUENCY)
                    else:
                        time.sleep(0.5)
                        
                except Exception as inner_e:
                    print(f"Control loop error: {inner_e}")
                    time.sleep(0.1)
                    
        except Exception as outer_e:
            print(f"Control loop error: {outer_e}")
    
    def _handle_arrow_keys(self):
        """Handle arrow key presses for X-axis movement."""
        while self.running:
            try:
                if not self.face_tracking_active and not self.thermal_tracking_active:
                    if keyboard.is_pressed('up'):
                        try:
                            print(f"UP: Moving forward {X_MOVE_STEP*1000:.0f}mm in tool X")
                            urscript_cmd = f"movel(pose_trans(get_actual_tcp_pose(), p[{X_MOVE_STEP:.6f}, 0, 0, 0, 0, 0]), a=0.5, v=0.2)"
                            self.robot.send_program(urscript_cmd)
                        except Exception as move_e:
                            print(f"UP movement error: {move_e}")
                        time.sleep(1.0)
                    elif keyboard.is_pressed('down'):
                        try:
                            print(f"DOWN: Moving backward {X_MOVE_STEP*1000:.0f}mm in tool X")
                            urscript_cmd = f"movel(pose_trans(get_actual_tcp_pose(), p[-{X_MOVE_STEP:.6f}, 0, 0, 0, 0, 0]), a=0.5, v=0.2)"
                            self.robot.send_program(urscript_cmd)
                        except Exception as move_e:
                            print(f"DOWN movement error: {move_e}")
                        time.sleep(1.0)
                    else:
                        time.sleep(0.05)
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Arrow key error: {e}")
                time.sleep(0.1)
    
    def cleanup(self):
        """Clean up robot resources."""
        print("Cleaning up robot...")
        self.running = False
        self.control_running = False
        
        if self.robot:
            try:
                self.robot.send_program("stopl(0.5)")
            except:
                pass
        
        # Stop threads
        if self.control_thread and self.control_thread.is_alive():
            self.control_thread.join(timeout=1)
        
        if self.arrow_key_thread and self.arrow_key_thread.is_alive():
            self.arrow_key_thread.join(timeout=1)
        
        if self.robot:
            self.robot.close()
        
        print("✓ Robot cleanup complete") 