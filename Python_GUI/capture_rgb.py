"""
RGB Camera Capture Module for GUI v8

Captures RGB video from external USB webcam using OpenCV.
Optimized with threading and hardware configurations for low latency.
"""

import cv2
import threading
import queue
import time
import logging
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)


class RGBCameraCapture:
    """RGB camera capture using OpenCV with threading for low latency."""
    
    def __init__(self, camera_index: int = 0, target_fps: int = 30):
        """Initialize RGB camera capture."""
        self.camera_index = camera_index
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        
        # Camera device
        self.camera = None
        
        # Threading components for low latency
        self.running = False
        self.capture_thread = None
        self.frame_queue = queue.Queue(maxsize=2)  # Prevent stale frames
        
        logger.info(f"RGBCameraCapture initialized with camera_index={camera_index}, target_fps={target_fps}")
    
    def start(self) -> bool:
        """Start RGB camera capture."""
        if self.running:
            logger.warning("RGB camera already running")
            return True
        
        # Initialize camera
        if not self._initialize_camera():
            logger.error("Failed to initialize RGB camera")
            return False
        
        # Start capture thread
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        logger.info("RGB camera capture started")
        return True
    
    def stop(self):
        """Stop RGB camera capture."""
        logger.info("Stopping RGB camera capture...")
        
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        
        if self.camera:
            self.camera.release()
            self.camera = None
        
        logger.info("RGB camera capture stopped")
    
    def _initialize_camera(self) -> bool:
        """Initialize the RGB camera hardware."""
        try:
            # DirectShow backend for webcam compatibility
            self.camera = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            
            if not self.camera.isOpened():
                logger.error(f"Failed to open camera at index {self.camera_index}")
                return False
            
            # Hardware optimizations for latency and bandwidth
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))  # Bandwidth
            self.camera.set(cv2.CAP_PROP_FPS, self.target_fps)
            
            # High resolution for quality
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            
            # Latency optimizations
            try:
                self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # Disable auto-focus (latency killer)
            except:
                pass  # Some cameras don't support this
            
            # Test frame capture
            ret, frame = self.camera.read()
            if not ret or frame is None:
                logger.error("Failed to capture test frame from RGB camera")
                self.camera.release()
                return False
            
            logger.info(f"RGB camera initialized - Frame size: {frame.shape}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RGB camera: {e}")
            if self.camera:
                self.camera.release()
                self.camera = None
            return False
    
    def _capture_loop(self):
        """Main capture loop running in separate thread."""
        logger.info("RGB camera capture loop started")
        
        while self.running:
            loop_start = time.time()
            
            try:
                if not self.camera or not self.camera.isOpened():
                    logger.error("Camera not available in capture loop")
                    break
                
                # Capture frame
                ret, frame = self.camera.read()
                
                if not ret or frame is None:
                    logger.warning("Failed to capture frame from RGB camera")
                    time.sleep(0.1)
                    continue
                
                # Convert BGR to RGB for consistent display
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Put frame in queue (non-blocking)
                try:
                    self.frame_queue.put(rgb_frame, block=False)
                except queue.Full:
                    # Remove oldest frame if queue is full (prevent stale frames)
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put(rgb_frame, block=False)
                    except queue.Empty:
                        pass
                
                # Frame rate control for consistent timing
                elapsed = time.time() - loop_start
                sleep_time = max(0.001, self.frame_interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in RGB capture loop: {e}")
                break
        
        logger.info("RGB camera capture loop ended")
    
    def get_latest_frame(self) -> Optional:
        """Get the latest RGB frame."""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None
    
    def is_running(self) -> bool:
        """Check if camera is running."""
        return self.running and self.camera is not None


if __name__ == "__main__":
    """Test RGB camera capture."""
    logging.basicConfig(level=logging.INFO)
    
    print("Testing RGB camera capture...")
    camera = RGBCameraCapture(camera_index=0)
    
    if camera.start():
        print("RGB camera started successfully")
        
        # Test for 10 seconds
        start_time = time.time()
        frame_count = 0
        
        while time.time() - start_time < 10:
            frame = camera.get_latest_frame()
            if frame is not None:
                frame_count += 1
                print(f"Captured frame {frame_count}, shape: {frame.shape}")
            time.sleep(0.1)
        
        camera.stop()
        print(f"Captured {frame_count} frames in 10 seconds")
    else:
        print("Failed to start RGB camera")