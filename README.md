# Embodied Visual Search V1

AI2-THOR online interactive embodied visual search prototype.

V1 scope:

- Environment interaction only
- FastAPI backend + React frontend
- Manual action controls
- Robot RGB view returned from AI2-THOR
- Room view / third-party view kept as interface shell
- Simple agent shell only
- No training
- No VLM API

## Why Linux / WSL2 / Docker

Running AI2-THOR directly on Windows can fail with errors like:

- `Invalid commit_id`
- `no build exists for arch=Windows`

This usually means the required Unity build is not available for the current Windows setup. For a stable V1 demo path, run the backend in Linux, WSL2, or Docker, and access the frontend from the Windows browser.

Recommended setup:

- Backend: WSL2 Ubuntu / native Linux / Docker Linux container
- Frontend: Windows browser or local Node.js

## Project Structure

```text
embodied-visual-search/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── backend/
│   ├── app.py
│   ├── api/
│   ├── envs/
│   ├── agents/
│   ├── actions/
│   ├── memory/
│   ├── schemas/
│   ├── scripts/
│   └── tmp/
├── frontend/
├── data/
└── scripts/
```

## Backend Environment

Recommended:

- Python 3.10 or 3.11
- Linux / WSL2 Ubuntu
- Node.js 18+ for frontend

Install backend dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

WSL2 note:

- Open the project inside the Linux filesystem if possible.
- Avoid relying on native Windows AI2-THOR runtime behavior.

## Minimal AI2-THOR Runtime Validation

Do this first before starting the full backend.

Command:

```bash
python backend/scripts/check_ai2thor_runtime.py
```

What it does:

- Creates `Controller(platform=CloudRendering, scene="FloorPlan212", width=640, height=480)`
- Executes one `RotateRight`
- Saves one RGB frame to `backend/tmp/check_ai2thor_frame.png`

Expected result:

- Console prints success information
- Output image exists at `backend/tmp/check_ai2thor_frame.png`

If this step fails, do not continue to the full project yet. Fix runtime first.

## Environment Variables

Copy `.env.example` to `.env` if needed.

```bash
cp .env.example .env
```

Key settings:

- `AI2THOR_PLATFORM=CloudRendering`
- `AI2THOR_WIDTH=640`
- `AI2THOR_HEIGHT=480`
- `AI2THOR_QUALITY=Low`

## Start Backend

After the minimal runtime check passes:

```bash
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

Backend endpoints:

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

## Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default URL:

- `http://localhost:5173`

If backend runs elsewhere, set:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Demo Flow

1. Run `python backend/scripts/check_ai2thor_runtime.py`.
2. Start backend.
3. Start frontend.
4. Open `http://localhost:5173`.
5. Select `LivingRoom`.
6. Select `FloorPlan211` or `FloorPlan212`.
7. Click `Load Scene`.
8. Confirm robot RGB view appears.
9. Use manual actions like `RotateRight`.
10. Optionally click `Agent Step` to run the shell agent.

## API

- `GET /api/scenes`
- `POST /api/env/load`
- `GET /api/env/observation`
- `POST /api/env/action`
- `POST /api/agent/step`
- `GET /api/trajectory`

Example:

```bash
curl http://localhost:8000/api/scenes
```

```bash
curl -X POST http://localhost:8000/api/env/load \
  -H "Content-Type: application/json" \
  -d '{"scene":"FloorPlan211","task":"Find the sofa"}'
```

## Runtime Troubleshooting

If you still see `Invalid commit_id` or `no build exists`:

1. Try a Linux / WSL2 runtime first. This is the preferred path.
2. Try an AI2-THOR version known to work in your environment, for example testing adjacent releases around your current version such as `4.3.x`, `4.4.x`, or another project-pinned version.
3. If your team already has a Unity build, pass a local executable path through AI2-THOR instead of relying on automatic build resolution.

Typical next checks:

- verify `ai2thor.__version__`
- verify `CloudRendering` is used as a class, not a string
- test with `local_executable_path=...` if you have a local build
- pin a known-good `ai2thor` version in `requirements.txt`

## Current V1 Focus

This prototype intentionally keeps the agent simple:

- `BaseAgent`
- `DummyAgent`

The current goal is to make AI2-THOR environment interaction reliable first. Complex search policies, multimodal reasoning, and long-term memory are out of scope for V1.
