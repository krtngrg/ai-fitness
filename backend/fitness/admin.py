from django.contrib import admin
from .models import (
    UserProfile, BodyMetric, FitnessGoal,
    Exercise, Roadmap, RoadmapDay, RoadmapDayExercise,
    WorkoutSession, ExerciseLog, AIModelRun, PostureEvent, DailyCalorieSummary,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "age", "gender", "current_weight_kg", "activity_level"]
    search_fields = ["user__email"]


@admin.register(BodyMetric)
class BodyMetricAdmin(admin.ModelAdmin):
    list_display = ["user", "weight_kg", "recorded_at"]
    search_fields = ["user__email"]


@admin.register(FitnessGoal)
class FitnessGoalAdmin(admin.ModelAdmin):
    list_display = ["user", "goal_type", "start_weight_kg", "target_weight_kg", "status", "start_date", "target_date"]
    search_fields = ["user__email"]
    list_filter = ["goal_type", "status"]


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "category", "difficulty", "estimated_calories_per_rep", "has_ai_detection"]
    search_fields = ["name", "slug"]
    list_filter = ["category", "difficulty", "has_ai_detection"]


@admin.register(Roadmap)
class RoadmapAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "total_weeks", "status", "start_date", "end_date"]
    search_fields = ["user__email", "title"]
    list_filter = ["status"]


@admin.register(RoadmapDay)
class RoadmapDayAdmin(admin.ModelAdmin):
    list_display = ["roadmap", "day_number", "week_number", "workout_date", "focus", "is_rest_day", "completed"]
    list_filter = ["focus", "is_rest_day", "completed"]


@admin.register(RoadmapDayExercise)
class RoadmapDayExerciseAdmin(admin.ModelAdmin):
    list_display = ["roadmap_day", "exercise", "planned_sets", "planned_reps", "planned_calories"]
    search_fields = ["exercise__name"]


@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "roadmap_day", "started_at", "total_calories_burned", "completed", "source"]
    search_fields = ["user__email"]
    list_filter = ["completed", "source"]


@admin.register(ExerciseLog)
class ExerciseLogAdmin(admin.ModelAdmin):
    list_display = ["session", "exercise", "actual_reps", "calories_burned", "posture_score", "completed"]
    search_fields = ["exercise__name", "session__user__email"]


@admin.register(AIModelRun)
class AIModelRunAdmin(admin.ModelAdmin):
    list_display = ["session", "model_name", "detector_type", "started_at"]
    search_fields = ["model_name", "detector_type"]


@admin.register(PostureEvent)
class PostureEventAdmin(admin.ModelAdmin):
    list_display = ["ai_run", "issue_type", "posture_score", "timestamp_seconds"]
    list_filter = ["issue_type"]


@admin.register(DailyCalorieSummary)
class DailyCalorieSummaryAdmin(admin.ModelAdmin):
    list_display = ["user", "summary_date", "planned_calories", "actual_calories_burned", "workout_completed"]
    search_fields = ["user__email"]
    list_filter = ["workout_completed"]
