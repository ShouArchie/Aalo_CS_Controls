from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cv2
import asyncio
import threading
import time
import queue
from pathlib import Path
import sys

# Import robot control
try:
    from robot_control import robot_controller
    print("✓ Robot control system imported")
except ImportError as e:
    print(f"✗ Robot control import failed: {e}")
    robot_controller = None

# ---- include HT301 capture from existing Python_GUI stack ----
ROOT_DIR = Path(__file__).resolve().parents[2]
PY_GUI_DIR = ROOT_DIR / 'Python_GUI'
HT301_LIB_DIR = PY_GUI_DIR / 'Python Context HT301 Thermal Stack' / 'IR-Py-Thermal-master'

print(f"Adding paths to sys.path:")
print(f"  PY_GUI_DIR: {PY_GUI_DIR}")
print(f"  HT301_LIB_DIR: {HT301_LIB_DIR}")

for path in [str(PY_GUI_DIR), str(HT301_LIB_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)
        print(f"  Added: {path}")

# Try importing thermal capture
ThermalCameraCapture = None
try:
    print("Attempting to import capture_thermal...")
    from capture_thermal import ThermalCameraCapture  # type: ignore
    print("✓ Successfully imported ThermalCameraCapture")
except Exception as e:
    print(f"✗ Failed to import ThermalCameraCapture: {e}")
    print(f"  Python path: {sys.path[:3]}...")  # Show first 3 paths
    try:
        # Try importing irpythermal directly
        import irpythermal
        print("✓ irpythermal module available")
    except Exception as e2:
        print(f"✗ irpythermal also failed: {e2}")

app = FastAPI()

class TempRangeRequest(BaseModel):
    min_temp: float
    max_temp: float

class RobotConnectionRequest(BaseModel):
    ip: str

class RobotMoveRequest(BaseModel):
    direction: str
    distance: float = 0.05

class ThermalTrackingRequest(BaseModel):
    enabled: bool

class HomeJointsRequest(BaseModel):
    joints: list[float]  # Joint angles in degrees

# Allow all origins for local setup (laptop-only deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Generic OpenCV camera stream (used for RGB webcam)
# ------------------------------------------------------------------
class CameraStream:
    """High-performance camera stream with optimized threading and minimal latency."""

    def __init__(self, index: int, target_fps: int = 30, priority: str = "normal"):
        self.index = index
        self.target_fps = target_fps
        self.priority = priority  # "high", "normal", "low"
        
        # Initialize camera with optimal settings
        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera at index {index}")

        # Aggressive optimization for lowest latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Single frame buffer
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FPS, target_fps)
        
        # Set resolution for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Threading
        self.running = False
        self.frame_bytes: bytes | None = None
        self.capture_thread: threading.Thread | None = None
        self.encode_thread: threading.Thread | None = None
        
        # Frame queue for decoupling capture and encoding
        self.frame_queue = queue.Queue(maxsize=2)  # Small queue to reduce latency
        self.last_frame_time = 0
        
        # JPEG encoding settings
        self.jpeg_quality = 85 if priority == "high" else 75
        self.jpeg_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]

    def start(self):
        if self.running:
            return
        self.running = True
        
        # Separate threads for capture and encoding for better performance
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.encode_thread = threading.Thread(target=self._encode_loop, daemon=True)
        
        # Set thread priority based on camera importance
        if self.priority == "high":
            try:
                import os
                if hasattr(os, 'sched_setparam'):
                    # Linux/Unix thread priority
                    param = os.sched_param(os.sched_get_priority_max(os.SCHED_FIFO))
                    os.sched_setparam(0, param)
            except:
                pass  # Platform doesn't support priority setting
        
        self.capture_thread.start()
        self.encode_thread.start()

    def _capture_loop(self):
        """High-priority capture loop - minimal processing."""
        target_interval = 1.0 / self.target_fps
        while self.running:
            start_time = time.time()
            
            ret, frame = self.cap.read()
            if ret:
                # Non-blocking queue put - drop frames if encoding can't keep up
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    # Drop oldest frame and add new one
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame)
                    except queue.Empty:
                        pass
            
            # Precise timing control
            elapsed = time.time() - start_time
            sleep_time = max(0, target_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _encode_loop(self):
        """Encoding loop - handles JPEG compression in separate thread."""
        while self.running:
            try:
                # Get frame with timeout
                frame = self.frame_queue.get(timeout=0.1)
                
                # Fast JPEG encoding
                success, jpg = cv2.imencode(".jpg", frame, self.jpeg_params)
                if success:
                    self.frame_bytes = jpg.tobytes()
                    self.last_frame_time = time.time()
                    
            except queue.Empty:
                time.sleep(0.01)  # Brief pause if no frames available
            except Exception as e:
                print(f"Encode error: {e}")
                time.sleep(0.01)

    def latest(self) -> bytes | None:
        return self.frame_bytes

    def get_fps(self) -> float:
        """Calculate actual FPS."""
        if self.last_frame_time == 0:
            return 0
        return 1.0 / max(0.001, time.time() - self.last_frame_time)

    def stop(self):
        self.running = False
        
        # Join threads with timeout
        for thread in [self.capture_thread, self.encode_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=1)
        
        # Release camera
        if self.cap:
            self.cap.release()


# ------------------------------------------------------------------
# Fallback OpenCV thermal stream with colormap processing
# ------------------------------------------------------------------


class RawThermalStream(CameraStream):
    """Capture from a plain UVC thermal camera and apply false-color colormap."""

    def __init__(self, index: int = 2, target_fps: int = 25):
        super().__init__(index=index, target_fps=target_fps, priority="high")

    def _encode_loop(self):
        """Override encoding loop for thermal colormap processing."""
        while self.running:
            try:
                # Get frame with timeout
                frame = self.frame_queue.get(timeout=0.1)
                
                # Convert to grayscale (assume 8-bit or choose one channel)
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                else:
                    gray = frame

                # Normalize and apply colormap
                norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
                color = cv2.applyColorMap(norm.astype('uint8'), cv2.COLORMAP_INFERNO)

                ok, jpg = cv2.imencode('.jpg', color, self.jpeg_params)
                if ok:
                    self.frame_bytes = jpg.tobytes()
                    self.last_frame_time = time.time()
                    
            except queue.Empty:
                time.sleep(0.01)
            except Exception as e:
                print(f"Thermal colormap error: {e}")
                time.sleep(0.01)


# ------------------------------------------------------------------
# HT301 thermal stream wrapper
# ------------------------------------------------------------------


class HT301Stream:
    """High-performance HT301 thermal camera stream with optimized threading."""

    def __init__(self, target_fps: int = 15):
        if ThermalCameraCapture is None:
            raise RuntimeError("ThermalCameraCapture module not available")

        self.target_fps = target_fps
        self.capture = ThermalCameraCapture(target_fps=target_fps,
                                            temp_filter_enabled=False)
        self.running = False
        self.frame_bytes: bytes | None = None
        self.capture_thread: threading.Thread | None = None
        self.encode_thread: threading.Thread | None = None
        
        # Frame queue for decoupling capture and encoding
        self.frame_queue = queue.Queue(maxsize=2)
        self.last_frame_time = 0
        
        # High quality JPEG for thermal data
        self.jpeg_params = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

    def start(self):
        if self.running:
            return
        if not self.capture.start():
            raise RuntimeError("HT301 camera failed to start")

        self.running = True
        
        # Separate threads for better performance
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.encode_thread = threading.Thread(target=self._encode_loop, daemon=True)
        
        self.capture_thread.start()
        self.encode_thread.start()

    def _capture_loop(self):
        """High-priority thermal capture loop."""
        target_interval = 1.0 / max(self.target_fps, 1)
        while self.running:
            start_time = time.time()
            
            frame = self.capture.get_latest_frame()
            if frame is not None:
                # Non-blocking queue put
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    # Drop oldest frame and add new one
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame)
                    except queue.Empty:
                        pass
            
            # Precise timing control
            elapsed = time.time() - start_time
            sleep_time = max(0, target_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _encode_loop(self):
        """Encoding loop for thermal frames."""
        while self.running:
            try:
                # Get frame with timeout
                frame = self.frame_queue.get(timeout=0.1)
                
                # frame is RGB; convert to BGR for JPEG encoding
                bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Rotate thermal camera view by 180 degrees
                rotated = cv2.rotate(bgr, cv2.ROTATE_180)
                
                ok, jpg = cv2.imencode('.jpg', rotated, self.jpeg_params)
                if ok:
                    self.frame_bytes = jpg.tobytes()
                    self.last_frame_time = time.time()
                    
            except queue.Empty:
                time.sleep(0.01)
            except Exception as e:
                print(f"Thermal encode error: {e}")
                time.sleep(0.01)

    def latest(self) -> bytes | None:
        return self.frame_bytes

    def get_fps(self) -> float:
        """Calculate actual FPS."""
        if self.last_frame_time == 0:
            return 0
        return 1.0 / max(0.001, time.time() - self.last_frame_time)

    def stop(self):
        self.running = False
        
        # Join threads with timeout
        for thread in [self.capture_thread, self.encode_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=1)
                
        if hasattr(self.capture, 'stop'):
            try:
                self.capture.stop()
            except Exception:
                pass


# Instantiate streams AFTER class definitions

# RGB stream (try index 1 then 0)
def _init_rgb() -> CameraStream | None:
    for idx in (1, 0, 2):
        try:
            cs = CameraStream(index=idx, target_fps=30)
            cs.start()
            print(f"✓ RGB camera started at index {idx}")
            return cs
        except Exception as e:
            print(f"RGB camera index {idx} failed: {e}")
    return None


# Initialize RGB camera with high priority for smooth video - try 60fps first
try:
    rgb_stream = CameraStream(index=1, target_fps=60, priority="high")
    rgb_stream.start()
    print(f"✓ RGB camera started at index 1 with 60 FPS high priority")
except Exception as e:
    print(f"60 FPS failed for RGB, trying 30 FPS fallback: {e}")
    rgb_stream = CameraStream(index=1, target_fps=30, priority="high")
    rgb_stream.start()
    print(f"✓ RGB camera started at index 1 with 30 FPS fallback")

# Thermal stream (HT301 preferred) with high priority - try 60fps first
thermal_stream: HT301Stream | CameraStream

try:
    thermal_stream = HT301Stream(target_fps=60)  # Try 60 FPS for thermal
    thermal_stream.start()
    print("✓ HT301 thermal camera started with 60 FPS high priority")
except Exception as e:
    print(f"HT301 60 FPS failed, trying 30 FPS: {e}")
    try:
        thermal_stream = HT301Stream(target_fps=30)
        thermal_stream.start()
        print("✓ HT301 thermal camera started with 30 FPS fallback")
    except Exception as e2:
        print(f"HT301 init error: {e2}. Falling back to webcam index 2.")
        thermal_stream = RawThermalStream(index=2, target_fps=60)
        try:
            thermal_stream.start()
            print("✓ Fallback thermal camera started with 60 FPS")
        except Exception as e3:
            print(f"60 FPS fallback failed, using 30 FPS: {e3}")
            thermal_stream = RawThermalStream(index=2, target_fps=30)
            thermal_stream.start()
            print("✓ Fallback thermal camera started with 30 FPS")

# Start streams ensured above; collect running list for shutdown
running_streams = [s for s in (rgb_stream, thermal_stream) if s]


@app.get("/")
async def root():
    return {"status": "ok"}


async def _frame_sender(websocket: WebSocket, stream: CameraStream | HT301Stream):
    """High-performance frame sender optimized for minimal latency."""
    await websocket.accept()
    try:
        last_frame = None
        frame_count = 0
        start_time = time.time()
        
        while True:
            frame = stream.latest()
            if frame and frame != last_frame:
                # Only send new frames to reduce bandwidth
                await websocket.send_bytes(frame)
                last_frame = frame
                frame_count += 1
                
                # Log performance every 100 frames
                if frame_count % 100 == 0:
                    elapsed = time.time() - start_time
                    actual_fps = frame_count / elapsed
                    print(f"WebSocket FPS: {actual_fps:.1f}")
                    frame_count = 0
                    start_time = time.time()
            
            # Minimal sleep for high-frequency updates
            await asyncio.sleep(0.005)  # 200 Hz check rate
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
        return
    except Exception as e:
        print(f"WebSocket error: {e}")
        return


@app.websocket("/ws/rgb")
async def ws_rgb(websocket: WebSocket):
    await _frame_sender(websocket, rgb_stream)


@app.websocket("/ws/thermal")
async def ws_thermal(websocket: WebSocket):
    await _frame_sender(websocket, thermal_stream)


# Graceful shutdown for camera resources
@app.on_event("shutdown")
async def shutdown_event():
    for stream in running_streams:
        stream.stop()


@app.get("/api/temperature/{x}/{y}")
async def get_temperature_at_point(x: int, y: int):
    """Get temperature value at specific pixel coordinates from HT301."""
    if isinstance(thermal_stream, HT301Stream):
        try:
            # No rotation - coordinates map directly
            temp = thermal_stream.capture.get_temperature_at_point(x, y)
            return {"temperature": temp, "x": x, "y": y, "unit": "C"}
        except Exception as e:
            return {"error": str(e)}
    else:
        return {"error": "Temperature data only available with HT301 camera"}


@app.get("/api/thermal/minmax")
async def get_thermal_minmax():
    """Get min/max temperature data from HT301."""
    if isinstance(thermal_stream, HT301Stream):
        try:
            data = thermal_stream.capture.get_min_max_temperatures()
            return data if data else {"error": "No thermal data available"}
        except Exception as e:
            return {"error": str(e)}
    else:
        return {"error": "Temperature data only available with HT301 camera"}


@app.post("/api/thermal/filter/toggle")
async def toggle_temperature_filter():
    """Toggle temperature filter on/off."""
    if isinstance(thermal_stream, HT301Stream):
        try:
            enabled = thermal_stream.capture.toggle_temperature_filter()
            return {"enabled": enabled, "success": True}
        except Exception as e:
            return {"error": str(e), "success": False}
    else:
        return {"error": "Temperature filter only available with HT301 camera", "success": False}


@app.post("/api/thermal/filter/range")
async def set_temperature_range(request: TempRangeRequest):
    """Set temperature filter range."""
    if isinstance(thermal_stream, HT301Stream):
        try:
            min_temp = request.min_temp
            max_temp = request.max_temp
                
            success = thermal_stream.capture.set_temperature_filter_range(min_temp, max_temp)
            return {"success": success, "min_temp": min_temp, "max_temp": max_temp}
        except Exception as e:
            return {"error": str(e), "success": False}
    else:
        return {"error": "Temperature filter only available with HT301 camera", "success": False}


@app.post("/api/thermal/palette/cycle")
async def cycle_color_palette():
    """Cycle through thermal color palettes."""
    if isinstance(thermal_stream, HT301Stream):
        try:
            palette_name = thermal_stream.capture.cycle_color_palette()
            return {"palette": palette_name, "success": True}
        except Exception as e:
            return {"error": str(e), "success": False}
    else:
        return {"error": "Color palette only available with HT301 camera", "success": False}


@app.post("/api/thermal/calibrate")
async def manual_calibration():
    """Trigger manual flat field correction (FFC)."""
    if isinstance(thermal_stream, HT301Stream):
        try:
            success = thermal_stream.capture.trigger_manual_ffc()
            return {"success": success}
        except Exception as e:
            return {"error": str(e), "success": False}
    else:
        return {"error": "Manual calibration only available with HT301 camera", "success": False}


# ===== ROBOT CONTROL API ENDPOINTS =====

@app.post("/api/robot/connect")
async def connect_robot(request: RobotConnectionRequest):
    """Connect to UR10e robot at specified IP address."""
    if robot_controller is None:
        return {"connected": False, "error": "Robot controller not available"}
    
    result = robot_controller.connect(request.ip)
    return result

@app.post("/api/robot/disconnect")
async def disconnect_robot():
    """Disconnect from UR10e robot."""
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.disconnect()
    return result

@app.post("/api/robot/home")
async def move_robot_home():
    """Move robot to home position."""
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.move_to_home()
    return result

@app.post("/api/robot/move")
async def move_robot_manual(request: RobotMoveRequest):
    """Manual robot movement in specified direction."""
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.move_manual(request.direction, request.distance)
    return result

@app.post("/api/robot/thermal-tracking")
async def toggle_thermal_tracking(request: ThermalTrackingRequest):
    """Toggle thermal tracking on/off."""
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    if request.enabled:
        result = robot_controller.start_thermal_tracking()
    else:
        result = robot_controller.stop_thermal_tracking()
    
    return result

@app.get("/api/robot/status")
async def get_robot_status():
    """Get current robot status and position."""
    if robot_controller is None:
        return {
            "connected": False,
            "error": "Robot controller not available",
            "position": "UNKNOWN",
            "thermal_tracking": False,
            "spacemouse_connected": False
        }
    
    status = robot_controller.get_status()
    return status

@app.post("/api/robot/home-joints")
async def move_robot_home_joints(request: HomeJointsRequest):
    """Move robot to specific joint angles (home joints)."""
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.move_to_joint_angles(request.joints)
    return result

@app.post("/api/robot/config/home-joints")
async def update_home_joints_config(request: HomeJointsRequest):
    """Update the home joints configuration."""
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.update_home_joints_config(request.joints)
    return result 