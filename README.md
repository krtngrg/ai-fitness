# MoveMate AI — Full Stack Fitness App with Real-Time Pose Detection

MoveMate AI is a full-stack fitness tracking app that uses **MediaPipe pose estimation** running directly in the browser to count reps, score your form, track calories, and save workout results. You create a personalised AI fitness plan, follow daily workouts, and get live skeleton overlay + feedback while exercising.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Running Without Docker (Local Dev)](#running-without-docker-local-dev)
- [Running With Docker](#running-with-docker)
- [Environment Variables](#environment-variables)
- [Exercises Supported](#exercises-supported)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Known Limitations](#known-limitations)

---

## What It Does

1. Register and create a fitness goal (e.g. "lose 5 kg in 8 weeks")
2. Backend generates a full 8-week workout roadmap with daily exercises
3. Dashboard shows today's workout, calories burned, streak, and form score
4. Click **Start Workout** → pick an exercise → click **Start AI Webcam Workout**
5. Webcam opens in the browser — MediaPipe detects your pose at ~30 fps
6. AI counts reps per set, draws skeleton overlay, shows form score + feedback on canvas
7. After all sets complete, results auto-save to Django
8. Workout Results page shows reps / calories / form score / posture feedback
9. Repeat for each exercise in today's plan

---

## Architecture

```
Browser (port 5173 or 80)
  │
  ├── GET/POST  /api/...  ──────────────► Django backend (port 8000)
  │                                         Auth, plans, sessions, save results
  │
  └── Webcam pose detection
        Runs 100% in the browser via MediaPipe Tasks Vision (WASM)
        No Python or local process needed for the workout itself

Optional: FastAPI AI service (port 9001)
  Legacy Python/OpenCV mode — only needed if running workouts
  via the old local Python window instead of the browser webcam
```

**Three services:**

| Service | Dev port | What it does |
|---|---|---|
| Django backend | 8000 | Auth, fitness plans, saving results, dashboard data |
| React + Vite frontend | 5173 | UI, browser webcam AI workout |
| FastAPI AI service | 9001 | Optional — Python/OpenCV webcam (legacy mode) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, React Router v7, Lucide React |
| Pose detection | MediaPipe Tasks Vision 0.10.35 (WASM, runs in browser) |
| Backend | Django 6, Django REST Framework 3.17 |
| Auth | SimpleJWT — HttpOnly cookie access + refresh tokens |
| API docs | drf-spectacular (Swagger UI at `/api/docs/`) |
| AI service (optional) | FastAPI 0.115, Uvicorn, OpenCV, MediaPipe Python |
| Containerisation | Docker (multi-stage), Docker Compose |
| Database | SQLite (dev) — swap to PostgreSQL for production |
| Web server (prod) | Nginx 1.27 (serves React build, proxies `/api` to Django) |

---

## Prerequisites

### Without Docker
- Python 3.12+
- Node.js 20+
- A webcam

### With Docker
- Docker Desktop (Windows/Mac) or Docker Engine + Docker Compose (Linux)
- A webcam accessible to the browser

---

## Running Without Docker (Local Dev)

This is the recommended way to develop. Three terminals required.

### Step 1 — Python virtual environment

```bash
# From project root
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Step 2 — Django backend

```bash
cd backend

python manage.py migrate
python manage.py seed_exercises
python manage.py runserver
```

Backend runs at **http://localhost:8000**
Swagger docs at **http://localhost:8000/api/docs/**

> First time only: optionally create a superuser for the Django admin panel
> ```bash
> python manage.py createsuperuser
> ```

### Step 3 — React frontend

Open a new terminal:

```bash
cd frontend

npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

> **Important:** always open the app at `localhost:5173` not `127.0.0.1:5173`.
> Some browsers block camera access on `127.0.0.1`. Localhost is required for
> the MediaPipe WASM security headers (COOP/COEP) to work correctly.

### Step 4 — FastAPI AI service (optional)

Only needed if you want to use the old Python/OpenCV local camera window.
The browser webcam workout works without this.

```bash
# From project root (venv active)
uvicorn ai_model.api_server:app --host 127.0.0.1 --port 9001 --reload
```

### Summary — what to open

| URL | What it is |
|---|---|
| http://localhost:5173 | The app |
| http://localhost:8000/api/docs/ | Swagger API docs |
| http://localhost:8000/admin/ | Django admin panel |

---

## Running With Docker

### Development mode (live reload)

```bash
# From project root
docker compose up --build
```

This starts:
- `movemate_backend` on port 8000 (Django dev server, source mounted)
- `movemate_frontend` on port 5173 (Vite dev server, source mounted)

Both containers reload when you edit source files.

The AI service is in the `ai` profile — only start it if you need it:

```bash
docker compose --profile ai up --build
```

Open **http://localhost:5173**

### Production mode

Production uses Gunicorn for Django and Nginx to serve the React build and proxy `/api`.

**Step 1 — Create a `.env` file at the project root:**

```bash
# .env  (never commit this file)
SECRET_KEY=your-very-long-random-secret-key-here
DEBUG=0
DJANGO_ALLOWED_HOSTS=yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com
VITE_API_URL=https://yourdomain.com/api
VITE_AI_SERVICE_URL=https://yourdomain.com:9001
```

**Step 2 — Build and start production containers:**

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Production services:
- Django runs under **Gunicorn** (4 workers)
- React is **pre-built** and served by **Nginx** on port 80
- Nginx proxies `/api/` requests to the Django container
- Static assets cached for 1 year with correct WASM security headers

**Stop production containers:**

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

### Useful Docker commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Run Django management commands inside the container
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_exercises
docker compose exec backend python manage.py createsuperuser

# Rebuild a single service after code changes
docker compose up --build backend

# Stop everything and remove volumes (wipes the database)
docker compose down -v
```

---

## Environment Variables

### Backend — `backend/backend/settings.py`

These can be overridden via environment variables or a `.env` file:

| Variable | Default (dev) | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-...` | Django secret key — **change in production** |
| `DEBUG` | `1` | Set to `0` in production |
| `DJANGO_ALLOWED_HOSTS` | `*` | Comma-separated allowed hosts |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Frontend origin(s) |

### Frontend — `frontend/.env`

Create this file (not committed to git):

```bash
VITE_API_URL=http://localhost:8000/api
VITE_AI_SERVICE_URL=http://localhost:9001
```

In production the Nginx proxy handles `/api/` so `VITE_API_URL` is set at build time via Docker build args.

### JWT cookie settings (`settings.py`)

```python
JWT_COOKIE_SECURE   = False   # set True in production (HTTPS only)
JWT_COOKIE_SAMESITE = "Lax"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS":  True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```

---

## Exercises Supported

All exercises run in the browser with MediaPipe pose detection. No setup required.

| Exercise | Slug | How reps are counted | Camera position |
|---|---|---|---|
| Squat | `squat` | Knee angle: UP > 155° → DOWN < 125° → UP | Front-facing |
| Push-up | `push_up` | Elbow angle + prone position gate | Side view |
| Sit-up | `sit_up` | Torso angle + lying-flat gate + knee-bend gate | Side view |
| Jumping Jack | `jumping_jack` | Foot ratio + wrist height CLOSED↔OPEN | Front-facing |
| Plank | `plank` | 3s countdown → hold timer. Alarm if form breaks | Side view |
| Lunges | `lunges` | Both knees straight → front knee < 115° → back | Front-facing |
| Burpee | `burpee` | Floor position → wrists above shoulders = 1 rep | Front-facing |
| Mountain Climber | `mountain_climber` | Alternating knee drives, L+R = 1 rep | Side view |

### Camera tips

- **Side view exercises** (push-up, sit-up, plank, mountain climber): stand/lie sideways so the camera sees your full body profile
- **Front-facing exercises** (squat, jumping jack, lunge, burpee): face the camera and step back until your full body is in frame
- Room must be **well-lit** — avoid backlighting
- Use **localhost** not 127.0.0.1 in your browser

### Plank behaviour

- Get into plank position → a **3-second countdown** appears on screen
- Once countdown finishes the hold timer starts
- If your form breaks during the hold → **red flash overlay + alarm beep**
- Timer resets and you must hold still for another 3 seconds to restart

---

## API Reference

Full interactive docs at **http://localhost:8000/api/docs/**

### Auth — `/api/users/`

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| POST | `/auth/register/` | No | Create account |
| POST | `/auth/login/` | No | Login — sets `access_token` + `refresh_token` HttpOnly cookies |
| POST | `/auth/logout/` | Yes | Clears cookies, blacklists refresh token |
| GET | `/auth/me/` | Yes | Current user info |
| POST | `/auth/refresh/` | No | Refresh access token using cookie |

### Fitness — `/api/fitness/`

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| GET / PATCH | `/profile/` | Yes | User profile (age, weight, height, activity) |
| POST | `/plans/generate/` | Yes | Generate AI workout roadmap |
| GET | `/roadmaps/` | Yes | List roadmaps |
| GET | `/roadmaps/{id}/` | Yes | Roadmap with all days and exercises |
| GET | `/roadmaps/today/` | Yes | Today's workout day |
| GET | `/dashboard/` | Yes | Calories, streak, posture score, today's plan |
| POST | `/workout-sessions/start/` | Yes | Start session, get exercise list |
| GET | `/workout-sessions/` | Yes | All past sessions |
| GET | `/workout-sessions/{id}/` | Yes | Session detail with logs |
| POST | `/workout-sessions/{id}/ai-result/` | Yes | Save AI workout result |
| GET / POST | `/body-metrics/` | Yes | Weight log |
| GET / POST | `/goals/` | Yes | Fitness goals |

---

## Project Structure

```
AI-Fitness-/
│
├── backend/                        Django project
│   ├── Dockerfile                  Multi-stage: base → development → production
│   ├── requirements.txt            Django, DRF, SimpleJWT, drf-spectacular, gunicorn
│   ├── manage.py
│   ├── backend/
│   │   ├── settings.py             All settings — JWT, CORS, apps
│   │   └── urls.py                 /api/users/, /api/fitness/, /api/docs/
│   ├── users/                      Auth app (email login, JWT cookies)
│   │   ├── models.py               Custom User (email-based, UUID pk)
│   │   ├── authentication.py       CookieJWTAuthentication
│   │   ├── jwt.py                  set_auth_cookies / delete_auth_cookies
│   │   ├── views.py                Register, Login, Logout, Me, Refresh
│   │   └── urls.py
│   └── fitness/                    Main app
│       ├── models.py               10 models — see alltaskdone.txt for full schema
│       ├── serializers.py          All input/output serializers
│       ├── views.py                All API views
│       ├── urls.py
│       ├── signals.py              Auto-creates UserProfile on User save
│       ├── services/
│       │   ├── plan_generator.py   Generates 56-day roadmap
│       │   └── calorie_calculator.py  BMR/TDEE math
│       └── management/commands/
│           └── seed_exercises.py   Seeds 8 exercises into DB
│
├── frontend/                       React + Vite app
│   ├── Dockerfile                  Multi-stage: deps → development → builder → production (Nginx)
│   ├── nginx.conf                  Nginx config — SPA routing, /api proxy, WASM headers
│   ├── vite.config.js              Dev proxy + COOP/COEP security headers for WASM
│   ├── package.json
│   └── src/
│       ├── main.jsx                Entry — BrowserRouter + AuthProvider
│       ├── App.jsx                 All routes
│       ├── api/client.js           Fetch wrappers — auto token refresh on 401
│       ├── context/AuthContext.jsx Global auth state
│       ├── lib/exerciseLogic.js    All pose analysis logic (browser port of Python AI)
│       ├── hooks/useWebcamPose.js  MediaPipe camera hook — RAF loop, canvas drawing
│       ├── components/             DashboardLayout, Sidebar, AuthLayout, etc.
│       └── pages/                  Landing, Login, Register, Dashboard, LiveWorkout, etc.
│
├── ai_model/                       Python AI engine (optional — legacy OpenCV mode)
│   ├── Dockerfile                  Multi-stage: base → development → production
│   ├── requirements_ai.txt         FastAPI, OpenCV, MediaPipe, NumPy
│   ├── api_server.py               FastAPI service (port 9001)
│   ├── workout_runner.py           OpenCV webcam set/rep loop
│   ├── exercise_logic.py           Pose analysis — all 8 exercises
│   ├── drawing.py                  OpenCV UI panels
│   ├── pose_helpers.py             Angle calculation helpers
│   ├── landmarks.py                MediaPipe landmark indices
│   ├── state.py                    MoveMateState dataclass
│   ├── config.py                   Thresholds and camera index
│   └── pose_landmarker_lite.task   MediaPipe model binary (~6 MB)
│
├── docker-compose.yml              Dev compose — backend + frontend + ai (profile)
├── docker-compose.prod.yml         Prod overrides — Gunicorn + Nginx, no source mounts
├── requirements.txt                Full Python deps (for local venv setup)
├── README.md                       This file
└── alltaskdone.txt                 Full developer handoff document
```

---

## Known Limitations

- **SQLite in dev** — not suitable for production concurrent writes. Use PostgreSQL.
- **SECRET_KEY** in settings.py is a placeholder — must be changed before any deployment.
- **Camera permissions** — browser must be opened on `localhost` not `127.0.0.1`.
- **AI service (port 9001)** needs the `pose_landmarker_lite.task` model file — this is ~6 MB binary not committed to git. Download from [MediaPipe Models](https://developers.google.com/mediapipe/solutions/vision/pose_landmarker#models) or copy from the venv cache.
- **Sit-up / push-up** require specific camera angles (side view) — see Exercises table above.
- **DailyCalorieSummary** overwrites instead of accumulating if multiple workouts are saved in one day. Known bug, not yet fixed.
