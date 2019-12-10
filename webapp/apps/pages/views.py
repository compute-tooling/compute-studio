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
            return render(
                request,
                self.profile_template,
                context={
                    "username": request.user.username,
                    "runs": profile.sims_breakdown(self.projects),
                    "cost_breakdown": profile.costs_breakdown(self.projects),
                    "show_readme": False,
                },
            )
        return render(request, self.home_template)


class AboutView(View):
    template = "pages/about.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template)


class PrivacyView(View):
    template = "pages/privacy.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template)


class TermsView(View):
    template = "pages/terms.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template)
