from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.core.mail import send_mail

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from webapp.apps.users.models import Project, is_profile_active

from .serializers import PublishSerializer


class ProjectView(View):
    template_name = "publish/publish.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    @method_decorator(login_required(login_url="/users/login/"))
    @method_decorator(user_passes_test(is_profile_active, login_url="/users/login/"))
    def post(self, request, *args, **kwargs):
        print(request.POST)
        serializer = PublishSerializer(data=request.POST)
        is_valid = serializer.is_valid()
        if is_valid:
            app_name = (
                serializer.validated_data["name"]
                .replace("-", "_")
                .replace(" ", "")
                .lower()
            )
            model = serializer.save(
                profile=request.user.profile, status="pending", app_name=app_name
            )
            status_url = request.build_absolute_uri(
                reverse("userprofile", kwargs={"username": request.user.username})
            )
            send_mail(
                f"{request.user.username} is publishing a model on COMP!",
                (
                    f"{model.name} will be live or you will have feedback within "
                    f"the next 24 hours. Check the status of the submission at "
                    f"{status_url}."
                ),
                "thecompmodels@gmail.com",
                ["henrymdoupe@gmail.com", "thecompmodels@gmail.com"],
                fail_silently=False,
            )
            return redirect(f"/{request.user.username}")
        else:
            print(request)
            print(serializer.errors)
            return render(request, self.template_name, {"errors": serializer.errors})


class ProjectDetailView(View):
    template_name = "publish/publish.html"

    def get_object(self, username, app_name):
        return get_object_or_404(
            Project, name=app_name, profile__user__username=username
        )

    def get(self, request, *args, **kwargs):
        self.get_object(**kwargs)
        return render(request, self.template_name)


class ProjectDetailAPIView(APIView):
    def get_object(self, username, app_name):
        return get_object_or_404(
            Project, name=app_name, profile__user__username=username
        )

    def get(self, request, *args, **kwargs):
        project = self.get_object(**kwargs)
        serializer = PublishSerializer(project)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        print(kwargs)
        project = self.get_object(**kwargs)
        serializer = PublishSerializer(project, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
