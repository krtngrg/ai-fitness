import uuid
from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    ACTIVITY_LEVEL_CHOICES = [
        ("sedentary", "Sedentary"),
        ("light", "Light"),
        ("moderate", "Moderate"),
        ("active", "Active"),
        ("very_active", "Very Active"),
    ]

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    current_weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    activity_level = models.CharField(max_length=50, choices=ACTIVITY_LEVEL_CHOICES, default="sedentary")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile - {self.user.email}"


class BodyMetric(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="body_metrics"
    )
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    body_fat_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    waist_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.user.email} - {self.weight_kg} kg"


class FitnessGoal(models.Model):
    GOAL_TYPE_CHOICES = [
        ("weight_loss", "Weight Loss"),
        ("muscle_gain", "Muscle Gain"),
        ("maintenance", "Maintenance"),
        ("endurance", "Endurance"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fitness_goals"
    )
    goal_type = models.CharField(max_length=50, choices=GOAL_TYPE_CHOICES)
    start_weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    target_weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    start_date = models.DateField()
    target_date = models.DateField()
    target_daily_calorie_burn = models.PositiveIntegerField(null=True, blank=True)
    target_weekly_calorie_burn = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.goal_type}"


# ─── NEW MODELS ───────────────────────────────────────────────────────────────

class Exercise(models.Model):
    CATEGORY_CHOICES = [
        ("strength", "Strength"),
        ("cardio", "Cardio"),
        ("core", "Core"),
        ("mobility", "Mobility"),
    ]
    DIFFICULTY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    difficulty = models.CharField(max_length=50, choices=DIFFICULTY_CHOICES, default="beginner")
    estimated_calories_per_rep = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    estimated_calories_per_minute = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    has_ai_detection = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Roadmap(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="roadmaps"
    )
    goal = models.ForeignKey(FitnessGoal, on_delete=models.CASCADE, related_name="roadmaps")
    title = models.CharField(max_length=255)
    total_weeks = models.PositiveIntegerField()
    total_days = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    start_weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    target_weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    target_weight_loss_kg = models.DecimalField(max_digits=5, decimal_places=2)
    estimated_total_calorie_deficit = models.IntegerField()
    daily_calorie_burn_target = models.IntegerField()
    weekly_calorie_burn_target = models.IntegerField()
    ai_summary = models.TextField()
    warning_message = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class RoadmapDay(models.Model):
    FOCUS_CHOICES = [
        ("Full Body", "Full Body"),
        ("Core", "Core"),
        ("Lower Body", "Lower Body"),
        ("Upper Body", "Upper Body"),
        ("Cardio", "Cardio"),
        ("Rest", "Rest"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="days")
    day_number = models.PositiveIntegerField()
    week_number = models.PositiveIntegerField()
    workout_date = models.DateField()
    focus = models.CharField(max_length=50, choices=FOCUS_CHOICES)
    planned_duration_minutes = models.PositiveIntegerField(default=30)
    planned_calories = models.PositiveIntegerField(default=0)
    is_rest_day = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["day_number"]
        unique_together = [["roadmap", "day_number"]]

    def __str__(self):
        return f"Day {self.day_number} - {self.focus}"


class RoadmapDayExercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    roadmap_day = models.ForeignKey(RoadmapDay, on_delete=models.CASCADE, related_name="exercises")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    planned_sets = models.PositiveIntegerField()
    planned_reps = models.PositiveIntegerField(null=True, blank=True)
    planned_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    rest_seconds = models.PositiveIntegerField(default=30)
    planned_calories = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    exercise_order = models.PositiveIntegerField(default=1)
    instructions = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["exercise_order"]

    def __str__(self):
        return f"{self.roadmap_day} - {self.exercise.name}"


class WorkoutSession(models.Model):
    SOURCE_CHOICES = [
        ("ai_camera", "AI Camera"),
        ("manual", "Manual"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workout_sessions"
    )
    roadmap_day = models.ForeignKey(RoadmapDay, on_delete=models.SET_NULL, null=True, blank=True, related_name="sessions")
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    total_duration_seconds = models.PositiveIntegerField(default=0)
    total_calories_burned = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    average_posture_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    completed = models.BooleanField(default=False)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="ai_camera")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.started_at.date()}"


class ExerciseLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name="exercise_logs")
    roadmap_day_exercise = models.ForeignKey(
        RoadmapDayExercise, on_delete=models.SET_NULL, null=True, blank=True
    )
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    planned_reps = models.PositiveIntegerField(null=True, blank=True)
    actual_sets = models.PositiveIntegerField(default=0)
    actual_reps = models.PositiveIntegerField(default=0)
    actual_duration_seconds = models.PositiveIntegerField(default=0)
    planned_calories = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    calories_burned = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    posture_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    correct_reps = models.PositiveIntegerField(default=0)
    incorrect_reps = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.exercise.name} - {self.session}"


class AIModelRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name="ai_runs")
    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=50, null=True, blank=True)
    detector_type = models.CharField(max_length=50)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.model_name} - {self.session}"


class PostureEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ai_run = models.ForeignKey(AIModelRun, on_delete=models.CASCADE, related_name="posture_events")
    exercise_log = models.ForeignKey(
        ExerciseLog, on_delete=models.SET_NULL, null=True, blank=True, related_name="posture_events"
    )
    timestamp_seconds = models.DecimalField(max_digits=8, decimal_places=3)
    posture_score = models.DecimalField(max_digits=5, decimal_places=2)
    issue_type = models.CharField(max_length=100)
    feedback = models.TextField()
    landmark_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.issue_type} at {self.timestamp_seconds}s"


class DailyCalorieSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_calorie_summaries"
    )
    summary_date = models.DateField()
    planned_calories = models.PositiveIntegerField(default=0)
    actual_calories_burned = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    workout_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["user", "summary_date"]]
        ordering = ["-summary_date"]

    def __str__(self):
        return f"{self.user.email} - {self.summary_date}"
