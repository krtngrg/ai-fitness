# MoveMate AI — Fitness Tracking App with Webcam Pose Detection

MoveMate AI is a full-stack fitness tracking application that uses **real-time webcam pose detection** to count reps, track form quality, calculate calories burned, and save workout results to a database. The user creates a personalised AI fitness plan, follows the daily workout on the dashboard, and gets live feedback from an OpenCV/MediaPipe camera window while the results are automatically saved.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [User Flow](#user-flow)
- [Setup & Installation](#setup--installation)
- [Running the Project](#running-the-project)
- [Backend API Reference](#backend-api-reference)
- [AI Model](#ai-model)
- [Database Models](#database-models)
- [Frontend Pages](#frontend-pages)
- [Environment Variables](#environment-variables)
- [What Is Already Built](#what-is-already-built)
- [What Can Be Extended Next](#what-can-be-extended-next)
- [AI Prompt for Continuation](#ai-prompt-for-continuation)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User's Machine                           │
│                                                                 │
│  ┌──────────────┐   HTTP/fetch    ┌──────────────────────────┐  │
│  │   React       │ ─────────────► │  Django Backend           │  │
│  │   Vite        │                │  Port 8000                │  │
│  │   Port 5173   │ ◄───────────── │  - JWT auth (HttpOnly)    │  │
│  └──────┬────────┘                │  - Fitness Plans API      │  │
│         │                         │  - Workout Sessions API   │  │
│         │ POST /ai/start-workout   │  - Dashboard API         │  │
│         ▼                         │  - SQLite DB              │  │
│  ┌──────────────┐                 └──────────┬───────────────┘  │
│  │  FastAPI AI   │                            │                  │
│  │  Service      │   POST result JSON         │                  │
│  │  Port 9001    │ ──────────────────────────►│                  │
│  │               │                            │                  │
│  └──────┬────────┘                            │                  │
│         │                                     │                  │
│         ▼  opens local window                 │                  │
│  ┌──────────────┐                             │                  │
│  │  OpenCV +     │                            │                  │
│  │  MediaPipe    │                            │                  │
│  │  Webcam       │                            │                  │
│  └──────────────┘                             │                  │
└─────────────────────────────────────────────────────────────────┘
```

**Three separate processes must run simultaneously:**

| Process | Port | Command |
|---------|------|---------|
| Django backend | 8000 | `python manage.py runserver` |
| FastAPI AI service | 9001 | `uvicorn ai_model.api_server:app --host 127.0.0.1 --port 9001 --reload` |
| React frontend | 5173 | `npm run dev` |

**Data flow when user clicks "Start Local AI Camera":**
1. Frontend POSTs to FastAPI (port 9001) with session_id, exercise_slug, planned_reps, access_token
2. FastAPI calls `workout_runner.run_ai_workout()`
3. OpenCV webcam window opens — user performs exercise
4. AI counts reps per set, shows progress overlay, shows set-complete screens
5. On finish, AI POSTs result JSON to Django (`/api/fitness/workout-sessions/{id}/ai-result/`)
6. Django saves ExerciseLog, AIModelRun, PostureEvents, DailyCalorieSummary
7. FastAPI returns result to browser → browser navigates to `/workout-results`

---

## Tech Stack

### Backend
- **Django 6** + **Django REST Framework 3.17**
- **SimpleJWT** — access + refresh tokens stored in HttpOnly cookies
- **drf-spectacular** — auto-generated Swagger/OpenAPI docs at `/api/docs/`
- **CORS headers** — allows `localhost:5173`
- **SQLite** (dev) — easily swappable to PostgreSQL

### AI Service
- **FastAPI 0.115** + **Uvicorn** — lightweight async API server
- **OpenCV** (`opencv-python`) — webcam capture and frame rendering
- **MediaPipe 0.10** — `PoseLandmarker` task for 33-point body pose detection
- **NumPy** — frame array manipulation

### Frontend
- **React 19** + **Vite 8**
- **React Router DOM v7** — client-side routing
- **Lucide React** — icons
- **fetch API** — all HTTP calls with `credentials: "include"` for cookie auth

---

## Project Structure

```
movemate_mvp0_ai_engine/
│
├── backend/                        # Django project
│   ├── backend/
│   │   ├── settings.py             # Django settings, JWT config, CORS
│   │   └── urls.py                 # Root URLs — /api/users/, /api/fitness/, /api/docs/
│   │
│   ├── users/                      # Auth app
│   │   ├── models.py               # Custom User model (email-based, UUID pk)
│   │   ├── views.py                # Register, Login, Logout, Me, Refresh
│   │   ├── authentication.py       # CookieJWTAuthentication — reads HttpOnly cookie
│   │   ├── jwt.py                  # set_auth_cookies / delete_auth_cookies helpers
│   │   └── urls.py                 # /auth/register/ /login/ /logout/ /me/ /refresh/
│   │
│   ├── fitness/                    # Main fitness app
│   │   ├── models.py               # All 10 models (see Database Models section)
│   │   ├── serializers.py          # Input/output serializers for all APIs
│   │   ├── views.py                # All API views (see Backend API Reference)
│   │   ├── urls.py                 # Fitness URL routes
│   │   ├── admin.py                # Django admin registrations
│   │   ├── services/
│   │   │   ├── plan_generator.py   # Generates Roadmap + RoadmapDays + RoadmapDayExercises
│   │   │   └── calorie_calculator.py # BMR/TDEE calorie math
│   │   └── management/commands/
│   │       └── seed_exercises.py   # Seeds 8 canonical exercises into DB
│   │
│   └── manage.py
│
├── ai_model/                       # Python AI engine
│   ├── api_server.py               # FastAPI service (port 9001) — entry point
│   ├── workout_runner.py           # Core: runs webcam AI for one exercise with sets
│   ├── main.py                     # CLI standalone runner (python main.py)
│   ├── exercise_logic.py           # Pose analysis for each exercise type
│   ├── drawing.py                  # OpenCV UI: panels, progress bars, set-complete screens
│   ├── calorie_tracker.py          # Calorie accumulator (per-rep + plank per-second)
│   ├── pose_landmarker.py          # MediaPipe PoseLandmarker setup
│   ├── pose_helpers.py             # Angle calculation, landmark visibility helpers
│   ├── landmarks.py                # Landmark index constants + skeleton connections
│   ├── state.py                    # MoveMateState dataclass
│   ├── config.py                   # Camera index, model path, exercise thresholds
│   └── pose_landmarker_lite.task   # MediaPipe model file (binary, ~6MB)
│
├── frontend/                       # React + Vite app
│   ├── .env                        # VITE_API_URL, VITE_AI_SERVICE_URL
│   ├── src/
│   │   ├── main.jsx                # Entry — BrowserRouter + AuthProvider
│   │   ├── App.jsx                 # Route definitions
│   │   ├── api/
│   │   │   └── client.js           # All fetch wrappers with cookie auth + auto token refresh
│   │   ├── context/
│   │   │   └── AuthContext.jsx     # Global auth state (user, logout)
│   │   ├── components/
│   │   │   ├── AuthLayout.jsx      # Shared Login/Register form UI
│   │   │   ├── DashboardLayout.jsx # Sidebar + main content wrapper
│   │   │   ├── Sidebar.jsx         # Navigation sidebar
│   │   │   ├── ProtectedRoute.jsx  # Redirects to /login if not authenticated
│   │   │   ├── Navbar.jsx          # Landing page navbar
│   │   │   ├── GoalPlanner.jsx     # Goal planner form component
│   │   │   ├── StatCard.jsx        # Stat display card
│   │   │   └── FeatureCard.jsx     # Landing page feature card
│   │   ├── pages/
│   │   │   ├── Landing.jsx         # Public landing page
│   │   │   ├── Login.jsx           # Login page
│   │   │   ├── Register.jsx        # Register page
│   │   │   ├── Dashboard.jsx       # Main dashboard (stats, today's workout, start button)
│   │   │   ├── GoalPlanner.jsx     # Generate AI fitness plan
│   │   │   ├── ExerciseSelection.jsx  # Pick an exercise from today's workout
│   │   │   ├── LiveWorkout.jsx     # Start AI camera, show status
│   │   │   ├── WorkoutResults.jsx  # Show results after AI workout
│   │   │   ├── WorkoutHistory.jsx  # List all past sessions
│   │   │   └── Profile.jsx         # User profile + body metrics
│   │   └── styles/
│   │       └── global.css          # Dark UI theme, all component styles
│   └── package.json
│
├── venv/                           # Python virtual environment
├── requirements.txt                # opencv-python, mediapipe, numpy
└── README.md
```

---

## User Flow

```
1. Register / Login
         │
         ▼
2. Goal Planner
   - Enter: current weight, target weight, duration, activity level
   - Backend generates:
       FitnessGoal → Roadmap → 56 RoadmapDays → RoadmapDayExercises
   - Each day has exercises with planned sets × reps and estimated calories
         │
         ▼
3. Dashboard
   - Shows: calories burned today, weekly calories, workouts done, streak
   - Shows: Active Plan (title, weekly target)
   - Shows: Today's Workout (Day 3 — Full Body, exercises list)
   - Button: [▶ Start Workout]
         │
         ▼
4. Start Workout → POST /api/fitness/workout-sessions/start/
   - Backend creates WorkoutSession
   - Returns session_id + exercise list
   - Navigate to /exercise-selection
         │
         ▼
5. Exercise Selection
   - Shows all exercises for today
   - Each shows: name, AI badge, planned sets × reps, kcal
   - Click [Start] on any exercise
         │
         ▼
6. Live Workout Page (/live-workout)
   - Shows exercise info and session ID
   - Button: [📷 Start Local AI Camera]
   - Calls POST http://127.0.0.1:9001/ai/start-workout
         │
         ▼
7. OpenCV Webcam Window opens
   - Left panel: exercise name, state badge, rep counter (12/15),
                 rep progress bar, set indicator (SET 2/3 with dots),
                 calories, form score bar, angle metrics
   - Bottom: feedback pill (e.g. "Go lower")
   - When set done → Set Complete overlay → "Press N – Start Set 3"
   - When all sets done → Workout Complete overlay → auto-closes
         │
         ▼
8. AI POSTs result JSON to Django
   POST /api/fitness/workout-sessions/{session_id}/ai-result/
   - Backend saves: WorkoutSession (completed), ExerciseLog,
                    AIModelRun, PostureEvents, DailyCalorieSummary
         │
         ▼
9. Browser navigates to /workout-results
   - Shows: reps, correct/incorrect, calories, form score, feedback
         │
         ▼
10. Dashboard refreshes
    - "Burned Today" now shows actual calories
    - Workout streak increments
    - Workout History shows completed session
```

---

## Setup & Installation

### Prerequisites
- Python 3.12+
- Node.js 20+
- A webcam

### 1. Clone and create venv

```bash
git clone <repo>
cd movemate_mvp0_ai_engine
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Install Python dependencies

```bash
# Core AI deps
pip install opencv-python mediapipe numpy

# Backend deps
pip install django djangorestframework djangorestframework-simplejwt \
            django-cors-headers drf-spectacular

# AI service deps
pip install fastapi uvicorn requests httpx
```

Or install all at once:
```bash
pip install -r requirements.txt
```

### 3. Backend setup

```bash
cd backend
python manage.py migrate
python manage.py seed_exercises     # seeds 8 exercises into DB
python manage.py createsuperuser    # optional: for /admin panel
```

### 4. Frontend setup

```bash
cd frontend
npm install
```

---

## Running the Project

Open **3 terminals**:

```bash
# Terminal 1 — Django backend (port 8000)
cd backend
source ../venv/bin/activate
python manage.py runserver

# Terminal 2 — FastAPI AI service (port 9001)
cd movemate_mvp0_ai_engine   # project root
source venv/bin/activate
uvicorn ai_model.api_server:app --host 127.0.0.1 --port 9001 --reload

# Terminal 3 — React frontend (port 5173)
cd frontend
npm run dev
```

Open browser: **http://localhost:5173**

Swagger API docs: **http://localhost:8000/api/docs/**

---

## Backend API Reference

### Auth — `/api/users/`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register/` | No | Register new user |
| POST | `/auth/login/` | No | Login — sets HttpOnly JWT cookies + returns access token in body |
| POST | `/auth/logout/` | Yes | Clears cookies + blacklists refresh token |
| GET | `/auth/me/` | Yes | Returns current user info |
| POST | `/auth/refresh/` | No | Refreshes access token using refresh cookie |

**Login response** (also sets `access_token` + `refresh_token` HttpOnly cookies):
```json
{
  "message": "Login successful",
  "email": "user@example.com",
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

### Fitness — `/api/fitness/`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET/PUT/PATCH | `/profile/` | Yes | User profile (age, weight, height, activity level) |
| POST | `/plans/generate/` | Yes | Generate AI fitness roadmap |
| GET | `/roadmaps/` | Yes | List user's roadmaps |
| GET | `/roadmaps/{id}/` | Yes | Roadmap detail with all days and exercises |
| GET | `/roadmaps/today/` | Yes | Today's workout day |
| GET | `/dashboard/` | Yes | Dashboard summary (calories, streak, today's workout) |
| POST | `/workout-sessions/start/` | Yes | Create WorkoutSession, get exercise list |
| GET | `/workout-sessions/` | Yes | Workout history |
| GET | `/workout-sessions/{id}/` | Yes | Session detail |
| POST | `/workout-sessions/{id}/ai-result/` | Yes | Save AI workout result |
| GET/POST | `/body-metrics/` | Yes | Weight, body fat logs |
| GET/POST | `/goals/` | Yes | Fitness goals |

### AI Service — `http://127.0.0.1:9001`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/ai/start-workout` | Start webcam AI session |

**POST `/ai/start-workout` request:**
```json
{
  "session_id": "uuid",
  "exercise_slug": "squat",
  "planned_sets": 3,
  "planned_reps": 10,
  "planned_duration_seconds": null,
  "roadmap_day_exercise_id": "uuid",
  "backend_callback_url": "http://127.0.0.1:8000/api/fitness/workout-sessions/{id}/ai-result/",
  "access_token": "eyJ..."
}
```

**POST `/api/fitness/plans/generate/` request:**
```json
{
  "goal_type": "weight_loss",
  "current_weight_kg": "75.00",
  "target_weight_kg": "70.00",
  "duration_weeks": 8,
  "age": 25,
  "gender": "male",
  "height_cm": "175.00",
  "activity_level": "moderate"
}
```

**POST `/api/fitness/workout-sessions/{id}/ai-result/` request:**
```json
{
  "model": {
    "model_name": "MoveMate Pose AI",
    "model_version": "1.0",
    "detector_type": "squat_detector",
    "metadata": {"camera_fps": 30, "model_file": "pose_landmarker_lite.task"}
  },
  "session": {
    "total_duration_seconds": 300,
    "total_calories_burned": 9.6,
    "average_posture_score": 84.0
  },
  "exercises": [
    {
      "exercise_slug": "squat",
      "roadmap_day_exercise_id": "uuid-or-null",
      "actual_sets": 3,
      "actual_reps": 30,
      "actual_duration_seconds": 300,
      "correct_reps": 27,
      "incorrect_reps": 3,
      "calories_burned": 9.6,
      "posture_score": 84.0,
      "posture_events": [
        {
          "timestamp_seconds": 45.2,
          "issue_type": "poor_form",
          "feedback": "Go lower and keep back straight",
          "posture_score": 65,
          "landmark_data": {"Knee angle": 98.5, "Hip angle": 78.3}
        }
      ]
    }
  ]
}
```

---

## AI Model

### Supported Exercises

| Slug | Display Name | Detection Method | Calories |
|------|-------------|-----------------|---------|
| `squat` | Squat | Knee + hip angle | 0.32 kcal/rep |
| `push_up` | Push-up | Elbow angle + body alignment | 0.29 kcal/rep |
| `jumping_jack` | Jumping Jack | Foot width ratio + wrist height | 0.20 kcal/rep |
| `plank` | Plank | Body alignment angle (timed hold) | 0.06 kcal/sec |
| `lunges` | Lunge | Front knee angle + torso | 0.30 kcal/rep |

### How Detection Works

1. **MediaPipe PoseLandmarker** detects 33 body landmarks per frame at ~30fps
2. `pose_helpers.py` calculates joint angles using `calculate_angle(a, b, c)` (returns degrees 0–180)
3. `exercise_logic.py` applies state machine per exercise:
   - Squat: `UP (knee>160°) → DOWN (knee<105°) → UP = +1 rep`
   - Push-up: `UP (elbow>155°) → DOWN (elbow<95°) → UP = +1 rep`
   - Jumping Jack: foot ratio + wrist height transitions CLOSED↔OPEN
   - Plank: body angle > 160° = counting seconds
   - Lunge: both legs straight → front knee < 115° → both straight = +1 rep
4. `calorie_tracker.py` accumulates calories by reps or time
5. Form score = 100 minus deductions for bad angles (capped 0–100)
6. Any rep with `form_score < 70` is logged as a PostureEvent

### Webcam UI (OpenCV window)

```
┌─────────────────────────────────────────┬──────────────────┐
│ MoveMate AI                             │  SET  2 / 3      │
│ ─────────────                           │  ● ● ○           │
│ SQUAT                                   └──────────────────┘
│ [DOWN]                                                      │
│                                                             │
│  12  / 15    4.80                                           │
│  ████████░░  kcal                                           │
│  reps                                                       │
│                                                             │
│  Form  84/100                                               │
│  ████████████░░                                             │
│  Knee°: 112.5                                               │
│  Hip°: 95.2                                                 │
│─────────────────────────────────────────────────────────────│
│              ┌──────────────────────────────┐               │
│              │ Good depth. Push back up.    │               │
│              └──────────────────────────────┘               │
│  Q quit  N next-set  R reset  C calories                    │
└─────────────────────────────────────────────────────────────┘
```

When a set completes → full-screen **Set Complete** overlay with Next button.  
When all sets complete → **Workout Complete** overlay → auto-closes → result saved.

---

## Database Models

```
User (custom, email-based, UUID pk)
  │
  ├── UserProfile        age, height, weight, activity_level
  ├── BodyMetric         weight snapshots over time
  ├── FitnessGoal        goal_type, start/target weight, calorie targets
  │     │
  │     └── Roadmap      title, weeks, daily_calorie_burn_target
  │           │
  │           └── RoadmapDay     day_number, workout_date, focus, planned_calories
  │                 │
  │                 └── RoadmapDayExercise   exercise FK, planned_sets, planned_reps
  │
  ├── WorkoutSession     started_at, total_calories, avg_posture, completed, source
  │     │
  │     ├── ExerciseLog  exercise FK, actual_reps, calories, posture_score, correct/incorrect
  │     │     │
  │     │     └── PostureEvent   timestamp, issue_type, feedback, landmark_data JSON
  │     │
  │     └── AIModelRun   model_name, detector_type, metadata JSON
  │
  ├── DailyCalorieSummary   summary_date (unique per user), planned/actual calories
  │
  └── Exercise           slug, name, category, calories_per_rep, has_ai_detection
```

---

## Frontend Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Landing | Public marketing page |
| `/login` | Login | Email + password login |
| `/register` | Register | Create account |
| `/dashboard` | Dashboard | Stats, active plan, today's workout, Start Workout button |
| `/goal-planner` | GoalPlanner | Generate AI fitness plan form |
| `/exercise-selection` | ExerciseSelection | Pick exercise from today's plan |
| `/live-workout` | LiveWorkout | Start AI camera, show running/done status |
| `/workout-results` | WorkoutResults | Show reps, calories, form score, feedback |
| `/workout-history` | WorkoutHistory | All past sessions with expandable exercise logs |
| `/profile` | Profile | Update weight, height, activity level |

### Auth
- JWT stored in **HttpOnly cookies** (no localStorage for tokens)
- `client.js` auto-retries on 401 with a token refresh call
- `ProtectedRoute` redirects unauthenticated users to `/login`
- `AuthContext` provides `{ user, setUser, logout }` globally

---

## Environment Variables

**`frontend/.env`**
```
VITE_API_URL=http://127.0.0.1:8000/api
VITE_AI_SERVICE_URL=http://127.0.0.1:9001
```

**`backend/backend/settings.py`** (key settings)
```python
JWT_COOKIE_ACCESS = "access_token"
JWT_COOKIE_REFRESH = "refresh_token"
JWT_COOKIE_SECURE = False          # True in production (HTTPS)
JWT_COOKIE_SAMESITE = "Lax"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
```

---

## What Is Already Built

- ✅ Custom email-based User auth with JWT HttpOnly cookies
- ✅ Auto token refresh on 401 in frontend
- ✅ User profile + body metrics tracking
- ✅ AI-generated fitness roadmap (8-week plan, 56 days, exercises per day)
- ✅ Dashboard with calories burned today/this week, streak, posture score
- ✅ Today's workout display with exercise list
- ✅ Start Workout → creates session → exercise selection flow
- ✅ FastAPI AI service runs as separate local process (port 9001)
- ✅ OpenCV webcam AI with real-time pose detection
- ✅ 5 exercises detected: Squat, Push-up, Jumping Jack, Plank, Lunge
- ✅ Set-by-set tracking: rep counter per set, progress bar, set indicator dots
- ✅ Set Complete overlay screen between sets (press N for next set)
- ✅ All Sets Done overlay screen (auto-closes, saves result)
- ✅ Form score, posture events with landmark angles logged per rep
- ✅ AI result automatically POSTed to Django after workout
- ✅ WorkoutSession, ExerciseLog, AIModelRun, PostureEvent, DailyCalorieSummary all saved
- ✅ WorkoutResults page shows reps/calories/form/feedback
- ✅ WorkoutHistory page shows all sessions with exercise logs
- ✅ Swagger UI at `/api/docs/` with full request examples
- ✅ Dark UI theme throughout

---

## What Can Be Extended Next

### High Priority
- **Sit-up detection** — add `analyze_situp()` in `exercise_logic.py` (torso angle)
- **Browser webcam** — replace OpenCV with WebRTC + TensorFlow.js PoseNet so no local Python window needed
- **Push notifications** — remind user when it's workout time
- **Multiple exercises per session** — loop through all exercises in one go

### Medium Priority
- **PostgreSQL** — replace SQLite with Postgres for production
- **Progress charts** — line charts for weight loss, weekly calories (use recharts)
- **Rest timer** — countdown between sets inside the webcam window
- **Voice feedback** — use `pyttsx3` to speak form feedback aloud during workout
- **Export workout PDF** — generate a PDF summary of completed workout

### Lower Priority
- **Social features** — share workout results
- **Custom plan editor** — let user modify AI-generated plan
- **Mobile app** — React Native wrapper
- **HTTPS + production deploy** — Nginx + Gunicorn + SSL

---

## AI Prompt for Continuation

Use this prompt to give to another AI to continue development:

```
You are a senior full-stack developer continuing work on MoveMate AI — 
a fitness app with real-time webcam pose detection.

ARCHITECTURE:
- Django 6 backend (port 8000) with DRF + SimpleJWT HttpOnly cookie auth
- FastAPI AI service (port 9001) that runs OpenCV/MediaPipe in a local window
- React 19 + Vite frontend (port 5173)

DATA FLOW:
Frontend → POST /api/fitness/workout-sessions/start/ → get session_id + exercises
Frontend → POST http://127.0.0.1:9001/ai/start-workout → opens webcam window
AI runs set-by-set tracking → on finish → POSTs result to Django callback URL
Django saves: WorkoutSession, ExerciseLog, AIModelRun, PostureEvent, DailyCalorieSummary
Frontend → navigate to /workout-results with AI result

KEY FILES:
- ai_model/workout_runner.py     — run_ai_workout() function, set/rep loop
- ai_model/drawing.py            — draw_info_panel(), draw_set_complete_screen(), draw_all_sets_done_screen()
- ai_model/exercise_logic.py     — analyze_squat/pushup/jumping_jack/plank/lunge()
- ai_model/api_server.py         — FastAPI POST /ai/start-workout
- backend/fitness/models.py      — all 10 DB models
- backend/fitness/views.py       — all API views including SaveAIWorkoutResultView
- backend/fitness/serializers.py — AIWorkoutResultSerializer (nested input)
- frontend/src/api/client.js     — all fetch wrappers with auto token refresh
- frontend/src/pages/Dashboard.jsx        — handleStartWorkout → navigate to /exercise-selection
- frontend/src/pages/ExerciseSelection.jsx — pick exercise → navigate to /live-workout
- frontend/src/pages/LiveWorkout.jsx      — calls FastAPI, shows status
- frontend/src/pages/WorkoutResults.jsx  — shows reps/calories/form/feedback

EXERCISE SLUGS (must match DB):
squat, push_up, jumping_jack, plank, lunges, sit_up, burpee, mountain_climber

EXISTING EXERCISE DETECTION (exercise_logic.py):
squat → knee angle state machine (UP > 160°, DOWN < 105°)
push_up → elbow angle (UP > 155°, DOWN < 95°)
jumping_jack → foot ratio + wrist height CLOSED/OPEN states
plank → body angle > 160° starts timer
lunge → both knees straight → front knee < 115° → back to straight

AUTH:
- Backend: CookieJWTAuthentication reads 'access_token' HttpOnly cookie
- Bearer token also supported (for AI service callback)
- Frontend auto-refreshes on 401 via /api/users/auth/refresh/
- access_token also stored in localStorage for AI service to use as Bearer

WHAT STILL NEEDS BUILDING:
[describe your specific task here]
```

---

## Quick Test Flow

```bash
# 1. Start all 3 services (see Running the Project above)

# 2. Open http://localhost:5173
# 3. Register: POST /api/users/auth/register/
#    { "email": "test@test.com", "password": "Test1234!", "name": "Test User" }

# 4. Generate plan: Goal Planner page
#    { current_weight: 75, target_weight: 70, duration_weeks: 8, activity_level: "moderate" }

# 5. Dashboard → click "Start Workout"
# 6. Exercise Selection → click "Start" on Squat
# 7. Live Workout → click "Start Local AI Camera"
# 8. OpenCV window opens → do squats → press Q or complete all sets
# 9. Results page shows your stats
# 10. Dashboard shows updated "Burned Today" calories
# 11. Workout History shows the completed session
```
