"""
Data migration: Enable has_ai_detection for lunges, jumping_jack, and plank
so they match what the AI model (api_server.py SUPPORTED_SLUGS) actually supports.

AI model supports: squat, push_up, jumping_jack, plank, lunge, lunges
"""
from django.db import migrations


def enable_ai_detection(apps, schema_editor):
    Exercise = apps.get_model("fitness", "Exercise")
    # These slugs are supported by the AI model
    ai_slugs = ["squat", "push_up", "lunges", "jumping_jack", "plank"]
    Exercise.objects.filter(slug__in=ai_slugs).update(has_ai_detection=True)
    # Non-AI exercises
    non_ai_slugs = ["sit_up", "burpee", "mountain_climber"]
    Exercise.objects.filter(slug__in=non_ai_slugs).update(has_ai_detection=False)


def reverse_ai_detection(apps, schema_editor):
    Exercise = apps.get_model("fitness", "Exercise")
    # Revert to original seed state (only squat and push_up were True)
    Exercise.objects.filter(slug__in=["lunges", "jumping_jack", "plank"]).update(has_ai_detection=False)


class Migration(migrations.Migration):

    dependencies = [
        ("fitness", "0003_aimodelrun_exercise_exerciselog_postureevent_roadmap_and_more"),
    ]

    operations = [
        migrations.RunPython(enable_ai_detection, reverse_ai_detection),
    ]
