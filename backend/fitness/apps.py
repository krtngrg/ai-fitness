from django.apps import AppConfig


class FitnessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fitness"

    def ready(self):
        import fitness.signals
        self._auto_seed_exercises()

    def _auto_seed_exercises(self):
        """
        Seed the Exercise catalogue on every startup if the table is empty.
        This prevents the plan generator from creating empty roadmap days
        when seed_exercises was never run manually.
        """
        try:
            from django.db import connection
            # Only run if the table actually exists (skip during initial migrate)
            tables = connection.introspection.table_names()
            if "fitness_exercise" not in tables:
                return

            from fitness.models import Exercise
            if Exercise.objects.exists():
                return  # already seeded, nothing to do

            from fitness.management.commands.seed_exercises import EXERCISES
            for data in EXERCISES:
                slug = data["slug"]
                Exercise.objects.update_or_create(
                    slug=slug,
                    defaults=data,
                )
        except Exception:
            pass  # never crash startup due to seeding