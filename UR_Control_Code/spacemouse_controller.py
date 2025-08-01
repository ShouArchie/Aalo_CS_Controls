"""
Space Mouse Controller for Face and Thermal Tracking System
Handles 3D Connexion Space Mouse input for manual robot control
"""

import pygame
import time
import math
import threading
from config import *


class SpaceMouseController:
    """Handles Space Mouse connection and input processing"""
    
    def __init__(self, robot_controller):
        self.robot_controller = robot_controller
        self.spacemouse_connected = False
        self.joystick = None
        self.spacemouse_active = False
        self.running = False
        self.spacemouse_thread = None
        
        # Control parameters from config
        self.translation_scale = SPACEMOUSE_TRANSLATION_SCALE
        self.rotation_scale = SPACEMOUSE_ROTATION_SCALE
        
        # Movement tracking
        self._last_movement_active = False
        
    def connect_spacemouse(self):
        """Connect to the 3D Connexion Space Mouse."""
        try:
            print("Initializing Space Mouse...")
            
            # Initialize pygame joystick module
            pygame.init()
            pygame.joystick.init()
            
            # Get number of joysticks/input devices
            joystick_count = pygame.joystick.get_count()
            print(f"Found {joystick_count} input device(s)")
            
            if joystick_count == 0:
                print("✗ No input devices detected")
                return False
            
            # Look for 3D Connexion devices
            for i in range(joystick_count):
                js = pygame.joystick.Joystick(i)
                js.init()
                device_name = js.get_name().lower()
                print(f"Device {i}: {js.get_name()}")
                print(f"  Axes: {js.get_numaxes()}, Buttons: {js.get_numbuttons()}")
                
                # Check if this looks like a 3D Connexion device
                if ("3dconnexion" in device_name or 
                    "spacemouse" in device_name or 
                    js.get_numaxes() >= 6):
                    
                    print(f"✓ Using Space Mouse: {js.get_name()}")
                    self.joystick = js
                    self.spacemouse_connected = True
                    return True
            
            # Use first device as fallback
            if joystick_count > 0:
                js = pygame.joystick.Joystick(0)
                js.init()
                print(f"⚠ Using first available device: {js.get_name()}")
                self.joystick = js
                self.spacemouse_connected = True
                return True
            
            return False
                
        except Exception as e:
            print(f"✗ Error connecting to Space Mouse: {e}")
            return False
    
    def read_spacemouse_input(self):
        """Read and process space mouse input with deadzone filtering."""
        if not self.spacemouse_connected or not self.joystick:
            return None
            
        try:
            num_axes = self.joystick.get_numaxes()
            if num_axes < 6:
                return None
                
            axis_values = [self.joystick.get_axis(i) for i in range(num_axes)]
            
            # Apply deadzone from config
            for i in range(len(axis_values)):
                if abs(axis_values[i]) < SPACEMOUSE_DEADZONE:
                    axis_values[i] = 0.0
            
            # Axis mapping based on the original implementation:
            # Axis 0: Y translation (TCP)
            # Axis 1: X translation (reversed, TCP)
            # Axis 2: Z translation (reversed, TCP)
            # Axis 3: Wrist1 (joint 3)
            # Axis 4: Wrist2 (joint 4)
            # Axis 5: Wrist3 (joint 5)
            movement = {
                'x': axis_values[1] if len(axis_values) > 1 else 0.0,  # X (reversed)
                'y': axis_values[0] if len(axis_values) > 0 else 0.0,   # Y
                'z': -axis_values[2] if len(axis_values) > 2 else 0.0,  # Z (reversed)
                'wrist1': -axis_values[3] if len(axis_values) > 3 else 0.0,  # Wrist1
                'wrist2': -axis_values[4] if len(axis_values) > 4 else 0.0,  # Wrist2
                'wrist3': axis_values[5] if len(axis_values) > 5 else 0.0,   # Wrist3
                'raw_axes': axis_values
            }
            
            # Check for button presses
            num_buttons = self.joystick.get_numbuttons()
            button_pressed = False
            for i in range(num_buttons):
                if self.joystick.get_button(i):
                    button_pressed = True
                    break
            movement['button_pressed'] = button_pressed
            
            return movement
            
        except Exception as e:
            print(f"Error reading space mouse: {e}")
            return None
    
    def send_spacemouse_movement(self, movement):
        """Send space mouse movement commands to robot with exponential scaling."""
        if not movement or not self.robot_controller.robot:
            return
            
        movement_threshold = 0.7
        raw_axes = movement['raw_axes']
        
        # Apply exponential scaling for more precise control
        def exp_scale(x):
            if x == 0:
                return 0
            
            abs_x = abs(x)
            if abs_x <= SPACEMOUSE_DEADZONE:
                return 0
            
            # Remap from [deadzone, 1.0] to [0.0, 1.0]
            normalized_x = (abs_x - SPACEMOUSE_DEADZONE) / (1.0 - SPACEMOUSE_DEADZONE)
            
            # Apply exponential scaling
            exp_factor = 5.0
            scaled = (math.exp(exp_factor * normalized_x) - 1) / (math.exp(exp_factor) - 1)
            return scaled if x > 0 else -scaled
        
        dx = exp_scale(movement['x']) * self.translation_scale
        dy = exp_scale(movement['y']) * self.translation_scale
        dz = exp_scale(movement['z']) * self.translation_scale
        
        # Apply exponential scaling to wrist rotations
        wrist1_vel = exp_scale(movement['wrist1']) * self.rotation_scale
        wrist2_vel = exp_scale(movement['wrist2']) * self.rotation_scale
        wrist3_vel = exp_scale(movement['wrist3']) * self.rotation_scale
        
        # Apply speed limits
        dx = max(-SPACEMOUSE_MAX_TRANSLATION_SPEED, min(SPACEMOUSE_MAX_TRANSLATION_SPEED, dx))
        dy = max(-SPACEMOUSE_MAX_TRANSLATION_SPEED, min(SPACEMOUSE_MAX_TRANSLATION_SPEED, dy))
        dz = max(-SPACEMOUSE_MAX_TRANSLATION_SPEED, min(SPACEMOUSE_MAX_TRANSLATION_SPEED, dz))
        
        wrist1_vel = max(-SPACEMOUSE_MAX_ROTATION_SPEED, min(SPACEMOUSE_MAX_ROTATION_SPEED, wrist1_vel))
        wrist2_vel = max(-SPACEMOUSE_MAX_ROTATION_SPEED, min(SPACEMOUSE_MAX_ROTATION_SPEED, wrist2_vel))
        wrist3_vel = max(-SPACEMOUSE_MAX_ROTATION_SPEED, min(SPACEMOUSE_MAX_ROTATION_SPEED, wrist3_vel))
        
        # Check if there's any meaningful movement
        has_translation = abs(dx) > 0.0001 or abs(dy) > 0.0001 or abs(dz) > 0.0001
        has_rotation = abs(wrist1_vel) > 0.0001 or abs(wrist2_vel) > 0.0001 or abs(wrist3_vel) > 0.0001
        
        try:
            # Only send commands if there's actual movement or we need to stop
            if has_translation or has_rotation:
                # If any translation, send speedl in TCP frame
                if has_translation:
                    urscript_cmd = f"speedl([{dx:.6f}, {dy:.6f}, {dz:.6f}, 0, 0, 0], 0.5, 1.0)"
                    self.robot_controller.robot.send_program(urscript_cmd)
                
                # If any wrist movement, send speedj for wrists
                if has_rotation:
                    urscript_cmd = f"speedj([0,0,0,{wrist1_vel:.6f},{wrist2_vel:.6f},{wrist3_vel:.6f}], 2, 0.5)"
                    self.robot_controller.robot.send_program(urscript_cmd)
            elif all(abs(axis) < movement_threshold for axis in raw_axes):
                # Only send stop commands if axes were previously active
                if hasattr(self, '_last_movement_active') and self._last_movement_active:
                    self.robot_controller.robot.send_program("stopl(0.2)")
                    self.robot_controller.robot.send_program("speedj([0,0,0,0,0,0], 1, 0.2)")
                    self._last_movement_active = False
            
            # Track if movement was active this cycle
            self._last_movement_active = has_translation or has_rotation
                
        except Exception as e:
            print(f"Error sending space mouse movement: {e}")
    
    def update_spacemouse_state(self):
        """Update space mouse state based on tracking modes."""
        # Space mouse is active when both tracking modes are off
        should_be_active = (not self.robot_controller.face_tracking_active and 
                           not self.robot_controller.thermal_tracking_active and
                           self.spacemouse_connected)
        
        if should_be_active != self.spacemouse_active:
            self.spacemouse_active = should_be_active
            
            if not self.spacemouse_active:
                # Stop robot when deactivating space mouse
                try:
                    if self.robot_controller.robot:
                        self.robot_controller.robot.send_program("stopl(0.2)")
                except Exception as e:
                    print(f"Error stopping robot: {e}")
    
    def start_spacemouse_thread(self):
        """Start the space mouse control thread."""
        if not self.spacemouse_connected:
            return False
            
        self.running = True
        self.spacemouse_thread = threading.Thread(target=self._spacemouse_loop)
        self.spacemouse_thread.daemon = True
        self.spacemouse_thread.start()
        return True
    
    def _spacemouse_loop(self):
        """Main space mouse control loop."""
        try:
            import keyboard  # Import here to check for arrow key presses
            
            while self.running:
                # Update space mouse state based on tracking modes
                self.update_spacemouse_state()
                
                if self.spacemouse_active:
                    # Check if arrow keys are being pressed - pause space mouse if so
                    arrow_keys_pressed = False
                    try:
                        arrow_keys_pressed = (keyboard.is_pressed('up') or 
                                            keyboard.is_pressed('down') or
                                            keyboard.is_pressed('left') or
                                            keyboard.is_pressed('right'))
                    except:
                        pass  # Ignore keyboard check errors
                    
                    if not arrow_keys_pressed:
                        # Update pygame events
                        if pygame.get_init():
                            pygame.event.pump()
                        
                        # Read space mouse input
                        movement = self.read_spacemouse_input()
                        if movement:
                            # Check for button press
                            if movement['button_pressed']:
                                print("Space Mouse button pressed!")
                            
                            # Send movement commands
                            self.send_spacemouse_movement(movement)
                    else:
                        # Arrow keys are pressed, pause space mouse briefly
                        time.sleep(0.1)
                    
                    time.sleep(1.0 / SPACEMOUSE_UPDATE_RATE)  # Configurable update rate
                else:
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"Space mouse loop error: {e}")
    
    def cleanup(self):
        """Clean up space mouse resources."""
        print("Cleaning up space mouse...")
        self.running = False
        self.spacemouse_active = False
        
        # Stop space mouse thread
        if self.spacemouse_thread and self.spacemouse_thread.is_alive():
            self.spacemouse_thread.join(timeout=1)
        
        # Clean up pygame
        if self.spacemouse_connected:
            try:
                if self.joystick:
                    self.joystick.quit()
                pygame.quit()
            except:
                pass
        
        print("✓ Space mouse cleanup complete") 