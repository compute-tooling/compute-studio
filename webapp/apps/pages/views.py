from django.shortcuts import render, get_object_or_404
from django.views import View

from webapp.apps.users.models import Project, Profile


class HomeView(View):
    profile_template = "profile/home_base.html"
    home_template = "pages/getting_started.html"
    projects = Project.objects.all()

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            profile = request.user.profile
            return render(
                request,
                self.profile_template,
                context={
                    "username": request.user.username,
                    "show_readme": False,
                    "projects": self.projects.filter(owner=profile),
                },
            )
        return render(request, self.home_template)


class ProfileView(View):
    profile_template = "profile/home_base.html"
    projects = Project.objects.all()

    def get(self, request, *args, **kwargs):
        username = kwargs["username"]
        profile = get_object_or_404(Profile, user__username__iexact=username)
        return render(
            request,
            self.profile_template,
            context={
                "username": request.user.username,
                "show_readme": False,
                "projects": self.projects.filter(owner=profile, listed=True),
            },
        )


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
