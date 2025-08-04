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

> **Note** Camera indices are hard-coded in `backend/main.py` as *1 = RGB* and *0 = Thermal* – adjust locally if needed.

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
  - **Bottom Section**: Cold Spray Pattern controls with customizable parameters

### 🔧 **Navigation & Features**
- **Cross-page navigation**: Each page has quick access buttons to other sections
- **Consistent theming**: Sci-fi tactical interface across all pages
- **Keyboard shortcuts**: Context-sensitive controls on each page
- **Robot connection**: Status and controls accessible from all relevant pages
- **Settings**: Global configuration accessible via F1 or CONFIG button

---

## 3 · Road-map Tasks

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

## 4 · Running Locally

### Backend
```bash
cd UnifiedGUI/backend
python -m venv .venv && source .venv/bin/activate  # optional
pip install -r requirements.txt
uvicorn main:app --reload
```
Server boots on `http://127.0.0.1:8000` with:
* `/` – health-check JSON
* `/ws/rgb` – binary JPEG stream
* `/ws/thermal` – binary JPEG stream

### Front-end *(after scaffold)*
```bash
cd UnifiedGUI/frontend
npm install
npm run dev
```
The app will proxy WebSocket calls to `localhost:8000` during dev.

---

## 5 · Style Guidelines
• Dark charcoal background `#101012`  
• Text: off-white `#E0E0E0`  
• Accent: orange `#FFA200` with glow `drop-shadow(0 0 6px #ffa200)`  
• Data overlays use thin geometric lines / dots to match HUD aesthetic.

---

## 6 · Blended Spray Pattern Feature

The application now includes a **Blended Spray Pattern** system for automated material deposition:

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

## 7 · Next Steps
1. Test cold spray functionality with connected robot
2. Add pattern visualization to the views page
3. Implement additional movement patterns
4. Add pattern save/load functionality

---

*Document generated automatically by the project assistant – keep it up-to-date as files evolve.* 