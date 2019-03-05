from django.core.cache import cache
from django.urls.exceptions import NoReverseMatch

from webapp.apps.users.models import Project


def project_list(request):
    if cache.get("project_list") is None:
        projects = Project.objects.filter(status__in=["live", "updating"])
        project_list = []
        for project in projects:
            try:
                t = (project.profile.user.username, project.name, project.app_url)
                project_list.append(t)
            except NoReverseMatch:
                print(f"No match for {project.name}")
        cache.set("project_list", project_list)
    else:
        project_list = cache.get("project_list")
    return {"project_list": project_list}
