"""
Create invoices for previous month's usage.

- Remove stale deployments.
"""
import calendar
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from webapp.apps.users.models import Deployment


class Command(BaseCommand):
    help = "Deletes stale deployments"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--stale-after", type=int, required=False, default=3600)

    def handle(self, *args, **options):
        now = timezone.now()
        for deployment in Deployment.objects.filter(
            status__in=["creating", "running"], deleted_at__isnull=True,
        ):
            load_secs_stale = (now - deployment.last_load_at).seconds
            ping_secs_stale = (now - deployment.last_ping_at).seconds

            secs_stale = min(load_secs_stale, ping_secs_stale)
            if secs_stale > options["stale_after"]:
                print(
                    f"Deleting {deployment.project} {deployment.name} since last use was {secs_stale} "
                    f"(> {options['stale_after']}) seconds ago."
                )
                if not options["dry_run"]:
                    deployment.delete_deployment()
