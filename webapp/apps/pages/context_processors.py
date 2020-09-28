from webapp.apps.users.models import Project, projects_with_access
from webapp.settings import DEBUG


def project_list(request):
    if request is not None:
        user = request.user
    else:
        user = None
    projects = projects_with_access(user, Project.objects.filter(listed=True)).order_by(
        "owner__user__username", "title"
    )
    project_list = []
    for project in projects:
        project_list.append(
            (project.owner.user.username, project.title, project.app_url)
        )
    return {"project_list": project_list, "debug": DEBUG}
