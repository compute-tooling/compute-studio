import json
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.mail import send_mail
from django.http import Http404
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.exceptions import PermissionDenied as APIPermissionDenied
from rest_framework import filters


# from webapp.settings import DEBUG

from webapp.settings import USE_STRIPE
from webapp.apps.users.models import (
    Project,
    Cluster,
    Deployment,
    EmbedApproval,
    Tag,
    is_profile_active,
    get_project_or_404,
    projects_with_access,
)
from webapp.apps.users.permissions import StrictRequiresActive, RequiresActive

from webapp.apps.users.serializers import (
    ProjectSerializer,
    ProjectWithVersionSerializer,
    TagSerializer,
    TagUpdateSerializer,
    EmbedApprovalSerializer,
    DeploymentSerializer,
)
from .utils import title_fixup

User = get_user_model()


class GetProjectMixin:
    def get_object(self, username, title, **kwargs):
        print(self.request.user, username, title)
        return get_project_or_404(
            Project.objects.all(),
            user=self.request.user,
            title__iexact=title,
            owner__user__username__iexact=username,
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
                    Project.objects.sync_project_with_workers(
                        ProjectSerializer(model).data, model.cluster
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
    api_user = User.objects.get(username="comp-api-user")

    def get(self, request, *args, **kwargs):
        ser = ProjectSerializer(
            projects_with_access(self.request.user),
            many=True,
            context={"request": request},
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
                    owner=request.user.profile,
                    status="pending",
                    title=title,
                    cluster=Cluster.objects.default(),
                )
                status_url = request.build_absolute_uri(model.app_url)
                model.assign_role("write", self.api_user)
                Project.objects.sync_project_with_workers(
                    ProjectSerializer(model).data, model.cluster
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


class TagsAPIView(GetProjectMixin, APIView):
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    permission_classes = (StrictRequiresActive,)

    def get(self, request, *args, **kwargs):
        project = self.get_object(**kwargs)
        if not project.has_write_access(request.user):
            raise APIPermissionDenied()
        return Response(
            {
                "staging_tag": TagSerializer(instance=project.staging_tag).data,
                "latest_tag": TagSerializer(instance=project.latest_tag).data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        project = self.get_object(**kwargs)
        if not project.has_write_access(request.user):
            raise APIPermissionDenied()
        serializer = TagUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        print("data", data)
        if data.get("staging_tag") is not None:
            tag, _ = Tag.objects.get_or_create(
                project=project,
                image_tag=data.get("staging_tag"),
                defaults=dict(cpu=project.cpu, memory=project.memory),
            )
            project.staging_tag = tag
        elif "staging_tag" in data:
            project.staging_tag = None

        if data.get("latest_tag") is not None:
            tag, _ = Tag.objects.get_or_create(
                project=project,
                image_tag=data.get("latest_tag"),
                defaults=dict(cpu=project.cpu, memory=project.memory),
            )
            project.latest_tag = tag

        project.save()

        return Response(
            {
                "staging_tag": TagSerializer(instance=project.staging_tag).data,
                "latest_tag": TagSerializer(instance=project.latest_tag).data,
            },
            status=status.HTTP_200_OK,
        )


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
        return self.queryset.filter(
            owner__user=user,
            listed=True,
            pk__in=projects_with_access(self.request.user),
        )


class EmbedApprovalView(GetProjectMixin, APIView):
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    permission_classes = (StrictRequiresActive,)

    def post(self, request, *args, **kwargs):
        project = self.get_object(**kwargs)
        if project.tech == "python-paramtools":
            return Response(
                {"tech": "Unable to embed ParamTools-based apps, yet. Stay tuned."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = EmbedApprovalSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            name = serializer.validated_data["name"]
            if EmbedApproval.objects.filter(project=project, name=name).count() > 0:
                return Response(
                    {"exists": f"Embed Approval for {name} already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            model = serializer.save(project=project, owner=request.user.profile)
            return Response(
                EmbedApprovalSerializer(instance=model).data, status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
        eas = EmbedApproval.objects.filter(
            project__owner__user__username__iexact=kwargs["username"],
            project__title__iexact=kwargs["title"],
            owner=request.user.profile,
        )
        serializer = EmbedApprovalSerializer(eas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EmbedApprovalDetailView(APIView):
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    permission_classes = (StrictRequiresActive,)

    def get(self, request, *args, **kwargs):
        ea = EmbedApproval.objects.get(
            project__owner__user__username__iexact=kwargs["username"],
            project__title__iexact=kwargs["title"],
            name__iexact=kwargs["ea_name"],
        )

        # Throw 404 if user does not have access.
        if ea.owner != request.user.profile:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = EmbedApprovalSerializer(ea)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        ea = EmbedApproval.objects.get(
            project__owner__user__username__iexact=kwargs["username"],
            project__title__iexact=kwargs["title"],
            name__iexact=kwargs["ea_name"],
        )

        # Throw 404 if user does not have access.
        if ea.owner != request.user.profile:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = EmbedApprovalSerializer(
            ea, data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            name = serializer.validated_data["name"]
            if (
                name != ea.name
                and EmbedApproval.objects.filter(project=ea.project, name=name).count()
                > 0
            ):
                return Response(
                    {"exists": f"Embed Approval for {name} already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            model = serializer.save(project=ea.project, owner=request.user.profile)
            return Response(
                EmbedApprovalSerializer(instance=model).data, status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        ea = EmbedApproval.objects.get(
            project__owner__user__username__iexact=kwargs["username"],
            project__title__iexact=kwargs["title"],
            name__iexact=kwargs["ea_name"],
        )

        # Throw 404 if user does not have access.
        if ea.owner != request.user.profile:
            return Response(status=status.HTTP_404_NOT_FOUND)

        ea.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DeploymentsView(generics.ListAPIView):
    permission_classes = (StrictRequiresActive,)
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at"]
    ordering = ["created_at"]
    queryset = Deployment.objects.filter(
        deleted_at__isnull=True, status__in=["creating", "running"]
    )
    serializer_class = DeploymentSerializer

    def get_queryset(self):
        if not self.request.user.username == "comp-api-user":
            raise APIPermissionDenied()
        return self.queryset


class DeploymentsDetailView(APIView):
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )

    permission_classes = (RequiresActive,)

    def get(self, request, *args, **kwargs):
        status_query = request.query_params.get("status", None)
        ping = request.query_params.get("ping", None)
        if status_query is None:
            status_kwarg = {"status__in": ["creating", "running"]}
        else:
            status_kwarg = {"status": status_query}

        deployment = get_object_or_404(
            Deployment,
            name__iexact=kwargs["dep_name"],
            project__owner__user__username__iexact=kwargs["username"],
            project__title__iexact=kwargs["title"],
            deleted_at__isnull=True,
            **status_kwarg,
        )

        if not deployment.project.has_write_acces(request.user):
            return Response(status=status.HTTP_404_NOT_FOUND)

        if ping is None:
            deployment.load()
        else:
            deployment.ping()

        return Response(
            DeploymentSerializer(deployment).data, status=status.HTTP_200_OK,
        )

    def delete(self, request, *args, **kwargs):
        if not (
            request.user.is_authenticated and request.user.username == "comp-api-user"
        ):
            raise APIPermissionDenied()
        deployment = get_object_or_404(
            Deployment,
            name__iexact=kwargs["dep_name"],
            project__owner__user__username__iexact=kwargs["username"],
            project__title__iexact=kwargs["title"],
            deleted_at__isnull=True,
            status__in=["creating", "running"],
        )

        deployment.delete_deployment()

        # self.charge_deployment(deployment, use_stripe=USE_STRIPE)

        return Response(status=status.HTTP_204_NO_CONTENT)


class DeploymentsIdView(APIView):
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )

    permission_classes = (RequiresActive,)

    def get(self, request, *args, **kwargs):
        ping = request.query_params.get("ping", None)
        deployment = get_object_or_404(Deployment, id=kwargs["id"])

        if ping is None:
            deployment.load()
        else:
            deployment.ping()

        return Response(
            DeploymentSerializer(deployment).data, status=status.HTTP_200_OK,
        )
