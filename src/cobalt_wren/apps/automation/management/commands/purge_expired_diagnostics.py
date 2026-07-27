from django.core.management.base import BaseCommand
from django.utils import timezone
from cobalt_wren.apps.automation.models.diagnostic import DiagnosticPayload

class Command(BaseCommand):
    help = "Delete expired diagnostic payload snapshots."

    def handle(self, *args: object, **options: object) -> None:
        del args, options
        deleted, _ = DiagnosticPayload.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired diagnostic records."))
