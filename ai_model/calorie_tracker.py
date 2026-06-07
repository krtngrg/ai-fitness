CALORIES_PER_REP = {
    "Squat": 0.32,
    "Push-up": 0.29,
    "Jumping Jack": 0.20,
    "Lunge": 0.30,
}

PLANK_CALORIES_PER_SECOND = 0.06


class CalorieTracker:
    def __init__(self):
        self.total_calories = 0.0
        self.last_reps = {}
        self.last_plank_seconds = 0.0

    def reset(self):
        self.total_calories = 0.0
        self.last_reps = {}
        self.last_plank_seconds = 0.0

    def update_by_reps(self, exercise_name, reps):
        previous_reps = self.last_reps.get(exercise_name, reps)
        new_reps = reps - previous_reps

        if new_reps > 0:
            calories_per_rep = CALORIES_PER_REP.get(exercise_name, 0.25)
            self.total_calories += new_reps * calories_per_rep

        self.last_reps[exercise_name] = reps
        return self.total_calories

    def update_plank(self, plank_seconds):
        new_seconds = plank_seconds - self.last_plank_seconds

        if new_seconds > 0:
            self.total_calories += new_seconds * PLANK_CALORIES_PER_SECOND

        self.last_plank_seconds = plank_seconds
        return self.total_calories