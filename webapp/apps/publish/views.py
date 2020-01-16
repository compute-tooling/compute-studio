import json
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.core.mail import send_mail

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# from webapp.settings import DEBUG

from webapp.apps.users.models import Project, is_profile_active

from .serializers import PublishSerializer
from .utils import title_fixup


class GetProjectMixin:
    def get_object(self, username, title):
        return get_object_or_404(
            Project, title__iexact=title, owner__user__username__iexact=username
        )


class ProjectView(View):
    template_name = "publish/publish.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)


class ProjectDetailView(GetProjectMixin, View):
    template_name = "publish/publish.html"

    def get(self, request, *args, **kwargs):
        self.get_object(**kwargs)
        return render(request, self.template_name)


class ProjectDetailAPIView(GetProjectMixin, APIView):
    def get(self, request, *args, **kwargs):
        project = self.get_object(**kwargs)
        serializer = PublishSerializer(project)
        data = serializer.data
        return Response(data)

    def put(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            project = self.get_object(**kwargs)
            if project.owner.user == request.user or request.user.has_perm(
                "write_project", project
            ):
                serializer = PublishSerializer(project, data=request.data)
                if serializer.is_valid():
                    model = serializer.save(status="updating")
                    status_url = request.build_absolute_uri(
                        reverse(
                            "userprofile", kwargs={"username": request.user.username}
                        )
                    )
                    try:
                        send_mail(
                            f"{request.user.username} is updating a model on Compute Studio!",
                            (
                                f"{model.title} will be updated or you will have feedback within "
                                f"the next 24 hours. Check the status of the update at "
                                f"{status_url}."
                            ),
                            "hank@compute.studio",
                            list({request.user.email, "hank@compute.studio"}),
                            fail_silently=False,
                        )
                    # Http 401 exception if mail credentials are not set up.
                    except Exception:
                        pass
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_401_UNAUTHORIZED)


class ProjectAPIView(GetProjectMixin, APIView):
    queryset = Project.objects.all()

    def get(self, request, *args, **kwargs):
        ser = PublishSerializer(self.queryset.all(), many=True)
        return Response(ser.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            serializer = PublishSerializer(data=request.POST)
            is_valid = serializer.is_valid()
            if is_valid:
                title = title_fixup(serializer.validated_data["title"])
                username = request.user.username
                if (
                    Project.objects.filter(
                        owner__user__username__iexact=username, title__iexact=title
                    ).count()
                    > 0
                ):
                    return Response(
                        {"project_exists": f"{username}/{title} already exists."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                model = serializer.save(
                    owner=request.user.profile,
                    status="pending",
                    title=title,
                    server_cost=0.1,
                )
                status_url = request.build_absolute_uri(
                    reverse("userprofile", kwargs={"username": request.user.username})
                )
                try:
                    send_mail(
                        f"{request.user.username} is publishing a model on Compute Studio!",
                        (
                            f"{model.title} will be live or you will have feedback within "
                            f"the next 24 hours. Check the status of the submission at "
                            f"{status_url}."
                        ),
                        "hank@compute.studio",
                        list({request.user.email, "hank@compute.studio"}),
                        fail_silently=False,
                    )
                # Http 401 exception if mail credentials are not set up.
                except Exception:
                    pass
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                print("error", request, serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
