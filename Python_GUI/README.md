# GUI v8 - Dual Camera with Temperature Range Filter

A professional dual-camera GUI application featuring simultaneous RGB and thermal camera display with advanced temperature filtering capabilities.

## 🎯 Purpose

GUI v8 provides **real-time dual camera visualization** for:
- Side-by-side RGB and thermal camera comparison
- Configurable temperature range filtering and analysis
- Professional thermal imaging with min/max detection
- Real-time temperature monitoring and visualization

## 🚀 Features

### **Dual Camera Display**
- **RGB Camera (Left Panel)** - External USB webcam with optimized threading
- **Thermal Camera (Right Panel)** - HT301 thermal camera with enhanced visualization
- **Side-by-Side Layout** - Real-time comparison and analysis
- **Professional Interface** - Clean, responsive GUI design

### **Advanced Thermal Capabilities**
- **HT301 Thermal Camera Integration** - USB connection via IR-Py-Thermal library
- **Live Thermal Display** - Real-time 384x288 thermal imaging at 15 FPS
- **Temperature Range Filtering** - Configurable temperature ranges from main.py
- **Min/Max Detection** - Visual overlay markers for hottest/coldest spots
- **Enhanced Temperature Processing** - Raw ADC to temperature conversion with lookup tables
- **Multiple Colormaps** - JET, HOT, COOL thermal visualization
- **Auto-exposure** - Automatic temperature range optimization for display
- **Manual Calibration** - Shutter-based calibration for accuracy

### **RGB Camera Features**
- **External USB Webcam Support** - Optimized for various webcam models
- **Threading Architecture** - Low-latency capture with dedicated thread
- **Hardware Optimizations** - DirectShow backend, buffer management, MJPG compression
- **High Resolution** - Up to 1920x1080 capture resolution
- **Real-time Display** - 30 FPS RGB video feed

## 📁 Project Structure

```
GUI_v8_fanC/
├── main.py                    # Application entry point with temperature filter config
├── gui_window.py             # Main GUI with dual-camera layout
├── capture_thermal.py        # HT301 thermal camera capture module
├── capture_rgb.py            # RGB camera module with threading
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── Python Context HT301 Thermal Stack/
    └── IR-Py-Thermal-master/ # Enhanced HT301 thermal library
```

## 🛠️ Installation

### Prerequisites
- Python 3.7+
- HT301 thermal camera connected via USB
- External USB webcam
- Windows 10+ (tested platform)

### Dependencies Installation
```bash
pip install -r requirements.txt
```

### Required Packages
- `opencv-python` (4.5.0+) - Computer vision and image processing
- `numpy` (1.20.0+) - Numerical computations
- `PyQt5` (5.15.0+) - GUI framework

## 🚀 Usage

### Quick Start
```bash
cd GUI_v8_fanC
python main.py
```

### Temperature Filter Configuration
Edit the top of `main.py` to control thermal filtering:
```python
ENABLE_TEMP_FILTER = True      # Set to False to show all temperatures
FILTER_TEMP_MIN = 0.0          # Minimum temperature to display (Celsius)
FILTER_TEMP_MAX = 20.0         # Maximum temperature to display (Celsius)
```

### GUI Layout
- **Left Panel** - RGB camera feed with status indicators
- **Right Panel** - Thermal camera with temperature filtering and min/max overlays
- **Enhanced Status** - Real-time temperature data and filter information

### Controls
- **Window Close** - Graceful shutdown of both cameras
- **Auto-refresh** - 30 Hz display update rate
- **Temperature Filtering** - Controlled from main.py configuration

## 🔧 Technical Details

### Camera Specifications
**RGB Camera:**
- **Resolution**: Up to 1920x1080 pixels
- **Frame Rate**: 30 FPS target
- **Interface**: USB via OpenCV DirectShow
- **Threading**: Dedicated capture thread for low latency

**Thermal Camera:**
- **Resolution**: 384x288 pixels
- **Frame Rate**: 15 FPS target
- **Interface**: USB via IR-Py-Thermal library
- **Temperature Range**: Configurable filtering
- **Calibration**: Manual shutter-based calibration support

### Performance Metrics
- **Memory Usage**: ~85-100 MB (dual camera)
- **CPU Usage**: ~15-25% (dual camera operation)
- **Display Latency**: <50ms RGB, <35ms thermal processing
- **Startup Time**: ~3-4 seconds

### Architecture Benefits
- **Dual Camera Synchronization** - Real-time side-by-side comparison
- **Professional Interface** - Clean, responsive GUI design
- **Configurable Filtering** - Easy temperature range adjustment
- **Optimized Performance** - Threading and hardware optimizations

## 🎯 Use Cases

Perfect for applications requiring:
- **Thermal + RGB comparison** (security, inspection, research)
- **Temperature monitoring** with visual context
- **Real-time analysis** with configurable filtering
- **Professional thermal imaging** with enhanced visualization

## 🚧 Current Status

**✅ Working**: Dual camera display, temperature filtering, min/max detection  
**✅ Optimized**: Threading, hardware configurations, performance tuning  
**✅ Professional**: Clean interface, proper shutdown, status indicators

---

**GUI v8 provides a complete dual-camera solution for professional thermal imaging applications.** 