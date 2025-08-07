# UnifiedGUI – UR 10e Control & Vision Stack

> All-in-one project combining a FastAPI backend (Python 3.13) and a futuristic Sci-Fi React / TypeScript front-end (Next.js 14 + shadcn UI) to drive a UR 10e robot arm while visualising dual-camera feeds.

---

## 1 · Current Folder Layout  
(*files will grow as we implement each milestone*)

```
UnifiedGUI/
│
├── backend/               # FastAPI service
│   ├── main.py            # Entry-point – RGB & Thermal WS streams & Robot control
│   ├── robot_control.py   # UR 10e control implementation
│   └── requirements.txt   # Python deps
│
└── frontend/              # Next.js 14 (app router)
    ├── src/
    │   ├── app/           # Routes
    │   │   ├── page.tsx           # Home/Navigation page
    │   │   ├── main/page.tsx      # Main dashboard (overview)
    │   │   ├── views/page.tsx     # Camera views & thermal controls
    │   │   └── controls/page.tsx  # Robot control interface
    │   └── components/    # Shared UI (CameraPanel, Settings, etc.)
    ├── tailwind.config.ts # Custom dark + orange sci-fi theme
    ├── package.json       # TS/React deps
    └── next.config.js     # Runtime options
```

> **Note** The backend includes **robust camera initialization** with 3-retry mechanism across multiple indices (RGB: 1,0,2 | Thermal: HT301 then webcam fallback). If cameras fail after 3 attempts, the system continues without them and other APIs remain functional.

---

## 2 · Application Structure

The frontend is now organized into **three distinct pages** for better workflow separation:

### 🏠 **Home Page** (`/`)
- **Purpose**: Navigation hub and automatic redirect to main dashboard
- **Features**: 
  - Quick navigation buttons to all sections
  - Auto-redirects to `/main` by default
  - Clean, minimal interface

### 📊 **Main Dashboard** (`/main`)
- **Purpose**: Overview of all systems with basic controls
- **Features**:
  - Dual camera feeds (RGB + Thermal)
  - System status monitoring
  - Basic thermal controls (filter toggle, palette switching)
  - Robot connection status and basic controls
  - Navigation to specialized pages

### 👁️ **Views Page** (`/views`)
- **Purpose**: Dedicated camera monitoring and thermal analysis
- **Features**:
  - **Larger camera displays** for detailed observation
  - **Full thermal control suite**:
    - Temperature filter toggle and range sliders
    - Color palette cycling
    - Manual calibration controls
    - Real-time temperature readings
  - System status monitoring
  - Keyboard shortcuts (Alt+F, Alt+T, Alt+P, Alt+C)

### 🤖 **Controls Page** (`/controls`)
- **Purpose**: Comprehensive robot control interface
- **Layout**:
  - **Left Half**: SpeedL continuous movement controls
    - Base speed configuration (m/s)
    - Global speed multiplier (0-100%)
    - Large directional buttons (+X, +Y, +Z, -X, -Y, -Z)
    - Emergency stop button
    - Hold-to-move interface with keyboard support (WASD/QE)
  - **Right Half**: Precision fine movement controls
    - TCP (Tool Center Point) configuration
    - Step size definition (mm precision)
    - Velocity and acceleration settings
    - Rotation angle configuration
    - Translation and rotation buttons
    - Keyboard shortcuts (IJKL/UO for translation, RF/TG/YH for rotation)
    - **Save Current as Home**: One-click button to save current joint angles as new home position
    - **Live Robot Position Display**: Real-time display of current robot joint angles with refresh capability
  - **Bottom Section**: Cold Spray Pattern controls with customizable parameters
    - Conical Spray Paths with JSON configuration support
    - Tool Alignment operations
    - Background execution for all spray patterns (cameras remain streaming)

### 🔧 **Navigation & Features**
- **Cross-page navigation**: Each page has quick access buttons to other sections
- **Consistent theming**: Sci-fi tactical interface across all pages
- **Keyboard shortcuts**: Context-sensitive controls on each page
- **Robot connection**: Status and controls accessible from all relevant pages
- **Settings**: Global configuration accessible via F1 or CONFIG button

---

## 3 · System Resilience & Error Handling

### 🔄 **Camera Initialization**
The backend implements a **robust 3-retry mechanism** for camera initialization:

**RGB Camera Retry Strategy:**
1. **Attempt 1-3**: Try camera index 1 at 60fps (high priority)
2. **Fallback 1**: Try camera index 1 at 30fps (high priority)
3. **Fallback 2**: Try camera index 0 at 30fps (normal priority)
4. **Fallback 3**: Try camera index 2 at 30fps (normal priority)
5. **Final State**: If all fail, continue without RGB camera

**Thermal Camera Retry Strategy:**
1. **Attempt 1-3**: Try HT301 thermal camera at 60fps
2. **Fallback 1**: Try HT301 thermal camera at 30fps
3. **Fallback 2**: Try webcam index 2 at 60fps (thermal fallback)
4. **Fallback 3**: Try webcam index 2 at 30fps (thermal fallback)
5. **Final State**: If all fail, continue without thermal camera

### ⚡ **Graceful Degradation**
- **Camera Failures**: WebSocket endpoints gracefully reject connections for failed cameras
- **Robot Unavailable**: All robot APIs return proper error messages when robot controller is not available
- **Partial Systems**: Frontend adapts to show only available camera feeds and controls
- **Status API**: `/api/status` endpoint reports which systems are online

### 🔍 **Startup Monitoring**
The backend provides a detailed startup summary showing:
- ✅/❌ RGB Camera status
- ✅/❌ Thermal Camera status  
- ✅/❌ Robot Controller status
- ✅/⚠️ WebSocket API availability
- ✅/❌ Robot API availability

---

## 4 · Road-map Tasks

| ID | Status | Task |
|----|--------|------|
| backend-skeleton | ✅ in progress | FastAPI server with WS frame endpoints |
| camera-module | ⏳ pending | Extract `CameraStream` into reusable package, add config loading |
| frontend-skeleton | ⏳ pending | Initialise Next.js + Tailwind + shadcn/ui |
| ws-frame-client | ⏳ pending | React hook & component to consume `/ws/rgb` & `/ws/thermal` |
| tailwind-theme | ⏳ pending | Neon/glow dark theme, orange accent (`#FFA200`) |
| camera-panel-component | ⏳ pending | HUD overlays: FPS, resolution, concentric targeting rings |
| robot-endpoints | ⏳ pending | REST & WS endpoints for UR 10e control; 100 Hz loop |

*(see `.todo` list managed by the assistant for live state)*

---

## 4 · Network Access Setup

### 🌐 **Accessing from Other Computers**

The UnifiedGUI backend can be accessed from other computers on the same network:

#### **Quick Setup:**

1. **Start Backend with Network Access:**
   ```bash
   cd UnifiedGUI/backend
   python main.py  # Shows network IP in startup banner
   ```

2. **Note the Network IP** (e.g., `192.168.1.100` shown in banner)

3. **Access from Other Computers:**
   - **Frontend**: `http://YOUR_IP:3000` (if running Next.js dev server with `--host 0.0.0.0`)
   - **Backend API**: `http://YOUR_IP:8000`
   - **Robot Controls**: Access via the frontend URL above

#### **Frontend Network Configuration:**

**Option A - Quick (Current Session Only):**
- Use localhost for development, backend handles CORS for all origins

**Option B - Permanent (Recommended for Production):**
1. Edit `UnifiedGUI/frontend/src/lib/config.ts`
2. Change: `const API_HOST = 'YOUR_NETWORK_IP';`
3. Restart frontend: `npm run dev`

#### **Firewall Configuration:**
- **Windows**: Allow ports 3000 (frontend) and 8000 (backend) through Windows Defender
- **Router**: Ensure computers are on same network/subnet

#### **Example Access:**
```
Primary Computer (Running Services):
├── Backend:  http://192.168.1.100:8000
└── Frontend: http://192.168.1.100:3000

Remote Computer (Accessing):
├── Open browser: http://192.168.1.100:3000
└── Robot controls work automatically via frontend proxy
```

---

## 5 · Running Locally

### Backend

**Local Development:**
```bash
cd UnifiedGUI/backend
python -m venv .venv && source .venv/bin/activate  # optional
pip install -r requirements.txt
uvicorn main:app --reload
```

**Network Access (Recommended):**
```bash
cd UnifiedGUI/backend
python main.py  # Auto-detects network IP and shows access URLs
```

Server provides:
* `/` – health-check JSON
* `/api/status` – system component status
* `/ws/rgb` – binary JPEG stream
* `/ws/thermal` – binary JPEG stream
* `/api/robot/*` – robot control endpoints

### Frontend

**Local Development:**
```bash
cd UnifiedGUI/frontend
npm install
npm run dev
```

**Network Access:**
```bash
cd UnifiedGUI/frontend
npm install
npm run dev:network  # Accessible from other computers on network
```

The app will connect to the backend API automatically.

---

## 5 · Style Guidelines
• Dark charcoal background `#101012`  
• Text: off-white `#E0E0E0`  
• Accent: orange `#FFA200` with glow `drop-shadow(0 0 6px #ffa200)`  
• Data overlays use thin geometric lines / dots to match HUD aesthetic.

---

## 6 · Blended Spray Pattern Feature

The application now includes a **Blended Spray Pattern** system for automated material deposition:

## 7 · Conical Spray Paths Feature

The application includes a **Conical Spray Paths** system based on `spray_test_V2.py` for executing 1-4 conical spray sequences:

### 🧊 **Pattern Overview**
- **Tool Alignment**: 20mm Y translation + 13.5° Y rotation (from testing.py)
- **Blended Spray Pattern**: Forward/reverse cycles with incremental rotation
- **Configurable Parameters**: Acceleration, velocity, blend radius, iterations
- **Movement Scale**: 50mm back-and-forth in Y direction, 1.36° rotation increments
- **Pattern Structure**: 5 forward + 5 reverse cycles per iteration
- **URScript Integration**: Direct robot program execution

### ⚙️ **Parameters**
- **Acceleration**: 0.01-2.0 m/s² (movement acceleration)
- **Velocity**: 0.01-1.0 m/s (movement speed)
- **Blend Radius**: 0.0001-0.01 m (path smoothing)
- **Iterations**: 1-50 cycles (pattern repetitions)

### 🎯 **Quick Presets**
- **Slow & Precise**: Low speed, high accuracy (0.05 m/s, 5 iterations)
- **Standard**: Balanced performance (0.1 m/s, 7 iterations)
- **Fast & Coverage**: High speed, maximum coverage (0.2 m/s, 10 iterations)

### 🔧 **Technical Implementation**
- **Backend**: URScript generation and robot communication
- **Frontend**: Parameter validation and execution status tracking
- **API Endpoints**: 
  - `POST /api/robot/align-tool` - Tool alignment for spray pattern
  - `POST /api/robot/cold-spray` - Execute cold spray pattern
- **Real-time Feedback**: Execution progress and estimated duration
- **Workflow Integration**: Align tool first, then execute pattern

---

## 7 · Conical Spray Paths Feature

The application includes a **Conical Spray Paths** system based on `spray_test_V2.py` for executing 1-4 conical spray sequences:

### 🌀 **Pattern Overview**
- **Conical Motion**: 3D conical sweeps using servoj script execution
- **Multiple Paths**: Support for 1-4 sequential spray paths per execution
- **Configurable Parameters**: Tilt angle, revolutions, cycle time per path
- **Step Calculation**: Always 180 steps × revolutions (matching spray_test_V2)
- **Direct Integration**: Uses robot_functions.conical_motion_servoj_script()

### ⚙️ **Parameters (per path)**
- **Tilt**: Cone angle in degrees (e.g., 10°, 15°)
- **Rev**: Number of revolutions (e.g., 2, 4)
- **Cycle**: Time per step in seconds (e.g., 0.015, 0.0475)

### 📋 **Quick Examples**
- **Single Path**: `[{"tilt": 15, "rev": 2, "cycle": 0.015}]`
- **Dual Path**: `[{"tilt": 15, "rev": 4, "cycle": 0.0475}, {"tilt": 10, "rev": 4, "cycle": 0.0475}]`
- **Quad Path**: Four sequential sweeps with varying parameters

### 🔧 **Technical Implementation**
- **Backend**: Direct integration with robot_functions.py and spray_test_V2 logic
- **Frontend**: JSON text input with validation and example buttons
- **API Endpoints**: 
  - `POST /api/robot/conical-spray` - Execute 1-4 conical spray paths
- **Validation**: JSON format, parameter types, and path count limits
- **Execution**: Sequential path execution with wait_until_idle between sweeps

### 🎯 **Usage Workflow**
1. **Input Paths**: Enter JSON configuration in text area
2. **Validate**: Real-time validation with visual feedback
3. **Execute**: Click execute button to run all paths sequentially
4. **Monitor**: Progress tracking and estimated duration display

---

## 8 · Next Steps
1. Test cold spray functionality with connected robot
2. Add pattern visualization to the views page
3. Implement additional movement patterns
4. Add pattern save/load functionality

---

*Document generated automatically by the project assistant – keep it up-to-date as files evolve.* 