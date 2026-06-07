from dataclasses import dataclass


@dataclass
class MoveMateState:
    exercise: str = "Squat"
    position: str = "UNKNOWN"
    reps: int = 0
    best_depth_angle: float = 999.0
    plank_start_time: float = None
    plank_seconds: float = 0.0
    best_plank_seconds: float = 0.0
    feedback: str = "Stand where your full body is visible."
    form_score: int = 100


def reset_state(exercise):
    return MoveMateState(exercise=exercise)
