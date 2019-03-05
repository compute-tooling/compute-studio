from django.shortcuts import render
from django.views import View

from webapp.apps.users.models import Project


class HomeView(View):
    profile_template = "profile/profile_base.html"
    home_template = "pages/about.html"
    projects = Project.objects.all()

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            profile = request.user.profile
            print(profile.sims(self.projects))
            return render(
                request,
                self.profile_template,
                context={
                    "username": request.user.username,
                    "sims": profile.sims(self.projects),
                    "cost_breakdown": profile.costs(self.projects),
                },
            )
        return render(request, self.home_template)


class AboutView(View):
    template = "pages/about.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template)
