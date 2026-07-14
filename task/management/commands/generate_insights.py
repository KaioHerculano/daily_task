from django.core.management.base import BaseCommand

from task.ai_services import generate_weekly_insights


class Command(BaseCommand):
    help = "Generate weekly study insights."

    def handle(self, *args, **options):
        insights = generate_weekly_insights()
        self.stdout.write(self.style.SUCCESS(f"Generated {len(insights)} insights."))
