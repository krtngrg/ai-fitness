from datetime import date, timedelta
from decimal import Decimal

from rest_framework import serializers

from .models import (
    UserProfile, BodyMetric, FitnessGoal,
    Exercise, Roadmap, RoadmapDay, RoadmapDayExercise,
    WorkoutSession, ExerciseLog, AIModelRun, PostureEvent, DailyCalorieSummary,
)


# ─── EXISTING ─────────────────────────────────────────────────────────────────

class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        fields = ["id", "email", "age", "gender", "height_cm", "current_weight_kg", "activity_level", "created_at", "updated_at"]
        read_only_fields = ["id", "email", "created_at", "updated_at"]


class BodyMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyMetric
        fields = ["id", "weight_kg", "body_fat_percentage", "waist_cm", "recorded_at"]
        read_only_fields = ["id", "recorded_at"]


class FitnessGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FitnessGoal
        fields = [
            "id", "goal_type", "start_weight_kg", "target_weight_kg",
            "start_date", "target_date", "target_daily_calorie_burn",
            "target_weekly_calorie_burn", "status", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        target_date = attrs.get("target_date")
        if start_date and target_date and target_date <= start_date:
            raise serializers.ValidationError("Target date must be after start date")
        return attrs


# ─── NEW ──────────────────────────────────────────────────────────────────────

class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = [
            "id", "name", "slug", "category", "difficulty",
            "estimated_calories_per_rep", "estimated_calories_per_minute",
            "has_ai_detection",
        ]


class RoadmapDayExerciseSerializer(serializers.ModelSerializer):
    exercise = ExerciseSerializer(read_only=True)

    class Meta:
        model = RoadmapDayExercise
        fields = [
            "id", "exercise", "planned_sets", "planned_reps",
            "planned_duration_seconds", "rest_seconds", "planned_calories",
            "exercise_order", "instructions",
        ]


class RoadmapDaySerializer(serializers.ModelSerializer):
    exercises = RoadmapDayExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = RoadmapDay
        fields = [
            "id", "day_number", "week_number", "workout_date", "focus",
            "planned_duration_minutes", "planned_calories", "is_rest_day",
            "completed", "exercises",
        ]


class RoadmapSerializer(serializers.ModelSerializer):
    days = RoadmapDaySerializer(many=True, read_only=True)

    class Meta:
        model = Roadmap
        fields = [
            "id", "title", "total_weeks", "total_days", "start_date", "end_date",
            "start_weight_kg", "target_weight_kg", "target_weight_loss_kg",
            "estimated_total_calorie_deficit", "daily_calorie_burn_target",
            "weekly_calorie_burn_target", "ai_summary", "warning_message",
            "status", "created_at", "days",
        ]


class RoadmapListSerializer(serializers.ModelSerializer):
    """Lightweight list view — no nested days."""
    class Meta:
        model = Roadmap
        fields = [
            "id", "title", "total_weeks", "total_days", "start_date", "end_date",
            "start_weight_kg", "target_weight_kg", "estimated_total_calorie_deficit",
            "daily_calorie_burn_target",
            "weekly_calorie_burn_target", "ai_summary", "warning_message",
            "status", "created_at",
        ]


# Generate Plan input serializer

class GeneratePlanSerializer(serializers.Serializer):
    goal_type = serializers.ChoiceField(choices=["weight_loss", "muscle_gain", "maintenance", "endurance"])
    current_weight_kg = serializers.DecimalField(max_digits=5, decimal_places=2)
    target_weight_kg = serializers.DecimalField(max_digits=5, decimal_places=2)
    duration_weeks = serializers.IntegerField(min_value=1, max_value=52)
    age = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=["male", "female", "other"], required=False, allow_null=True)
    height_cm = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    activity_level = serializers.ChoiceField(
        choices=["sedentary", "light", "moderate", "active", "very_active"],
        default="moderate",
    )

    def validate(self, attrs):
        if attrs["current_weight_kg"] <= 0:
            raise serializers.ValidationError({"current_weight_kg": "Must be greater than 0."})
        if attrs["target_weight_kg"] <= 0:
            raise serializers.ValidationError({"target_weight_kg": "Must be greater than 0."})
        if attrs["goal_type"] == "weight_loss" and attrs["target_weight_kg"] >= attrs["current_weight_kg"]:
            raise serializers.ValidationError(
                {"target_weight_kg": "For weight loss, target weight must be less than current weight."}
            )
        return attrs


# Workout Session serializers

class StartWorkoutSessionSerializer(serializers.Serializer):
    roadmap_day_id = serializers.UUIDField()


class PostureEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostureEvent
        fields = [
            "id", "timestamp_seconds", "posture_score", "issue_type",
            "feedback", "landmark_data", "created_at",
        ]


class ExerciseLogSerializer(serializers.ModelSerializer):
    exercise = ExerciseSerializer(read_only=True)
    posture_events = PostureEventSerializer(many=True, read_only=True)

    class Meta:
        model = ExerciseLog
        fields = [
            "id", "exercise", "planned_reps", "actual_sets", "actual_reps",
            "actual_duration_seconds", "planned_calories", "calories_burned",
            "posture_score", "correct_reps", "incorrect_reps", "completed",
            "posture_events", "created_at",
        ]


class WorkoutSessionSerializer(serializers.ModelSerializer):
    exercise_logs = ExerciseLogSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutSession
        fields = [
            "id", "roadmap_day", "started_at", "ended_at", "total_duration_seconds",
            "total_calories_burned", "average_posture_score", "completed", "source",
            "exercise_logs", "created_at",
        ]


# AI Result input serializers (nested)

class PostureEventInputSerializer(serializers.Serializer):
    timestamp_seconds = serializers.DecimalField(max_digits=8, decimal_places=3)
    posture_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    issue_type = serializers.CharField(max_length=100)
    feedback = serializers.CharField()
    landmark_data = serializers.DictField(required=False, default=dict)


class ExerciseResultInputSerializer(serializers.Serializer):
    exercise_slug = serializers.SlugField()
    roadmap_day_exercise_id = serializers.UUIDField(required=False, allow_null=True)
    actual_sets = serializers.IntegerField(min_value=0, default=0)
    actual_reps = serializers.IntegerField(min_value=0, default=0)
    actual_duration_seconds = serializers.IntegerField(min_value=0, default=0)
    correct_reps = serializers.IntegerField(min_value=0, default=0)
    incorrect_reps = serializers.IntegerField(min_value=0, default=0)
    calories_burned = serializers.DecimalField(max_digits=6, decimal_places=2, default=0)
    posture_score = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    posture_events = PostureEventInputSerializer(many=True, required=False, default=list)


class AIModelInputSerializer(serializers.Serializer):
    model_name = serializers.CharField(max_length=100)
    model_version = serializers.CharField(max_length=50, required=False, allow_null=True)
    detector_type = serializers.CharField(max_length=50)
    metadata = serializers.DictField(required=False, default=dict)


class AISessionInputSerializer(serializers.Serializer):
    total_duration_seconds = serializers.IntegerField(min_value=0, default=0)
    total_calories_burned = serializers.DecimalField(max_digits=7, decimal_places=2, default=0)
    average_posture_score = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)


class AIWorkoutResultSerializer(serializers.Serializer):
    model = AIModelInputSerializer()
    session = AISessionInputSerializer()
    exercises = ExerciseResultInputSerializer(many=True)
