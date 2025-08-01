# Face and Thermal Tracking System

A modular robotics control system that provides both face tracking and thermal hotspot tracking capabilities using computer vision and PID control.

## System Overview

This system integrates multiple cameras and a robotic arm to track either human faces or thermal hotspots with precise control and safety features.

### Key Features

- **Dual Tracking Modes**: Face tracking using MediaPipe and thermal hotspot tracking
- **Modular Architecture**: Clean separation of concerns across multiple files
- **PID Control**: Separate tuned parameters for face vs thermal tracking
- **Safety Features**: Emergency stop, deadzone control, speed limiting
- **Real-time Display**: Side-by-side camera feeds with visual indicators
- **Manual Control**: Arrow key movement when tracking is disabled

## File Structure

```
Finalized Code/
├── config.py              # All configuration parameters
├── camera_manager.py      # Camera initialization and management
├── detection_algorithms.py # Face and thermal detection algorithms
├── robot_controller.py    # Robot connection and PID control
├── spacemouse_controller.py # 3D Space Mouse control integration
├── main_tracker.py        # Main application entry point
└── README.md             # This file
```

## Module Descriptions

### `config.py`
Centralized configuration file containing:
- Robot IP and camera indices
- PID parameters for both tracking modes
- Speed limits and control parameters
- Camera settings and processing parameters

### `camera_manager.py`
Handles camera operations:
- Regular camera (60 FPS) and thermal camera (25 FPS) initialization
- Frame capture and processing
- Thermal frame cropping and rotation
- Center point calculations for each camera

### `detection_algorithms.py`
Computer vision algorithms:
- **FaceDetector**: MediaPipe-based face detection
- **ThermalDetector**: Hotspot detection with area filtering
- Drawing functions for visual feedback

### `robot_controller.py`
Robot control and PID system:
- Robot connection and positioning
- Separate PID controllers for face and thermal tracking
- Speed command generation with different parameters per mode
- Emergency stop and safety features
- Arrow key manual control

### `spacemouse_controller.py`
3D Space Mouse integration:
- 3D Connexion Space Mouse connection and input processing
- Full 6DOF control (translation and rotation)
- Exponential scaling for precise control
- Only active when tracking modes are disabled
- Real-time movement with configurable deadzone and scaling

### `main_tracker.py`
Main application coordinator:
- Integrates all components
- Handles user interface and keyboard input
- Manages the main execution loop
- Coordinates between detection and control systems

## Hardware Requirements

- UR robot (tested with UR5/UR10)
- Regular camera (index 1)
- Thermal camera (index 0, HIKMICRO compatible)
- Network connection to robot

## Software Dependencies

```bash
pip install opencv-python mediapipe urx keyboard numpy pygame
```

## Usage

### Basic Operation

1. **Start the system**:
   ```bash
   cd "Finalized Code"
   python main_tracker.py
   ```

2. **Controls**:
   - **F**: Toggle face tracking ON/OFF
   - **T**: Toggle thermal tracking ON/OFF
   - **H**: Return to starting position
   - **SPACE**: Emergency stop (stops all tracking and robot)
   - **UP/DOWN arrows**: Manual X-axis movement (only when both tracking modes are OFF)
   - **ESC**: Exit application
   - **Space Mouse**: Automatically active when both tracking modes are OFF

### Tracking Modes

- **Face Tracking**: 
  - Max speed: 2.5 m/s
  - Uses MediaPipe for detection
  - Includes position smoothing
  - Higher PID gains for responsiveness

- **Thermal Tracking**:
  - Max speed: 0.5 m/s
  - Lower acceleration (0.1) and shorter time parameter (0.3s)
  - Conservative PID gains for precision
  - Tracks hottest regions with area filtering

- **Space Mouse Control**:
  - Full 6DOF control (translation + 3 wrist rotations)
  - Max translation speed: 0.15 m/s, Max rotation speed: 0.3 rad/s
  - Automatically active when both tracking modes are disabled
  - Exponential scaling for precise control
  - Real-time response with configurable deadzone and speed limits

### Safety Features

- Only one tracking mode can be active at a time
- Emergency stop immediately disables all tracking
- Deadzone prevents jittery movement near center
- Speed limits prevent dangerous movements
- Arrow keys and Space Mouse only work when both tracking modes are disabled
- Space Mouse automatically activates/deactivates based on tracking state
- Space Mouse requires pygame library for input handling

## Configuration

### Adjusting PID Parameters

Edit `config.py` to modify PID gains:

```python
# Face tracking (more aggressive)
FACE_PID_KP_Y = 0.002
FACE_PID_KI_Y = 0.0003
FACE_PID_KD_Y = 0.0006

# Thermal tracking (more conservative)
THERMAL_PID_KP_Y = 0.0008
THERMAL_PID_KI_Y = 0.0001
THERMAL_PID_KD_Y = 0.0003
```

### Camera Settings

```python
THERMAL_CAMERA_INDEX = 0
REGULAR_CAMERA_INDEX = 1
THERMAL_CAMERA_FPS = 25
REGULAR_CAMERA_FPS = 60
```

### Speed Limits

```python
# Tracking mode speed limits
MAX_SPEED_Y_FACE = 2.5      # Face tracking max speed
MAX_SPEED_Y_THERMAL = 0.5   # Thermal tracking max speed

# Space Mouse speed limits
SPACEMOUSE_MAX_TRANSLATION_SPEED = 0.15  # Max translation speed (m/s)
SPACEMOUSE_MAX_ROTATION_SPEED = 0.3      # Max rotation speed (rad/s)
```

## API Usage

The modular design allows individual components to be used independently:

```python
from camera_manager import CameraManager
from detection_algorithms import FaceDetector, ThermalDetector
from robot_controller import RobotController

# Initialize components
camera_manager = CameraManager()
face_detector = FaceDetector()
robot_controller = RobotController()

# Use individual functions
ret, frame = camera_manager.capture_regular_frame()
face_data = face_detector.detect(frame)
robot_controller.set_face_tracking(True)
```

## Troubleshooting

### Common Issues

1. **Camera not found**: Check camera indices in `config.py`
2. **Robot connection failed**: Verify robot IP and network connection
3. **Thermal tracking circling**: Ensure thermal center coordinates are correct
4. **Overshooting**: Adjust PID parameters in `config.py`

### Debug Mode

Enable debug output by modifying the detection algorithms to print coordinates and values.

## Development

### Adding New Features

1. **New detection algorithm**: Add to `detection_algorithms.py`
2. **New control mode**: Extend `robot_controller.py`
3. **Configuration changes**: Update `config.py`
4. **UI modifications**: Edit `main_tracker.py`

### Testing Individual Components

Each module can be tested independently:

```python
# Test camera manager
from camera_manager import CameraManager
cm = CameraManager()
cm.init_regular_camera()

# Test face detection
from detection_algorithms import FaceDetector
fd = FaceDetector()
```

## Performance Notes

- Thermal camera runs at 25 FPS for stability
- Regular camera runs at 60 FPS for responsiveness
- PID control loop runs at 60 Hz
- Face position smoothing uses 200ms window

## Safety Warnings

- Always test with low speeds first
- Keep emergency stop (SPACE) easily accessible
- Ensure adequate workspace clearance
- Monitor robot movement at all times
- Use appropriate safety equipment and procedures 