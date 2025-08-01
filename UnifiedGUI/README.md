# UnifiedGUI – UR 10e Control & Vision Stack

> All-in-one project combining a FastAPI backend (Python 3.13) and a futuristic Sci-Fi React / TypeScript front-end (Next.js 14 + shadcn UI) to drive a UR 10e robot arm while visualising dual-camera feeds.

---

## 1 · Current Folder Layout  
(*files will grow as we implement each milestone*)

```
UnifiedGUI/
│
├── backend/               # FastAPI service
│   ├── main.py            # Entry-point – RGB & Thermal WS streams
│   ├── camera/            # Reusable OpenCV capture helpers   (todo)
│   ├── robot/             # UR 10e control adapters           (todo)
│   └── requirements.txt   # Python deps
│
└── frontend/              # Next.js 14 (app router)
    ├── src/
    │   ├── app/           # Routes
    │   └── components/    # Shared UI (CameraPanel, HUD, …)
    ├── tailwind.config.ts # Custom dark + orange sci-fi theme (todo)
    ├── package.json       # TS/React deps
    └── next.config.js     # Runtime options
```

> **Note** Camera indices are hard-coded in `backend/main.py` as *1 = RGB* and *0 = Thermal* – adjust locally if needed.

---

## 2 · Road-map Tasks

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

## 3 · Running Locally

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

## 4 · Style Guidelines
• Dark charcoal background `#101012`  
• Text: off-white `#E0E0E0`  
• Accent: orange `#FFA200` with glow `drop-shadow(0 0 6px #ffa200)`  
• Data overlays use thin geometric lines / dots to match HUD aesthetic.

---

## 5 · Next Steps
1. Scaffold the front-end (`frontend-skeleton`).  
2. Finish camera helper module and FPS measurement.  
3. Land Tailwind theme + CameraPanel.  
4. Integrate initial robot endpoints and control widgets.

---

*Document generated automatically by the project assistant – keep it up-to-date as files evolve.* 