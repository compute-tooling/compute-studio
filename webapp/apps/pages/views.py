from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.views import View

from webapp.apps.users.models import Project, Profile, EmbedApproval

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


class LogView(View):
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


class RobotsText(View):
    def get(self, request, *args, **kwargs):
        lines = [
            "User-Agent: *",
        ]

        viz_projects = Project.objects.exclude(
            pk__in=Project.objects.filter(tech="python-paramtools")
        )

        for project in viz_projects:
            lines.append(f"Disallow: /{project}/viz/")

        eas = EmbedApproval.objects.all()

        for ea in eas:
            lines.append(f"Disallow: {ea.get_absolute_url()}")

        return HttpResponse("\n".join(lines), content_type="text/plain")
