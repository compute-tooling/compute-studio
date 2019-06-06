from webapp.apps.users.models import Project


def project_list(request):
    projects = Project.objects.filter(listed=True).order_by(
        "owner__user__username", "title"
    )
    project_list = []
    for project in projects:
        project_list.append(
            (project.owner.user.username, project.title, project.app_url)
        )
    return {"project_list": project_list}
