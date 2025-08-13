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
    speed_percent: float = 100.0
    base_speed: float = 0.1

class ThermalTrackingRequest(BaseModel):
    enabled: bool

class HomeRequest(BaseModel):
    speed_percent: float = 100.0

class HomeJointsRequest(BaseModel):
    joints: list[float]
    speed_percent: float = 100.0  # Joint angles in degrees

class FineMovementRequest(BaseModel):
    direction: str
    step_size_mm: float = 1.0
    velocity: float = 0.1
    acceleration: float = 0.1

class StepSizeRequest(BaseModel):
    step_size_mm: float

class RotationRequest(BaseModel):
    axis: str
    angle_deg: float
    angular_velocity: float = 0.1
    speed_percent: float = 100.0



class TCPRequest(BaseModel):
    tcp_offset: list[float]
    tcp_id: int
    tcp_name: str

class ColdSprayRequest(BaseModel):
    acceleration: float = 0.1
    velocity: float = 0.1
    blend_radius: float = 0.001
    iterations: int = 7

class ConicalSprayRequest(BaseModel):
    spray_paths: str  # JSON string containing list of spray path dictionaries

class SpiralSprayRequest(BaseModel):
    spiral_params: str  # JSON string containing spiral parameters

class CustomPatternRequest(BaseModel):
    pattern_params: str  # JSON string containing custom pattern parameters

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
                # Flip RGB camera vertically
                # frame = cv2.flip(frame)
                
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
        # Actual FPS
        if self.last_frame_time == 0:
            return 0
        return 1.0 / max(0.001, time.time() - self.last_frame_time)

    def stop(self):
        self.running = False
        
        for thread in [self.capture_thread, self.encode_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=1)
        
        if self.cap:
            self.cap.release()

class RawThermalStream(CameraStream):
    def __init__(self, index: int = 2, target_fps: int = 25):
        super().__init__(index=index, target_fps=target_fps, priority="high")

    def _encode_loop(self):
        while self.running:
            try:
                # Get frame with timeout
                frame = self.frame_queue.get(timeout=0.1)
                
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                else:
                    gray = frame

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




class HT301Stream:
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
        
        self.frame_queue = queue.Queue(maxsize=2)
        self.last_frame_time = 0
        
        self.jpeg_params = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

    def start(self):
        if self.running:
            return
        if not self.capture.start():
            raise RuntimeError("HT301 camera failed to start")

        self.running = True
        
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.encode_thread = threading.Thread(target=self._encode_loop, daemon=True)
        
        self.capture_thread.start()
        self.encode_thread.start()

    def _capture_loop(self):
        target_interval = 1.0 / max(self.target_fps, 1)
        while self.running:
            start_time = time.time()
            
            frame = self.capture.get_latest_frame()
            if frame is not None:
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame)
                    except queue.Empty:
                        pass
            
            elapsed = time.time() - start_time
            sleep_time = max(0, target_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _encode_loop(self):
        while self.running:
            try:
                # Get frame with timeout
                frame = self.frame_queue.get(timeout=0.1)
                
                bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
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
        if self.last_frame_time == 0:
            return 0
        return 1.0 / max(0.001, time.time() - self.last_frame_time)

    def stop(self):
        self.running = False
        
        for thread in [self.capture_thread, self.encode_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=1)
                
        if hasattr(self.capture, 'stop'):
            try:
                self.capture.stop()
            except Exception:
                pass



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


def init_rgb_camera_with_retry(max_attempts=1) -> CameraStream | None:
    print(f"🔄 Attempting to initialize RGB camera (max {max_attempts} attempts)...")
    
    configs = [
        (1, 60, "high"),  # Preferred: index 1, 60fps, high priority
        (1, 30, "high"),  # Fallback: index 1, 30fps, high priority
        (0, 30, "normal"), # Fallback: index 0, 30fps, normal priority
        (2, 30, "normal"), # Fallback: index 2, 30fps, normal priority
    ]
    
    for attempt in range(max_attempts):
        print(f"🔄 RGB camera attempt {attempt + 1}/{max_attempts}")
        
        for idx, fps, priority in configs:
            try:
                print(f"  Trying RGB camera: index={idx}, fps={fps}, priority={priority}")
                rgb_stream = CameraStream(index=idx, target_fps=fps, priority=priority)
                rgb_stream.start()
                print(f"✅ RGB camera started: index={idx}, fps={fps}, priority={priority}")
                return rgb_stream
            except Exception as e:
                print(f"  ❌ RGB camera failed: index={idx}, fps={fps} - {e}")
        
        if attempt < max_attempts - 1:
            print(f"  🔄 Retrying RGB camera in 1 second...")
            time.sleep(1)
    
    print("❌ RGB camera initialization failed after all attempts")
    return None

rgb_stream = init_rgb_camera_with_retry(max_attempts=1)

def init_thermal_camera_with_retry(max_attempts=1) -> HT301Stream | CameraStream | None:
    print(f"🔄 Attempting to initialize thermal camera (max {max_attempts} attempts)...")
    
    configs = [
        ("HT301", 60),    # Preferred: HT301 at 60fps
        ("HT301", 30),    # Fallback: HT301 at 30fps 
        ("webcam", 60),   # Fallback: webcam index 2 at 60fps
        ("webcam", 30),   # Fallback: webcam index 2 at 30fps
    ]
    
    for attempt in range(max_attempts):
        print(f"🔄 Thermal camera attempt {attempt + 1}/{max_attempts}")
        
        for cam_type, fps in configs:
            try:
                if cam_type == "HT301":
                    print(f"  Trying HT301 thermal camera: fps={fps}")
                    thermal_stream = HT301Stream(target_fps=fps)
                    thermal_stream.start()
                    print(f"✅ HT301 thermal camera started: fps={fps}")
                    return thermal_stream
                else:  # webcam fallback
                    print(f"  Trying webcam thermal fallback: index=2, fps={fps}")
                    thermal_stream = RawThermalStream(index=2, target_fps=fps)
                    thermal_stream.start()
                    print(f"✅ Webcam thermal fallback started: index=2, fps={fps}")
                    return thermal_stream
            except Exception as e:
                print(f"  ❌ Thermal camera failed: {cam_type}, fps={fps} - {e}")
        
        if attempt < max_attempts - 1:
            print(f"  🔄 Retrying thermal camera in 1 second...")
            time.sleep(1)
    
    print("❌ Thermal camera initialization failed after all attempts")
    return None

thermal_stream = init_thermal_camera_with_retry(max_attempts=1)

running_streams = [s for s in (rgb_stream, thermal_stream) if s]

print("\n" + "="*60)
print("🚀 UNIFIED GUI BACKEND STARTUP SUMMARY")
print("="*60)
print(f"📹 RGB Camera:      {'✅ Available' if rgb_stream else '❌ Failed (3 attempts)'}")
print(f"🌡️  Thermal Camera:  {'✅ Available' if thermal_stream else '❌ Failed (3 attempts)'}")
print(f"🤖 Robot Controller: {'✅ Available' if robot_controller else '❌ Not Available'}")
print(f"🌐 WebSocket APIs:   {'✅ Active' if running_streams else '⚠️  Limited (no cameras)'}")
print(f"🎮 Robot APIs:       {'✅ Active' if robot_controller else '❌ Disabled'}")
print("="*60)
if not rgb_stream and not thermal_stream:
    print("⚠️  WARNING: No cameras available - camera views will not work")
if not robot_controller:
    print("⚠️  WARNING: Robot controller not available - robot controls disabled")
print("✅ Backend ready - cameras that failed will be ignored")
print("="*60 + "\n")


@app.get("/")
async def root():
    return {"status": "ok"}

@app.get("/api/status")
async def get_system_status():
    """Get the status of all system components."""
    return {
        "rgb_camera": rgb_stream is not None,
        "thermal_camera": thermal_stream is not None,
        "robot_controller": robot_controller is not None,
        "backend_ready": True
    }


async def _frame_sender(websocket: WebSocket, stream: CameraStream | HT301Stream):
    await websocket.accept()
    try:
        last_frame = None
        frame_count = 0
        start_time = time.time()
        
        while True:
            frame = stream.latest()
            if frame and frame != last_frame:
                await websocket.send_bytes(frame)
                last_frame = frame
                frame_count += 1
                
                if frame_count % 100 == 0:
                    elapsed = time.time() - start_time
                    actual_fps = frame_count / elapsed
                    print(f"WebSocket FPS: {actual_fps:.1f}")
                    frame_count = 0
                    start_time = time.time()
            
            await asyncio.sleep(0.005)  # 200 Hz check rate
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
        return
    except Exception as e:
        print(f"WebSocket error: {e}")
        return


@app.websocket("/ws/rgb")
async def ws_rgb(websocket: WebSocket):
    if rgb_stream is None:
        await websocket.accept()
        await websocket.close(code=1000, reason="RGB camera not available")
        print("❌ RGB WebSocket rejected - camera not initialized")
        return
    await _frame_sender(websocket, rgb_stream)


@app.websocket("/ws/thermal") 
async def ws_thermal(websocket: WebSocket):
    if thermal_stream is None:
        await websocket.accept()
        await websocket.close(code=1000, reason="Thermal camera not available")
        print("❌ Thermal WebSocket rejected - camera not initialized")
        return
    await _frame_sender(websocket, thermal_stream)


# shutdown for camera resources
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
    if robot_controller is None:
        return {"connected": False, "error": "Robot controller not available"}
    
    result = robot_controller.connect(request.ip)
    return result

@app.post("/api/robot/disconnect")
async def disconnect_robot():
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.disconnect()
    return result

@app.post("/api/robot/home")
async def move_robot_home(request: HomeRequest):
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.move_to_home(request.speed_percent)
    return result

@app.post("/api/robot/move")
async def move_robot_manual(request: RobotMoveRequest):
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.move_manual(request.direction, request.distance, request.speed_percent, request.base_speed)
    return result

@app.post("/api/robot/stop")
async def stop_robot_movement():
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.stop_movement()
    return result

@app.post("/api/robot/thermal-tracking")
async def toggle_thermal_tracking(request: ThermalTrackingRequest):
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    if request.enabled:
        result = robot_controller.start_thermal_tracking()
    else:
        result = robot_controller.stop_thermal_tracking()
    
    return result

@app.get("/api/robot/status")
async def get_robot_status():
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
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.move_to_joint_angles(request.joints, request.speed_percent)
    return result

@app.post("/api/robot/config/home-joints")
async def update_home_joints_config(request: HomeJointsRequest):
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.update_home_joints_config(request.joints)
    return result

@app.get("/api/robot/current-joints")
async def get_current_joint_angles():
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.get_current_joint_angles()
    return result

@app.post("/api/robot/config/save-current-as-home")
async def save_current_joints_as_home():
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.save_current_joints_as_home()
    return result

@app.post("/api/robot/move-fine")
async def move_robot_fine(request: FineMovementRequest):
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.move_fine(request.direction, request.step_size_mm, request.velocity, request.acceleration)
    return result

@app.post("/api/robot/config/step-size")
async def set_fine_step_size(request: StepSizeRequest):
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.set_fine_step_size(request.step_size_mm)
    return result

@app.post("/api/robot/move-rotation")
async def move_robot_rotation(request: RotationRequest):
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.move_rotation(request.axis, request.angle_deg, request.angular_velocity, request.speed_percent)
    return result



@app.post("/api/robot/set-tcp")
async def set_robot_tcp(request: TCPRequest):
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.set_tcp_offset(request.tcp_offset, request.tcp_id, request.tcp_name)
    return result

@app.get("/api/robot/get-tcp")
async def get_robot_tcp():
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.get_current_tcp()
    return result

@app.get("/api/robot/tcp-position")
async def get_tcp_position():
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.get_tcp_position()
    return result

@app.post("/api/robot/cold-spray")
async def execute_cold_spray_pattern(request: ColdSprayRequest):
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.execute_cold_spray_pattern(
        acc=request.acceleration,
        vel=request.velocity,
        blend_r=request.blend_radius,
        iterations=request.iterations
    )
    return result

@app.post("/api/robot/align-tool")
async def execute_tool_alignment():
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    result = robot_controller.execute_tool_alignment()
    return result

@app.post("/api/robot/conical-spray")
async def execute_conical_spray_paths(request: ConicalSprayRequest):
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    try:
        import json
        spray_paths = json.loads(request.spray_paths)
        
        if not isinstance(spray_paths, list) or len(spray_paths) == 0 or len(spray_paths) > 4:
            return {"success": False, "error": "Must provide 1-4 spray paths"}
        
        for i, path in enumerate(spray_paths):
            if not all(key in path for key in ['tilt', 'rev', 'cycle']):
                return {"success": False, "error": f"Path {i+1} missing required fields (tilt, rev, cycle)"}
            if not all(isinstance(path[key], (int, float)) for key in ['tilt', 'rev', 'cycle']):
                return {"success": False, "error": f"Path {i+1} fields must be numeric"}
            # validate approach_time if present (only allowed for first path)
            if 'approach_time' in path:
                if i > 0:
                    return {"success": False, "error": f"approach_time only allowed for first path"}
                if not isinstance(path['approach_time'], (int, float)):
                    return {"success": False, "error": f"approach_time must be numeric"}
        
        result = robot_controller.execute_conical_spray_paths(spray_paths)
        return result
        
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON format for spray paths"}
    except Exception as e:
        return {"success": False, "error": f"Failed to parse spray paths: {str(e)}"}


@app.post("/api/robot/spiral-spray")
async def execute_spiral_spray(request: SpiralSprayRequest):
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    try:
        import json
        spiral_params = json.loads(request.spiral_params)
        
        required_fields = ['tilt_start_deg', 'tilt_end_deg', 'revs', 'r_start_mm', 'r_end_mm', 'steps_per_rev', 'cycle_s', 'lookahead_s', 'gain', 'sing_tol_deg']
        for field in required_fields:
            if field not in spiral_params:
                return {"success": False, "error": f"Missing required field: {field}"}
            if not isinstance(spiral_params[field], (int, float)):
                return {"success": False, "error": f"Field {field} must be numeric"}
        
        spiral_params.setdefault('phase_offset_deg', 0.0)
        spiral_params.setdefault('cycle_s_start', None)
        spiral_params.setdefault('cycle_s_end', None) 
        spiral_params.setdefault('invert_tilt', False)
        spiral_params.setdefault('approach_time_s', 0.5)
        spiral_params.setdefault('delta_x_mm', 0.0)
        
        result = robot_controller.execute_spiral_spray(spiral_params)
        return result
        
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON format for spiral parameters"}
    except Exception as e:
        return {"success": False, "error": f"Failed to parse spiral parameters: {str(e)}"}


@app.post("/api/robot/custom-pattern")
async def execute_custom_pattern(request: CustomPatternRequest):
    if robot_controller is None:
        return {"success": False, "error": "Robot controller not available"}
    
    try:
        import json
        pattern_params = json.loads(request.pattern_params)
        
        required_fields = ['initial_cycles', 'tilt_angle_deg', 'initial_velocity', 'initial_acceleration', 'tilted_velocity', 'tilted_acceleration', 'tilted_cycles']
        for field in required_fields:
            if field not in pattern_params:
                return {"success": False, "error": f"Missing required field: {field}"}
            if not isinstance(pattern_params[field], (int, float)):
                return {"success": False, "error": f"Field {field} must be numeric"}
        
        result = robot_controller.execute_custom_pattern(pattern_params)
        return result
        
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON format for pattern parameters"}
    except Exception as e:
        return {"success": False, "error": f"Failed to parse pattern parameters: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    import socket
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("\n" + "="*70)
    print("🌐 UNIFIEDGUI BACKEND - NETWORK ACCESS ENABLED")
    print("="*70)
    print(f"🖥️  Local Access:    http://localhost:8000")
    print(f"🌍 Network Access:   http://{local_ip}:8000")
    print(f"📡 WebSocket RGB:    ws://{local_ip}:8000/ws/rgb")
    print(f"🌡️  WebSocket Thermal: ws://{local_ip}:8000/ws/thermal")
    print(f"🎮 API Base:         http://{local_ip}:8000/api/")
    print("="*70)
    print("⚠️  MAKE SURE TO UPDATE FRONTEND URLS TO USE THE NETWORK IP")
    print("   Example: Change 'localhost:8000' to f'{local_ip}:8000' in frontend")
    print("="*70 + "\n")
    
    uvicorn.run(
        app,  
        host="0.0.0.0",  # Listen on all network interfaces
        port=8000,
        reload=False,  # Disable reload in production
        log_level="info"
    ) 