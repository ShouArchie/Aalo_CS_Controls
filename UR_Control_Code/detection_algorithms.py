"""
Detection Algorithms for Face and Thermal Tracking System
Contains face detection and thermal hotspot detection algorithms
"""

import cv2
import numpy as np
import mediapipe as mp
from config import *


class FaceDetector:
    """Face detection using MediaPipe"""
    
    def __init__(self, min_detection_confidence=0.5):
        self.mp_face = mp.solutions.face_detection
        self.face_detection = self.mp_face.FaceDetection(
            min_detection_confidence=min_detection_confidence
        )
    
    def detect(self, frame):
        """
        Detect face in frame and return face center coordinates and bounding box.
        
        Returns:
            tuple: (face_x, face_y, x, y, w, h) or None if no face detected
        """
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_detection.process(rgb_frame)
            
            if results.detections:
                detection = results.detections[0]  # Use first face
                bbox = detection.location_data.relative_bounding_box
                
                # Convert to pixels
                x = int(bbox.xmin * frame.shape[1])
                y = int(bbox.ymin * frame.shape[0])
                w = int(bbox.width * frame.shape[1])
                h = int(bbox.height * frame.shape[0])
                
                # Face center
                face_x = x + w // 2
                face_y = y + h // 2
                
                return face_x, face_y, x, y, w, h
            
            return None
        except Exception as e:
            print(f"Face detection error: {e}")
            return None
    
    def draw_detection(self, frame, detection_data):
        """Draw face detection on frame."""
        if detection_data:
            face_x, face_y, x, y, w, h = detection_data
            # Draw face rectangle and center
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.circle(frame, (face_x, face_y), 5, (0, 255, 0), -1)


class ThermalDetector:
    """Thermal hotspot detection"""
    
    def __init__(self, heat_threshold=THERMAL_HEAT_THRESHOLD, min_area=MIN_HEAT_AREA):
        self.heat_threshold = heat_threshold
        self.min_area = min_area
    
    def find_hottest_point(self, frame):
        """
        Find the hottest point in thermal image.
        
        Returns:
            tuple: (x, y, max_value) for the centroid of the hottest region or None
        """
        try:
            # If the frame is colored, convert to grayscale
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame

            # Threshold to find hot regions
            minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(gray)
            thresh_val = maxVal * self.heat_threshold
            _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)

            # Find contours of hot regions
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Filter contours by area
            valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > self.min_area]
            if not valid_contours:
                # Fallback to hottest pixel if no valid region
                x, y = maxLoc
                return x, y, maxVal

            # Find the contour with the greatest total heat
            max_heat = -1
            best_cx, best_cy, best_max = 0, 0, 0
            for cnt in valid_contours:
                mask = np.zeros_like(gray)
                cv2.drawContours(mask, [cnt], -1, 255, -1)
                region_vals = gray[mask == 255]
                total_heat = np.sum(region_vals)
                if total_heat > max_heat:
                    max_heat = total_heat
                    M = cv2.moments(cnt)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                    else:
                        cx, cy = 0, 0
                    region_max = float(np.max(region_vals)) if region_vals.size > 0 else maxVal
                    best_cx, best_cy, best_max = cx, cy, region_max

            return best_cx, best_cy, best_max
        except Exception as e:
            print(f"Thermal detection error: {e}")
            return None
    
    def draw_detection(self, frame, detection_data):
        """Draw thermal detection on frame."""
        if detection_data:
            hot_x, hot_y, max_val = detection_data
            # Draw hottest point
            cv2.circle(frame, (hot_x, hot_y), 8, (0, 0, 255), 2)
            cv2.putText(frame, f"Hot: ({hot_x}, {hot_y}) {max_val:.1f}", 
                       (hot_x+10, hot_y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2) 