# MoveMate AI — Full Stack Fitness App

A local-first AI fitness tracker that uses MediaPipe pose estimation to count reps,
score form, and track calories in real time — running entirely in the browser.

---

## Architecture

Three processes run simultaneously:

| Process | Tech | Port |
|---|---|---|
| Django backend | DRF + SimpleJWT | 8000 |
| FastAPI AI service | uvicorn | 9001 |
| React frontend | Vite | 5173 |

---

## Quick Start

### 1. Python setup (backend + AI service)

```bash
# From project root
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Django backend

```bash
cd backend
python manage.py migrate
python manage.py seed_exercises
python manage.py runserver
```

### 3. FastAPI AI service (Python OpenCV mode)

```bash
# From project root (venv active)
uvicorn ai_model.api_server:app --host 127.0.0.1 --port 9001 --reload
```

### 4. React frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Open in browser

```
http://localhost:5173
```

> Use `localhost`, not `127.0.0.1` — some browsers block camera access on `127.0.0.1`.

---

## Browser Webcam Workout (primary mode)

The app uses **MediaPipe Tasks Vision** running entirely in the browser.
No Python or OpenCV needed for the workout itself.

### How it works

1. User clicks **Start AI Webcam Workout** in the browser
2. React requests camera permission via `getUserMedia`
3. MediaPipe `PoseLandmarker` loads from CDN (first load: 5–10 s)
4. Each video frame is analysed for pose landmarks
5. The canvas renders a mirrored feed + skeleton overlay + HUD
6. Reps, sets, form score, and calories update in real time
7. On completion, results are POST-ed to Django and saved

### Supported exercises

| Slug | Name | Detection method |
|---|---|---|
| `squat` | Squat | Knee + hip angle |
| `push_up` | Push-up | Elbow + body alignment |
| `jumping_jack` | Jumping Jack | Foot ratio + wrist height |
| `plank` | Plank | Body angle timer |
| `lunges` | Lunges | Front knee angle |
| `sit_up` | Sit-up | Hip flexion angle |

### Camera tips

- Stand far enough back that your **full body** is in frame
- Room must be **well-lit** — avoid back-lighting
- Push-ups and planks: use a **side profile** view
- Lunges: face the camera and step **forward**

---

## Browser Webcam Fix (June 7, 2026)

Two bugs caused a black screen on the workout page:

**Bug 1 — "Video element not mounted"**
`LiveWorkout.jsx` used multiple early `return` statements, one per phase
(`idle`, `loading`, `active`). Each return was an independent React tree.
The `<video ref={videoRef}>` only existed in the `active` phase.
When `start()` ran during `loading`, `videoRef.current` was `null`.

**Bug 2 — Black screen after partial fix**
Adding a tiny `<video>` to the loading phase fixed the null error, but
when the phase changed from `loading` → `active`, React unmounted the
old `<video>` and mounted a new one. The `srcObject` (camera stream)
was attached to the old element — the new element was blank.

**Fix applied**
`LiveWorkout.jsx` now uses a **single return** with conditional rendering.
The `<video>` element stays in the DOM for the entire component lifetime.
The loading spinner is rendered as a `position:absolute` overlay on top of
the canvas, not as a separate component tree.
`useWebcamPose.js` also adds `await setTimeout(0)` after `setPhase("loading")`
to let React commit the render before `openCamera()` accesses `videoRef`.

---

## Python CLI mode (standalone testing)

```bash
cd ai_model
python main.py
```

Controls: `q` = quit, `n` = next set

---

## Python packages

```
opencv-python==4.13.0.92
mediapipe==0.10.35
numpy==2.4.6
django==6.0.6
djangorestframework==3.17.1
djangorestframework-simplejwt==5.5.1
django-cors-headers==4.9.0
drf-spectacular==0.29.0
fastapi==0.115.6
uvicorn==0.32.1
```

---

## Database models (summary)

`User` → `UserProfile` → `FitnessGoal` → `Roadmap` → `RoadmapDay`
→ `RoadmapDayExercise` → `WorkoutSession` → `ExerciseLog`
→ `AIModelRun` → `PostureEvent` → `DailyCalorieSummary`

All models use UUID primary keys. Full schema in `backend/fitness/models.py`.

---

## API endpoints (summary)

| Method | URL | Description |
|---|---|---|
| POST | `/api/users/auth/register/` | Register |
| POST | `/api/users/auth/login/` | Login (sets HttpOnly cookies) |
| POST | `/api/users/auth/logout/` | Logout |
| GET | `/api/users/auth/me/` | Current user |
| POST | `/api/fitness/plans/generate/` | Generate AI workout plan |
| GET | `/api/fitness/roadmaps/today/` | Today's workout |
| POST | `/api/fitness/workout-sessions/start/` | Start session |
| POST | `/api/fitness/workout-sessions/{id}/ai-result/` | Save AI result |
| GET | `/api/fitness/dashboard/` | Dashboard summary |

Full Swagger docs: `http://localhost:8000/api/docs/`

---

## Known issues / next steps

- `DailyCalorieSummary` overwrites instead of accumulates on multiple daily sessions
- Access token stored in `localStorage` (needed for AI service Bearer auth — security review needed)
- Sit-up detection needs `analyze_situp()` in `exercise_logic.py`
- Session flow should complete all exercises before saving final result
