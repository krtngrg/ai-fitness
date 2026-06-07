from django.core.management.base import BaseCommand
from fitness.models import Exercise

EXERCISES = [
    {
        "name": "Squat",
        "slug": "squat",
        "category": "strength",
        "difficulty": "beginner",
        "estimated_calories_per_rep": "0.320",
        "estimated_calories_per_minute": "5.00",
        "has_ai_detection": True,
    },
    {
        "name": "Push Up",
        "slug": "push_up",
        "category": "strength",
        "difficulty": "beginner",
        "estimated_calories_per_rep": "0.290",
        "estimated_calories_per_minute": "6.00",
        "has_ai_detection": True,
    },
    {
        "name": "Sit Up",
        "slug": "sit_up",
        "category": "core",
        "difficulty": "beginner",
        "estimated_calories_per_rep": "0.250",
        "estimated_calories_per_minute": "5.00",
        "has_ai_detection": False,
    },
    {
        "name": "Plank",
        "slug": "plank",
        "category": "core",
        "difficulty": "beginner",
        "estimated_calories_per_rep": "0.000",
        "estimated_calories_per_minute": "4.00",
        "has_ai_detection": False,
    },
    {
        "name": "Jumping Jack",
        "slug": "jumping_jack",
        "category": "cardio",
        "difficulty": "beginner",
        "estimated_calories_per_rep": "0.200",
        "estimated_calories_per_minute": "8.00",
        "has_ai_detection": False,
    },
    {
        "name": "Burpee",
        "slug": "burpee",
        "category": "cardio",
        "difficulty": "intermediate",
        "estimated_calories_per_rep": "0.500",
        "estimated_calories_per_minute": "10.00",
        "has_ai_detection": False,
    },
    {
        "name": "Mountain Climber",
        "slug": "mountain_climber",
        "category": "cardio",
        "difficulty": "beginner",
        "estimated_calories_per_rep": "0.180",
        "estimated_calories_per_minute": "8.00",
        "has_ai_detection": False,
    },
    {
        "name": "Lunges",
        "slug": "lunges",
        "category": "strength",
        "difficulty": "beginner",
        "estimated_calories_per_rep": "0.300",
        "estimated_calories_per_minute": "5.50",
        "has_ai_detection": False,
    },
]


class Command(BaseCommand):
    help = "Seeds the Exercise catalogue with the 8 canonical exercises."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for data in EXERCISES:
            slug = data.pop("slug")
            obj, created = Exercise.objects.update_or_create(
                slug=slug,
                defaults={"slug": slug, **data},
            )
            data["slug"] = slug  # restore for next run safety

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  Created: {obj.name}"))
            else:
                updated_count += 1
                self.stdout.write(f"  Updated: {obj.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {created_count} created, {updated_count} updated."
            )
        )
