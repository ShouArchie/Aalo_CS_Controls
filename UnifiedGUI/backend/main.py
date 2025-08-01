from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cv2
import asyncio
import threading
import time
from pathlib import Path
import sys

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
    """Continuously capture frames from a camera and store the latest JPEG buffer."""

    def __init__(self, index: int, target_fps: int = 30):
        self.index = index
        self.target_fps = target_fps
        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera at index {index}")

        # Optimize for low latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer lag
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FPS, target_fps)

        self.running = False
        self.frame_bytes: bytes | None = None
        self.thread: threading.Thread | None = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                success, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if success:
                    self.frame_bytes = jpg.tobytes()
            else:
                time.sleep(0.01)  # Brief pause if capture fails

    def latest(self) -> bytes | None:
        return self.frame_bytes

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        if self.cap:
            self.cap.release()


# ------------------------------------------------------------------
# Fallback OpenCV thermal stream with colormap processing
# ------------------------------------------------------------------


class RawThermalStream(CameraStream):
    """Capture from a plain UVC thermal camera and apply false-color colormap."""

    def __init__(self, index: int = 2, target_fps: int = 25):
        super().__init__(index=index, target_fps=target_fps)

    def _loop(self):
        delay = 1.0 / max(self.target_fps, 1)
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Convert to grayscale (assume 8-bit or choose one channel)
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                else:
                    gray = frame

                # Normalize and apply colormap
                norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
                color = cv2.applyColorMap(norm.astype('uint8'), cv2.COLORMAP_INFERNO)

                ok, jpg = cv2.imencode('.jpg', color, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ok:
                    self.frame_bytes = jpg.tobytes()
            time.sleep(delay)


# ------------------------------------------------------------------
# HT301 thermal stream wrapper
# ------------------------------------------------------------------


class HT301Stream:
    """Use ThermalCameraCapture from capture_thermal to acquire frames."""

    def __init__(self, target_fps: int = 15):
        if ThermalCameraCapture is None:
            raise RuntimeError("ThermalCameraCapture module not available")

        self.target_fps = target_fps
        self.capture = ThermalCameraCapture(target_fps=target_fps,
                                            temp_filter_enabled=False)
        self.running = False
        self.frame_bytes: bytes | None = None
        self.thread: threading.Thread | None = None

    def start(self):
        if self.running:
            return
        if not self.capture.start():
            raise RuntimeError("HT301 camera failed to start")

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        delay = 1.0 / max(self.target_fps, 1)
        while self.running:
            frame = self.capture.get_latest_frame()
            if frame is not None:
                # frame is RGB; convert to BGR for JPEG encoding
                bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                ok, jpg = cv2.imencode('.jpg', bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ok:
                    self.frame_bytes = jpg.tobytes()
            time.sleep(delay)

    def latest(self) -> bytes | None:
        return self.frame_bytes

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
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


rgb_stream = CameraStream(index=1, target_fps=15)  # Lower FPS for less lag
rgb_stream.start()
print(f"✓ RGB camera started at index 1")

# Thermal stream (HT301 preferred)

thermal_stream: HT301Stream | CameraStream

try:
    thermal_stream = HT301Stream(target_fps=15)
    thermal_stream.start()
    print("✓ HT301 thermal camera started")
except Exception as e:
    print(f"HT301 init error: {e}. Falling back to webcam index 2.")
    thermal_stream = RawThermalStream(index=2, target_fps=25)
    thermal_stream.start()

# Start streams ensured above; collect running list for shutdown
running_streams = [s for s in (rgb_stream, thermal_stream) if s]


@app.get("/")
async def root():
    return {"status": "ok"}


async def _frame_sender(websocket: WebSocket, stream: CameraStream):
    """Send frames at ~100 Hz (10 ms sleep) or as fast as they arrive."""
    await websocket.accept()
    try:
        while True:
            frame = stream.latest()
            if frame:
                # Send raw JPEG bytes
                await websocket.send_bytes(frame)
            await asyncio.sleep(0.01)  # 100 Hz
    except WebSocketDisconnect:
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