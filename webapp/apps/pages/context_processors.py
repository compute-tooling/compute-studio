from django.db.models import Max

from webapp.apps.users.models import Project


def project_list(request, limit_recent=2):
    projects = Project.objects.filter(listed=True).order_by(
        "owner__user__username", "title"
    )
    project_list = []
    for project in projects:
        project_list.append(
            (project.owner.user.username, project.title, project.app_url)
        )

    recent_project_list = []
    # if request.user.is_authenticated and getattr(request.user, "profile", False):
    #     recent_sims_by_project = (
    #         request
    #         .user.profile.sims.annotate(recent_creation_date=Max("creation_date")).first(creation_date="recent_creation_date").order_by("-creation_date")
    #     )

    #     for sim in recent_sims_by_project[:limit_recent]:
    #         project = sim.project
    #         recent_project_list.append(
    #             (project.owner.user.username, project.title, project.app_url)
    #         )

    return {"project_list": project_list, "recent_project_list": recent_project_list}
