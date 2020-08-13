import json
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.mail import send_mail

from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication,
)

from guardian.shortcuts import assign_perm

# from webapp.settings import DEBUG

from webapp.apps.users.models import Project, is_profile_active
from webapp.apps.users.permissions import StrictRequiresActive, RequiresActive

from webapp.apps.users.serializers import (
    ProjectSerializer,
    ProjectWithVersionSerializer,
    DeploymentSerializer,
)
from .utils import title_fixup

User = get_user_model()


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
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )

    def get(self, request, *args, **kwargs):
        project = self.get_object(**kwargs)
        serializer = ProjectSerializer(project, context={"request": request})
        data = serializer.data
        return Response(data)

    def put(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            project = self.get_object(**kwargs)
            if project.has_write_access(request.user):
                serializer = ProjectSerializer(project, data=request.data)
                if serializer.is_valid():
                    model = serializer.save(status="live")
                    Project.objects.sync_projects_with_workers(
                        ProjectSerializer(Project.objects.all(), many=True).data
                    )
                    status_url = request.build_absolute_uri(model.app_url)
                    try:
                        send_mail(
                            f"{request.user.username} is updating a model on Compute Studio!",
                            (
                                f"{model.title} will be updated or you will have feedback within "
                                f"the next 24 hours. Check the status of the update at "
                                f"{status_url}."
                            ),
                            "notifications@compute.studio",
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
        ser = ProjectSerializer(
            self.queryset.all(), many=True, context={"request": request}
        )
        return Response(ser.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            serializer = ProjectSerializer(
                data=request.POST, context={"request": request}
            )
            is_valid = serializer.is_valid()
            if is_valid:
                title = title_fixup(serializer.validated_data["title"])
                username = request.user.username
                print("creating", title, username)
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
                    owner=request.user.profile, status="pending", title=title,
                )
                status_url = request.build_absolute_uri(model.app_url)
                api_user = User.objects.get(username="comp-api-user")
                assign_perm("write_project", api_user, model)
                Project.objects.sync_products(projects=[model])
                Project.objects.sync_projects_with_workers(
                    ProjectSerializer(Project.objects.all(), many=True).data
                )
                try:
                    send_mail(
                        f"{request.user.username} is publishing a model on Compute Studio!",
                        (
                            f"{model.title} will be live or you will have feedback within "
                            f"the next 24 hours. Check the status of the submission at "
                            f"{status_url}."
                        ),
                        "notifications@compute.studio",
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


class DeploymentAPIView(GetProjectMixin, APIView):
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )

    def get(self, request, *args, **kwargs):
        ser = DeploymentSerializer(
            self.get_object(**kwargs), context={"request": request}
        )
        return Response(ser.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        project = self.get_object(**kwargs)
        if request.user.is_authenticated and project.has_write_access(request.user):
            serializer = DeploymentSerializer(project, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_401_UNAUTHORIZED)


class RecentModelsAPIView(generics.ListAPIView):
    permission_classes = (StrictRequiresActive,)
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    queryset = None
    serializer_class = ProjectSerializer
    n_recent = 7

    def get_queryset(self):
        return self.request.user.profile.recent_models(limit=self.n_recent)


class ModelsAPIView(generics.ListAPIView):
    permission_classes = (StrictRequiresActive,)
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    queryset = Project.objects.all().order_by("-pk")
    serializer_class = ProjectWithVersionSerializer

    def get_queryset(self):
        return self.queryset.filter(owner__user=self.request.user)


class ProfileModelsAPIView(generics.ListAPIView):
    permission_classes = (RequiresActive,)
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    queryset = Project.objects.all().order_by("-pk")
    serializer_class = ProjectWithVersionSerializer

    def get_queryset(self):
        username = self.request.parser_context["kwargs"].get("username", None)
        user = get_object_or_404(get_user_model(), username__iexact=username)
        return self.queryset.filter(owner__user=user, listed=True)
