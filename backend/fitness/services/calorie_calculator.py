"""
Pure calorie and weight-loss calculation helpers.
No Django ORM calls — all functions take plain values.
"""
from decimal import Decimal

CALORIES_PER_KG_FAT = Decimal("7700")


def calculate_weight_loss_kg(current_weight, target_weight):
    return Decimal(str(current_weight)) - Decimal(str(target_weight))


def calculate_total_calorie_deficit(weight_loss_kg):
    return Decimal(str(weight_loss_kg)) * CALORIES_PER_KG_FAT


def calculate_daily_deficit(total_calorie_deficit, total_days):
    if total_days <= 0:
        return Decimal("0")
    return Decimal(str(total_calorie_deficit)) / Decimal(str(total_days))


def calculate_safe_warning(current_weight, target_weight, weeks):
    """Return a warning string if the goal is aggressive, else empty string."""
    if weeks <= 0:
        return ""
    weight_loss = Decimal(str(current_weight)) - Decimal(str(target_weight))
    weekly_loss = weight_loss / Decimal(str(weeks))
    threshold = Decimal(str(current_weight)) * Decimal("0.01")
    if weekly_loss > threshold:
        return (
            f"This goal may be aggressive. You are targeting "
            f"{weekly_loss:.2f} kg/week which exceeds the recommended 1% of "
            f"body weight ({threshold:.2f} kg/week). Consider a slower target "
            f"or combine exercise with safe nutrition guidance. "
            f"Please consult a healthcare professional if needed."
        )
    return ""


def estimate_exercise_calories(exercise, reps=None, duration_seconds=None):
    """Estimate calories burned for one set/interval of an exercise."""
    if reps is not None and reps > 0:
        return Decimal(str(exercise.estimated_calories_per_rep)) * Decimal(str(reps))
    if duration_seconds is not None and duration_seconds > 0:
        return (
            Decimal(str(exercise.estimated_calories_per_minute))
            * Decimal(str(duration_seconds))
            / Decimal("60")
        )
    return Decimal("0")


# Activity level → daily calorie burn target (calories/workout day)
ACTIVITY_CALORIE_TARGETS = {
    "sedentary": 300,
    "light": 375,
    "moderate": 500,
    "active": 600,
    "very_active": 700,
}
