# MoveMate AI — MVP-0 AI Engine

This is the first build step for MoveMate AI.

## Goal

Get the core AI engine working before building React or Django.

This script can:

- Open webcam
- Detect body landmarks with MediaPipe Pose
- Draw skeleton points
- Calculate knee angle
- Calculate hip/back angle
- Detect squat UP/DOWN state
- Count squat reps
- Show basic form feedback

## Install

Use Python 3.10 or 3.11 if possible.

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

Install packages:

```bash
pip install -r requirements.txt
```

## Run

```bash
python squat_detector.py
```

## Controls

- `q` = quit
- `r` = reset rep counter

## Testing Tips

- Put your full body in the camera frame.
- Stand sideways or slightly angled so knees, hips, and ankles are visible.
- Make sure the room is bright.
- If webcam does not open, change `CAMERA_INDEX = 0` to `CAMERA_INDEX = 1`.

## What Success Looks Like

You should see:

- Webcam feed
- Pose skeleton on your body
- Knee angle changing as you squat
- Hip angle changing as you squat
- Position changing between UP and DOWN
- Reps increasing when you complete squats
