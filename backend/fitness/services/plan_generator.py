"""
Generates a full Roadmap with RoadmapDays and RoadmapDayExercises
from a FitnessGoal + UserProfile.
"""
from datetime import date, timedelta
from decimal import Decimal

from ..models import Exercise, Roadmap, RoadmapDay, RoadmapDayExercise
from .calorie_calculator import (
    ACTIVITY_CALORIE_TARGETS,
    calculate_safe_warning,
    calculate_total_calorie_deficit,
    calculate_weight_loss_kg,
    estimate_exercise_calories,
)

# Day focus rotation (7-day cycle, index 0-6)
DAY_FOCUS_CYCLE = [
    "Full Body",   # Day 1
    "Core",        # Day 2
    "Lower Body",  # Day 3
    "Cardio",      # Day 4
    "Upper Body",  # Day 5
    "Full Body",   # Day 6
    "Rest",        # Day 7
]

# exercise_slug, base_sets, base_reps, base_duration_seconds, rest_seconds, is_timed
FOCUS_EXERCISES = {
    "Full Body": [
        ("squat",           3, 10, None, 45, False),
        ("push_up",         3, 8,  None, 45, False),
        ("sit_up",          3, 12, None, 30, False),
        ("plank",           3, None, 30, 30, True),
    ],
    "Core": [
        ("sit_up",          3, 15, None, 30, False),
        ("plank",           3, None, 30, 30, True),
        ("mountain_climber",3, None, 20, 30, True),
    ],
    "Lower Body": [
        ("squat",           4, 10, None, 45, False),
        ("lunges",          3, 10, None, 45, False),
        ("jumping_jack",    3, None, 30, 30, True),
    ],
    "Cardio": [
        ("jumping_jack",    4, None, 45, 30, True),
        ("burpee",          3, 8,  None, 60, False),
        ("mountain_climber",3, None, 30, 30, True),
    ],
    "Upper Body": [
        ("push_up",         4, 8,  None, 45, False),
        ("plank",           3, None, 30, 30, True),
    ],
}

EXERCISE_INSTRUCTIONS = {
    "squat":            "Stand with feet shoulder-width apart. Lower until thighs are parallel to the floor. Keep chest up.",
    "push_up":          "Start in a high plank. Lower chest to the floor keeping body straight. Push back up.",
    "sit_up":           "Lie on your back, knees bent. Curl up to bring torso upright. Lower with control.",
    "plank":            "Hold a forearm or high plank. Keep hips level and core braced. Breathe steadily.",
    "jumping_jack":     "Jump feet out while raising arms overhead. Return to start position. Maintain rhythm.",
    "burpee":           "Squat, kick feet back to a plank, do a push-up, jump feet in, then jump up explosively.",
    "mountain_climber": "Start in a high plank. Drive alternate knees towards chest in a running motion.",
    "lunges":           "Step forward and lower back knee towards the floor. Keep front knee over ankle. Push back up.",
}


def _progressive_reps(base_reps, week_number):
    """Add 2 reps every 2 weeks."""
    if base_reps is None:
        return None
    extra = ((week_number - 1) // 2) * 2
    return base_reps + extra


def _progressive_sets(base_sets, week_number):
    """Add 1 set every 3 weeks."""
    extra = (week_number - 1) // 3
    return base_sets + extra


def _progressive_duration(base_duration, week_number):
    """Add 10 seconds every 2 weeks."""
    if base_duration is None:
        return None
    extra = ((week_number - 1) // 2) * 10
    return base_duration + extra


def generate_roadmap_for_goal(user, goal, profile, duration_weeks):
    """
    Creates and returns a Roadmap with all days and exercises.
    """
    current_weight = profile.current_weight_kg or goal.start_weight_kg
    target_weight = goal.target_weight_kg

    weight_loss_kg = calculate_weight_loss_kg(current_weight, target_weight)
    total_calorie_deficit = calculate_total_calorie_deficit(weight_loss_kg)
    total_days = duration_weeks * 7

    activity_level = profile.activity_level or "moderate"
    daily_burn_target = ACTIVITY_CALORIE_TARGETS.get(activity_level, 500)
    weekly_burn_target = daily_burn_target * 6

    warning = calculate_safe_warning(current_weight, target_weight, duration_weeks)

    ai_summary = (
        f"Plan: Lose {float(weight_loss_kg):.1f} kg in {duration_weeks} weeks. "
        f"Total calorie deficit needed: {int(total_calorie_deficit):,} kcal. "
        f"Daily workout target: {daily_burn_target} kcal burned. "
        f"Activity level: {activity_level}. "
        f"Progressive overload applied — reps and sets increase each week."
    )

    today = date.today()
    end_date = today + timedelta(days=total_days - 1)

    roadmap = Roadmap.objects.create(
        user=user,
        goal=goal,
        title=f"{float(current_weight):.0f} kg to {float(target_weight):.0f} kg Weight Loss Plan",
        total_weeks=duration_weeks,
        total_days=total_days,
        start_date=today,
        end_date=end_date,
        start_weight_kg=current_weight,
        target_weight_kg=target_weight,
        target_weight_loss_kg=weight_loss_kg,
        estimated_total_calorie_deficit=int(total_calorie_deficit),
        daily_calorie_burn_target=daily_burn_target,
        weekly_calorie_burn_target=weekly_burn_target,
        ai_summary=ai_summary,
        warning_message=warning or None,
        status="active",
    )

    # Pre-fetch all exercises by slug once
    exercise_slugs = set()
    for exercises in FOCUS_EXERCISES.values():
        for slug, *_ in exercises:
            exercise_slugs.add(slug)

    exercise_map = {
        ex.slug: ex
        for ex in Exercise.objects.filter(slug__in=exercise_slugs)
    }

    for day_idx in range(total_days):
        day_number = day_idx + 1
        week_number = (day_idx // 7) + 1
        cycle_pos = day_idx % 7
        focus = DAY_FOCUS_CYCLE[cycle_pos]
        is_rest = focus == "Rest"
        workout_date = today + timedelta(days=day_idx)

        planned_calories = 0 if is_rest else daily_burn_target

        roadmap_day = RoadmapDay.objects.create(
            roadmap=roadmap,
            day_number=day_number,
            week_number=week_number,
            workout_date=workout_date,
            focus=focus,
            planned_duration_minutes=0 if is_rest else 35,
            planned_calories=planned_calories,
            is_rest_day=is_rest,
        )

        if is_rest:
            continue

        exercises_for_day = FOCUS_EXERCISES.get(focus, [])
        for order, (slug, base_sets, base_reps, base_dur, rest_sec, is_timed) in enumerate(exercises_for_day, start=1):
            exercise = exercise_map.get(slug)
            if not exercise:
                continue

            sets = _progressive_sets(base_sets, week_number)
            reps = _progressive_reps(base_reps, week_number) if not is_timed else None
            duration_sec = _progressive_duration(base_dur, week_number) if is_timed else None

            cal = estimate_exercise_calories(exercise, reps=reps, duration_seconds=duration_sec)
            total_cal = cal * Decimal(str(sets))

            RoadmapDayExercise.objects.create(
                roadmap_day=roadmap_day,
                exercise=exercise,
                planned_sets=sets,
                planned_reps=reps,
                planned_duration_seconds=duration_sec,
                rest_seconds=rest_sec,
                planned_calories=total_cal,
                exercise_order=order,
                instructions=EXERCISE_INSTRUCTIONS.get(slug, ""),
            )

    return roadmap
