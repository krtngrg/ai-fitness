from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserProfileView,
    BodyMetricViewSet,
    FitnessGoalViewSet,
    GeneratePlanView,
    RoadmapViewSet,
    TodayWorkoutView,
    StartWorkoutSessionView,
    WorkoutSessionViewSet,
    SaveAIWorkoutResultView,
    DashboardSummaryView,
)

router = DefaultRouter()
router.register("body-metrics", BodyMetricViewSet, basename="body-metrics")
router.register("goals", FitnessGoalViewSet, basename="goals")
router.register("roadmaps", RoadmapViewSet, basename="roadmaps")
router.register("workout-sessions", WorkoutSessionViewSet, basename="workout-sessions")

urlpatterns = [
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("plans/generate/", GeneratePlanView.as_view(), name="generate-plan"),
    # Must be before router includes to avoid <pk> capturing "today"
    path("roadmaps/today/", TodayWorkoutView.as_view(), name="today-workout"),
    path("workout-sessions/start/", StartWorkoutSessionView.as_view(), name="start-session"),
    path(
        "workout-sessions/<uuid:session_id>/ai-result/",
        SaveAIWorkoutResultView.as_view(),
        name="ai-result",
    ),
    path("dashboard/", DashboardSummaryView.as_view(), name="dashboard"),
    path("", include(router.urls)),
]
