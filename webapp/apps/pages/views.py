from django.shortcuts import render, get_object_or_404, redirect
from django.views import View

from webapp.apps.users.models import Project, Profile

ABOUT_URL = "https://about.compute.studio"


class HomeView(View):
    profile_template = "profile/home_base.html"
    projects = Project.objects.all()

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return render(
                request,
                self.profile_template,
                context={"username": request.user.username, "show_readme": False},
            )
        return redirect(ABOUT_URL)


class ProfileView(View):
    profile_template = "profile/home_base.html"
    projects = Project.objects.all()

    def get(self, request, *args, **kwargs):
        username = kwargs["username"]
        get_object_or_404(Profile, user__username__iexact=username)
        return render(
            request,
            self.profile_template,
            context={"username": request.user.username, "show_readme": False},
        )


class FeedView(View):
    profile_template = "profile/home_base.html"
    projects = Project.objects.all()

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.profile_template,
            context={"username": request.user.username, "show_readme": False},
        )


class AboutView(View):
    def get(self, request, *args, **kwargs):
        return redirect(ABOUT_URL)


class PrivacyView(View):
    template = "pages/privacy.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template)


class TermsView(View):
    template = "pages/terms.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template)


class DMCAView(View):
    template = "pages/dmca.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template)
