"""
Database updates to migrate project to another cluster.
"""
from django.core.management.base import BaseCommand

from webapp.apps.users.models import Project, Cluster
from webapp.apps.users.serializers import ProjectSerializer


class Command(BaseCommand):
    help = "Migrate project to cluster"

    def add_arguments(self, parser):
        parser.add_argument("--owner")
        parser.add_argument("--title")
        parser.add_argument("--service-account")

    def handle(self, *args, **options):
        cluster = Cluster.objects.get(
            service_account__user__username__iexact=options["service_account"]
        )
        assert cluster.version == "v1"
        project = Project.objects.get(
            owner__user__username__iexact=options["owner"],
            title__iexact=options["title"],
        )
        project.cluster = cluster
        project.save()
        project.assign_role("write", cluster.service_account.user)

        Project.objects.sync_project_with_workers(
            ProjectSerializer(project).data, cluster
        )
