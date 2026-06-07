from datetime import date, datetime, timedelta

from django.db.models import Avg, Sum
from django.utils import timezone

from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)

from .models import (
    BodyMetric, DailyCalorieSummary, Exercise, ExerciseLog,
    FitnessGoal, AIModelRun, PostureEvent, Roadmap, RoadmapDay,
    RoadmapDayExercise, UserProfile, WorkoutSession,
)
from .serializers import (
    AIWorkoutResultSerializer,
    BodyMetricSerializer,
    ExerciseLogSerializer,
    FitnessGoalSerializer,
    GeneratePlanSerializer,
    RoadmapListSerializer,
    RoadmapSerializer,
    StartWorkoutSessionSerializer,
    UserProfileSerializer,
    WorkoutSessionSerializer,
)
from .services.plan_generator import generate_roadmap_for_goal


# ─── EXISTING VIEWS ───────────────────────────────────────────────────────────

@extend_schema_view(
    get=extend_schema(tags=["Fitness"], summary="Get user profile"),
    put=extend_schema(
        tags=["Fitness"], summary="Update user profile",
        examples=[OpenApiExample("Update Profile", value={"age": 22, "gender": "male", "height_cm": "175.00", "current_weight_kg": "70.00", "activity_level": "moderate"}, request_only=True)],
    ),
    patch=extend_schema(
        tags=["Fitness"], summary="Partially update user profile",
        examples=[OpenApiExample("Patch Profile", value={"current_weight_kg": "69.50", "activity_level": "active"}, request_only=True)],
    ),
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class BodyMetricViewSet(viewsets.ModelViewSet):
    serializer_class = BodyMetricSerializer
    permission_classes = [IsAuthenticated]
    lookup_value_regex = "[0-9a-f-]+"

    def get_queryset(self):
        return BodyMetric.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        metric = serializer.save(user=self.request.user)
        UserProfile.objects.filter(user=self.request.user).update(current_weight_kg=metric.weight_kg)

    def perform_update(self, serializer):
        metric = serializer.save()
        UserProfile.objects.filter(user=self.request.user).update(current_weight_kg=metric.weight_kg)


class FitnessGoalViewSet(viewsets.ModelViewSet):
    serializer_class = FitnessGoalSerializer
    permission_classes = [IsAuthenticated]
    lookup_value_regex = "[0-9a-f-]+"

    def get_queryset(self):
        return FitnessGoal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ─── PLAN GENERATION ──────────────────────────────────────────────────────────

@extend_schema(
    tags=["Plans"],
    summary="Generate AI fitness roadmap",
    description="Creates a FitnessGoal, BodyMetric, Roadmap, RoadmapDays, and RoadmapDayExercises from user input.",
    request=GeneratePlanSerializer,
    responses={201: OpenApiResponse(description="Roadmap generated successfully.")},
    examples=[
        OpenApiExample(
            "Generate Plan",
            value={
                "goal_type": "weight_loss",
                "current_weight_kg": "70.00",
                "target_weight_kg": "60.00",
                "duration_weeks": 8,
                "age": 22,
                "gender": "male",
                "height_cm": "175.00",
                "activity_level": "moderate",
            },
            request_only=True,
        )
    ],
)
class GeneratePlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GeneratePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        today = date.today()
        target_date = today + timedelta(weeks=data["duration_weeks"])

        # Update or create UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.current_weight_kg = data["current_weight_kg"]
        if data.get("age"):
            profile.age = data["age"]
        if data.get("gender"):
            profile.gender = data["gender"]
        if data.get("height_cm"):
            profile.height_cm = data["height_cm"]
        profile.activity_level = data["activity_level"]
        profile.save()

        # Create BodyMetric
        BodyMetric.objects.create(user=request.user, weight_kg=data["current_weight_kg"])

        # Create FitnessGoal
        goal = FitnessGoal.objects.create(
            user=request.user,
            goal_type=data["goal_type"],
            start_weight_kg=data["current_weight_kg"],
            target_weight_kg=data["target_weight_kg"],
            start_date=today,
            target_date=target_date,
            status="active",
        )

        # Generate roadmap
        roadmap = generate_roadmap_for_goal(
            user=request.user,
            goal=goal,
            profile=profile,
            duration_weeks=data["duration_weeks"],
        )

        # Update goal with calorie targets from roadmap
        goal.target_daily_calorie_burn = roadmap.daily_calorie_burn_target
        goal.target_weekly_calorie_burn = roadmap.weekly_calorie_burn_target
        goal.save()

        return Response(
            {
                "message": "Roadmap generated successfully",
                "warning": roadmap.warning_message or "",
                "goal": FitnessGoalSerializer(goal).data,
                "roadmap": RoadmapListSerializer(roadmap).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ─── ROADMAP VIEWS ────────────────────────────────────────────────────────────

class RoadmapViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = "[0-9a-f-]+"

    def get_queryset(self):
        return Roadmap.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return RoadmapListSerializer
        return RoadmapSerializer

    @extend_schema(tags=["Plans"], summary="List roadmaps")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Plans"], summary="Roadmap detail with days and exercises")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


@extend_schema(
    tags=["Plans"],
    summary="Today's workout",
    description="Returns today's RoadmapDay and exercises from the user's active roadmap.",
    responses={200: OpenApiResponse(description="Today's workout day.")},
)
class TodayWorkoutView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = date.today()
        roadmap = Roadmap.objects.filter(user=request.user, status="active").first()
        if not roadmap:
            return Response({"detail": "No active roadmap found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            roadmap_day = roadmap.days.get(workout_date=today)
        except RoadmapDay.DoesNotExist:
            return Response({"detail": "No workout scheduled for today."}, status=status.HTTP_404_NOT_FOUND)

        exercises = []
        for rde in roadmap_day.exercises.select_related("exercise").all():
            exercises.append({
                "roadmap_day_exercise_id": str(rde.id),
                "exercise": rde.exercise.name,
                "exercise_slug": rde.exercise.slug,
                "planned_sets": rde.planned_sets,
                "planned_reps": rde.planned_reps,
                "planned_duration_seconds": rde.planned_duration_seconds,
                "planned_calories": str(rde.planned_calories),
                "has_ai_detection": rde.exercise.has_ai_detection,
                "instructions": rde.instructions,
            })

        return Response({
            "roadmap_day_id": str(roadmap_day.id),
            "day_number": roadmap_day.day_number,
            "week_number": roadmap_day.week_number,
            "focus": roadmap_day.focus,
            "is_rest_day": roadmap_day.is_rest_day,
            "planned_calories": roadmap_day.planned_calories,
            "completed": roadmap_day.completed,
            "exercises": exercises,
        })


# ─── WORKOUT SESSION VIEWS ────────────────────────────────────────────────────

@extend_schema(
    tags=["Sessions"],
    summary="Start a workout session",
    request=StartWorkoutSessionSerializer,
    responses={201: OpenApiResponse(description="Workout session started.")},
    examples=[
        OpenApiExample("Start Session", value={"roadmap_day_id": "uuid-here"}, request_only=True)
    ],
)
class StartWorkoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StartWorkoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        roadmap_day_id = serializer.validated_data["roadmap_day_id"]

        try:
            roadmap_day = RoadmapDay.objects.get(
                id=roadmap_day_id,
                roadmap__user=request.user,
            )
        except RoadmapDay.DoesNotExist:
            return Response({"detail": "Roadmap day not found."}, status=status.HTTP_404_NOT_FOUND)

        session = WorkoutSession.objects.create(
            user=request.user,
            roadmap_day=roadmap_day,
            started_at=timezone.now(),
            source="ai_camera",
        )

        exercise_options = []
        for rde in roadmap_day.exercises.select_related("exercise").all():
            exercise_options.append({
                "roadmap_day_exercise_id": str(rde.id),
                "exercise_slug": rde.exercise.slug,
                "exercise_name": rde.exercise.name,
                "planned_sets": rde.planned_sets,
                "planned_reps": rde.planned_reps,
                "planned_duration_seconds": rde.planned_duration_seconds,
                "planned_calories": str(rde.planned_calories),
                "has_ai_detection": rde.exercise.has_ai_detection,
            })

        return Response(
            {
                "message": "Workout session started",
                "session_id": str(session.id),
                "roadmap_day_id": str(roadmap_day.id),
                "started_at": session.started_at,
                "ai_launch": {"exercise_options": exercise_options},
            },
            status=status.HTTP_201_CREATED,
        )


class WorkoutSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WorkoutSessionSerializer
    permission_classes = [IsAuthenticated]
    lookup_value_regex = "[0-9a-f-]+"

    def get_queryset(self):
        return WorkoutSession.objects.filter(user=self.request.user).prefetch_related(
            "exercise_logs__exercise", "exercise_logs__posture_events"
        )

    @extend_schema(tags=["Sessions"], summary="List workout sessions")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Sessions"], summary="Workout session detail")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


@extend_schema(
    tags=["Sessions"],
    summary="Save AI webcam workout result",
    description="Receives the AI pose-detection result and saves ExerciseLogs, PostureEvents, AIModelRun, and DailyCalorieSummary.",
    request=AIWorkoutResultSerializer,
    responses={200: OpenApiResponse(description="AI workout result saved.")},
    examples=[
        OpenApiExample(
            "AI Result",
            value={
                "model": {
                    "model_name": "MoveMate Pose AI",
                    "model_version": "1.0",
                    "detector_type": "squat_detector",
                    "metadata": {"camera_fps": 30, "model_file": "pose_landmarker_lite.task", "device": "webcam"},
                },
                "session": {
                    "total_duration_seconds": 1200,
                    "total_calories_burned": 180.5,
                    "average_posture_score": 84.2,
                },
                "exercises": [
                    {
                        "exercise_slug": "squat",
                        "actual_sets": 3,
                        "actual_reps": 30,
                        "actual_duration_seconds": 300,
                        "correct_reps": 25,
                        "incorrect_reps": 5,
                        "calories_burned": 45.5,
                        "posture_score": 82.0,
                        "posture_events": [
                            {
                                "timestamp_seconds": 12.5,
                                "issue_type": "knee_caving",
                                "feedback": "Keep your knees aligned with your toes",
                                "posture_score": 70,
                                "landmark_data": {"left_knee_angle": 85, "right_knee_angle": 88},
                            }
                        ],
                    }
                ],
            },
            request_only=True,
        )
    ],
)
class SaveAIWorkoutResultView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = WorkoutSession.objects.get(id=session_id, user=request.user)
        except WorkoutSession.DoesNotExist:
            return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AIWorkoutResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        now = timezone.now()
        model_data = data["model"]
        session_data = data["session"]
        exercises_data = data["exercises"]

        # Create AIModelRun
        ai_run = AIModelRun.objects.create(
            session=session,
            model_name=model_data["model_name"],
            model_version=model_data.get("model_version"),
            detector_type=model_data["detector_type"],
            started_at=session.started_at,
            ended_at=now,
            metadata=model_data.get("metadata", {}),
        )

        # Update WorkoutSession
        session.ended_at = now
        session.total_duration_seconds = session_data["total_duration_seconds"]
        session.total_calories_burned = session_data["total_calories_burned"]
        session.average_posture_score = session_data.get("average_posture_score")
        session.completed = True
        session.save()

        # Process each exercise
        for ex_data in exercises_data:
            slug = ex_data["exercise_slug"]
            try:
                exercise = Exercise.objects.get(slug=slug)
            except Exercise.DoesNotExist:
                return Response(
                    {"detail": f"Exercise with slug '{slug}' not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            rde = None
            rde_id = ex_data.get("roadmap_day_exercise_id")
            planned_reps = None
            planned_calories = None
            if rde_id:
                try:
                    rde = RoadmapDayExercise.objects.get(
                        id=rde_id, roadmap_day__roadmap__user=request.user
                    )
                    planned_reps = rde.planned_reps
                    planned_calories = rde.planned_calories
                except RoadmapDayExercise.DoesNotExist:
                    pass

            actual_reps = ex_data["actual_reps"]
            completed = (planned_reps is not None and actual_reps >= planned_reps) or (
                planned_reps is None and actual_reps > 0
            )

            exercise_log = ExerciseLog.objects.create(
                session=session,
                roadmap_day_exercise=rde,
                exercise=exercise,
                planned_reps=planned_reps,
                actual_sets=ex_data["actual_sets"],
                actual_reps=actual_reps,
                actual_duration_seconds=ex_data["actual_duration_seconds"],
                planned_calories=planned_calories,
                calories_burned=ex_data["calories_burned"],
                posture_score=ex_data.get("posture_score"),
                correct_reps=ex_data["correct_reps"],
                incorrect_reps=ex_data["incorrect_reps"],
                completed=completed,
            )

            # Create PostureEvents
            for event in ex_data.get("posture_events", []):
                PostureEvent.objects.create(
                    ai_run=ai_run,
                    exercise_log=exercise_log,
                    timestamp_seconds=event["timestamp_seconds"],
                    posture_score=event["posture_score"],
                    issue_type=event["issue_type"],
                    feedback=event["feedback"],
                    landmark_data=event.get("landmark_data", {}),
                )

        # Mark RoadmapDay completed
        if session.roadmap_day:
            session.roadmap_day.completed = True
            session.roadmap_day.save()

            # Upsert DailyCalorieSummary
            summary_date = session.started_at.date()
            planned_cal = session.roadmap_day.planned_calories or 0
            DailyCalorieSummary.objects.update_or_create(
                user=request.user,
                summary_date=summary_date,
                defaults={
                    "planned_calories": planned_cal,
                    "actual_calories_burned": session.total_calories_burned,
                    "workout_completed": True,
                },
            )

        return Response(
            {
                "message": "AI workout result saved successfully",
                "session_id": str(session.id),
                "total_calories_burned": str(session.total_calories_burned),
                "average_posture_score": str(session.average_posture_score) if session.average_posture_score else None,
                "completed": session.completed,
            }
        )


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Dashboard"],
    summary="Dashboard summary",
    description="Returns current weight, goal, roadmap, calorie stats, posture score, and workout streak.",
    responses={200: OpenApiResponse(description="Dashboard data.")},
)
class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = date.today()

        profile = UserProfile.objects.filter(user=user).first()
        active_goal = FitnessGoal.objects.filter(user=user, status="active").first()
        active_roadmap = Roadmap.objects.filter(user=user, status="active").first()

        # Today calories
        today_summary = DailyCalorieSummary.objects.filter(user=user, summary_date=today).first()
        today_planned = today_summary.planned_calories if today_summary else 0
        today_actual = float(today_summary.actual_calories_burned) if today_summary else 0

        # Weekly calories (current ISO week Mon-Sun)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        weekly_summaries = DailyCalorieSummary.objects.filter(
            user=user, summary_date__range=[week_start, week_end]
        )
        weekly_planned = weekly_summaries.aggregate(t=Sum("planned_calories"))["t"] or 0
        weekly_actual = float(weekly_summaries.aggregate(t=Sum("actual_calories_burned"))["t"] or 0)

        # Total completed workouts
        total_completed = WorkoutSession.objects.filter(user=user, completed=True).count()

        # Average posture score
        avg_posture = ExerciseLog.objects.filter(
            session__user=user, posture_score__isnull=False
        ).aggregate(avg=Avg("posture_score"))["avg"]
        avg_posture = round(float(avg_posture), 1) if avg_posture else None

        # Workout streak (consecutive days ending today with completed workout)
        streak = 0
        check_date = today
        while True:
            summary = DailyCalorieSummary.objects.filter(
                user=user, summary_date=check_date, workout_completed=True
            ).exists()
            if summary:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        return Response({
            "current_weight_kg": str(profile.current_weight_kg) if profile and profile.current_weight_kg else None,
            "target_weight_kg": str(active_goal.target_weight_kg) if active_goal else None,
            "active_goal": FitnessGoalSerializer(active_goal).data if active_goal else None,
            "active_roadmap": RoadmapListSerializer(active_roadmap).data if active_roadmap else None,
            "today_planned_calories": today_planned,
            "today_actual_calories": today_actual,
            "weekly_planned_calories": weekly_planned,
            "weekly_actual_calories": weekly_actual,
            "total_workouts_completed": total_completed,
            "average_posture_score": avg_posture,
            "workout_streak": streak,
        })
