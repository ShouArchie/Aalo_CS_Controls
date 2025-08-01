"""
Configuration file for Face and Thermal Tracking System
Contains all configurable parameters and settings
"""

# === ROBOT CONFIGURATION ===
ROBOT_IP = "192.168.10.255"

# === CAMERA CONFIGURATION ===
THERMAL_CAMERA_INDEX = 0
REGULAR_CAMERA_INDEX = 1

# === CAMERA SETTINGS ===
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
REGULAR_CAMERA_FPS = 60
THERMAL_CAMERA_FPS = 25

# === ROBOT STARTING POSITION (in radians) ===
import math
START_JOINTS = [
    0.0,                    # Base = 0°
    math.radians(-60),      # Shoulder = -60°
    math.radians(80),       # Elbow = 80°
    math.radians(-110),     # Wrist1 = -110°
    math.radians(270),      # Wrist2 = 270°
    math.radians(-90)       # Wrist3 = -90°
]

# === PID CONTROLLER PARAMETERS ===
# Face tracking PID gains
FACE_PID_KP_Y = 0.002   # Proportional gain for Y (left/right)
FACE_PID_KI_Y = 0.0003  # Integral gain for Y
FACE_PID_KD_Y = 0.0006  # Derivative gain for Y
FACE_PID_KP_Z = 0.002   # Proportional gain for Z (up/down)
FACE_PID_KI_Z = 0.0003  # Integral gain for Z
FACE_PID_KD_Z = 0.0006  # Derivative gain for Z

# Thermal tracking PID gains (more conservative)
THERMAL_PID_KP_Y = 0.0008  # Lower proportional gain for thermal Y
THERMAL_PID_KI_Y = 0.0001  # Lower integral gain for thermal Y
THERMAL_PID_KD_Y = 0.0003  # Lower derivative gain for thermal Y
THERMAL_PID_KP_Z = 0.0008  # Lower proportional gain for thermal Z
THERMAL_PID_KI_Z = 0.0001  # Lower integral gain for thermal Z
THERMAL_PID_KD_Z = 0.0003  # Lower derivative gain for thermal Z

# === SPEED LIMITS ===
# Face tracking speed limits (m/s)
MAX_SPEED_Y_FACE = 2.5
MAX_SPEED_Z_FACE = 2.5

# Thermal tracking speed limits (m/s)
MAX_SPEED_Y_THERMAL = 0.5
MAX_SPEED_Z_THERMAL = 0.5

# === CONTROL PARAMETERS ===
DEADZONE_RADIUS = 25  # pixels - deadzone to prevent jittery movement
X_MOVE_STEP = 0.05    # 50mm steps for X-axis arrow key movement
FILTER_WINDOW = 0.2   # 200ms window for face position smoothing

# === SPEEDL COMMAND PARAMETERS ===
# Face tracking speedL parameters
FACE_ACCELERATION = 1.0
FACE_TIME_PARAM = 0.8

# Thermal tracking speedL parameters
THERMAL_ACCELERATION = 0.1
THERMAL_TIME_PARAM = 0.3

# === THERMAL CAMERA PROCESSING ===
THERMAL_CROP_TOP = 80     # Pixels to crop from top
THERMAL_CROP_RIGHT = 80   # Pixels to crop from right
THERMAL_HEAT_THRESHOLD = 0.9  # 90% of max value for heat detection
MIN_HEAT_AREA = 200       # Minimum area in pixels for valid heat regions

# === CONTROL LOOP SETTINGS ===
CONTROL_LOOP_FREQUENCY = 60  # Hz - PID control loop frequency

# === SPACE MOUSE CONFIGURATION ===
SPACEMOUSE_TRANSLATION_SCALE = 0.3  # Scale factor for translation (m per axis unit)
SPACEMOUSE_ROTATION_SCALE = 0.5     # Scale factor for rotation (rad per axis unit)
SPACEMOUSE_DEADZONE = 0.6           # Deadzone threshold for all axes
SPACEMOUSE_UPDATE_RATE = 30         # Hz - Space mouse update frequency

# Space Mouse speed limits (m/s for translation, rad/s for rotation)
SPACEMOUSE_MAX_TRANSLATION_SPEED = 0.15  # Maximum translation speed (m/s)
SPACEMOUSE_MAX_ROTATION_SPEED = 0.3      # Maximum rotation speed (rad/s) 