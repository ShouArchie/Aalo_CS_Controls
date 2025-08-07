#!/usr/bin/env python3
"""
Camera Detection Utility
Scans for all available cameras and their supported resolutions
"""

import cv2
import sys


def test_camera_resolutions(camera_index):
    """Test common resolutions for a given camera"""
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return []
    
    # Common resolutions to test
    test_resolutions = [
        (640, 480),    # VGA
        (800, 600),    # SVGA
        (1024, 768),   # XGA
        (1280, 720),   # HD 720p
        (1280, 960),   # SXGA-
        (1920, 1080),  # Full HD 1080p
        (2560, 1440),  # QHD
        (3840, 2160),  # 4K UHD
        (320, 240),    # QVGA
        (160, 120),    # QQVGA
        (1600, 1200),  # UXGA
        (2048, 1536),  # QXGA
    ]
    
    supported_resolutions = []
    
    for width, height in test_resolutions:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # Read the actual resolution set by the camera
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Check if the camera actually supports this resolution
        ret, frame = cap.read()
        if ret and frame is not None and actual_width == width and actual_height == height:
            supported_resolutions.append((width, height))
    
    cap.release()
    return supported_resolutions


def get_camera_properties(camera_index):
    """Get basic camera properties and capabilities"""
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return None
    
    properties = {}
    
    # Get current resolution
    properties['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    properties['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    properties['fps'] = cap.get(cv2.CAP_PROP_FPS)
    
    # Get camera backend info
    properties['backend'] = cap.getBackendName()
    
    # Test if camera can capture a frame
    ret, frame = cap.read()
    properties['can_capture'] = ret and frame is not None
    
    if properties['can_capture']:
        properties['frame_shape'] = frame.shape
        properties['channels'] = frame.shape[2] if len(frame.shape) == 3 else 1
    
    # Get additional properties if available
    try:
        properties['brightness'] = cap.get(cv2.CAP_PROP_BRIGHTNESS)
        properties['contrast'] = cap.get(cv2.CAP_PROP_CONTRAST)
        properties['saturation'] = cap.get(cv2.CAP_PROP_SATURATION)
        properties['hue'] = cap.get(cv2.CAP_PROP_HUE)
        properties['gain'] = cap.get(cv2.CAP_PROP_GAIN)
        properties['exposure'] = cap.get(cv2.CAP_PROP_EXPOSURE)
    except:
        pass
    
    cap.release()
    return properties


def detect_all_cameras():
    """Detect all available cameras and their capabilities"""
    print("🔍 Scanning for available cameras...")
    print("=" * 60)
    
    available_cameras = []
    max_tested = 10  # Test camera indices 0-9
    
    for i in range(max_tested):
        print(f"\n📹 Testing camera index {i}...")
        
        # Quick test to see if camera exists
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # Camera exists, get detailed info
            print(f"✅ Camera {i} detected!")
            
            properties = get_camera_properties(i)
            if properties and properties['can_capture']:
                print(f"   📐 Default resolution: {properties['width']}x{properties['height']}")
                print(f"   🎥 FPS: {properties['fps']:.1f}")
                print(f"   🔧 Backend: {properties['backend']}")
                print(f"   🌈 Channels: {properties['channels']}")
                
                # Test supported resolutions
                print(f"   🔍 Testing supported resolutions...")
                resolutions = test_camera_resolutions(i)
                
                camera_info = {
                    'index': i,
                    'properties': properties,
                    'supported_resolutions': resolutions
                }
                available_cameras.append(camera_info)
                
                if resolutions:
                    print(f"   ✅ Supported resolutions ({len(resolutions)}):")
                    for width, height in sorted(resolutions, key=lambda x: x[0] * x[1]):
                        print(f"      • {width}x{height}")
                else:
                    print(f"   ⚠️  No standard resolutions detected")
            else:
                print(f"   ❌ Camera {i} exists but cannot capture frames")
        else:
            print(f"   ❌ No camera at index {i}")
        
        cap.release()
    
    return available_cameras


def detect_thermal_cameras():
    """Try to detect HT301 thermal cameras"""
    print("\n🌡️ Scanning for thermal cameras...")
    print("=" * 60)
    
    try:
        # Try to import thermal camera libraries
        sys.path.append('./Python_GUI/Python Context HT301 Thermal Stack/ht301_hacklib-master')
        from ht301_hacklib import HT301
        
        print("✅ HT301 library found - attempting thermal camera detection...")
        
        # Try to initialize thermal camera
        try:
            thermal = HT301()
            thermal.start_stream()
            print("✅ HT301 thermal camera detected and operational!")
            
            # Get thermal camera info
            frame = thermal.get_frame()
            if frame is not None:
                print(f"   📐 Thermal resolution: {frame.shape[1]}x{frame.shape[0]}")
                print(f"   🌡️ Temperature range: Configurable")
                print(f"   🎨 Color palettes: Multiple available")
            
            thermal.stop_stream()
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize HT301 thermal camera: {e}")
            return False
            
    except ImportError:
        print("❌ HT301 thermal camera library not found")
        print("   💡 Check: ./Python_GUI/Python Context HT301 Thermal Stack/")
        return False


def main():
    """Main camera detection routine"""
    print("🎥 Camera Detection Utility")
    print("=" * 60)
    print("This tool scans for all available cameras and their capabilities.\n")
    
    # Detect regular cameras
    cameras = detect_all_cameras()
    
    # Detect thermal cameras
    thermal_detected = detect_thermal_cameras()
    
    # Summary
    print(f"\n📊 DETECTION SUMMARY")
    print("=" * 60)
    print(f"🎥 Regular cameras found: {len(cameras)}")
    if thermal_detected:
        print(f"🌡️ Thermal cameras found: 1 (HT301)")
    else:
        print(f"🌡️ Thermal cameras found: 0")
    
    if cameras:
        print(f"\n📋 Camera Index Recommendations:")
        for cam in cameras:
            idx = cam['index']
            props = cam['properties']
            res_count = len(cam['supported_resolutions'])
            print(f"   • Camera {idx}: {props['width']}x{props['height']} @ {props['fps']:.1f}fps ({res_count} resolutions)")
    
    print(f"\n💡 Usage Tips:")
    print(f"   • Use cv2.VideoCapture(index) to access cameras")
    print(f"   • Lower indices (0,1,2) are typically built-in cameras")
    print(f"   • Higher indices are usually external USB cameras")
    print(f"   • Test with different backends if detection fails")
    
    return cameras


if __name__ == "__main__":
    try:
        cameras = main()
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Detection interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during detection: {e}")
        import traceback
        traceback.print_exc()