from django.contrib.auth import get_user_model
from django.db.models import Q, BooleanField, Case, When, Value
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication,
)

from webapp.apps.publish.views import GetProjectMixin
from .permissions import StrictRequiresActive

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=True, min_length=1)

    class Meta:
        model = User
        fields = ("username",)
        read_only = ("username",)


class UsersAPIView(APIView):
    permission_classes = (StrictRequiresActive,)
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )

    queryset = User.objects.order_by("username").all()

    def get(self, request, *args, **kwargs):
        search_term = request.query_params.get("username", None)
        if not search_term:
            return Response([], status=status.HTTP_200_OK)

        suggested = (
            User.objects.filter(username__icontains=search_term)
            .annotate(
                exact_match=Case(
                    When(username__iexact=search_term, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                startswith_match=Case(
                    When(username__istartswith=search_term, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
            .order_by("-exact_match", "-startswith_match")
        )[:10]
        results = UserSerializer(suggested, many=True)
        return Response(results.data, status=status.HTTP_200_OK)


class AccessStatusAPI(GetProjectMixin, APIView):
    authentication_classes = (
        SessionAuthentication,
        TokenAuthentication,
    )

    def get(self, request, *args, **kwargs):
        user = request.user
        plan = {"name": "free", "plan_duration": None}
        remaining_private_sims = {}
        if user.is_authenticated and user.profile:
            user_status = user.profile.status
            username = user.username
            if getattr(user, "customer", None) is not None:
                plan = user.customer.current_plan()

        else:
            user_status = "anon"
            username = None

        if kwargs:
            project = self.get_object(**kwargs)
            if plan["name"] == "free" and user.is_authenticated:
                remaining_private_sims = user.profile.remaining_private_sims(
                    project=project
                )
            exp_cost, exp_time = project.exp_job_info(adjust=True)
            if user.is_authenticated and user.profile:
                can_run = user.profile.can_run(project)
                can_write_project = project.has_write_access(user)
            else:
                can_run = False
                can_write_project = False

            return Response(
                {
                    "is_sponsored": project.is_sponsored,
                    "sponsor_message": project.sponsor_message,
                    "user_status": user_status,
                    "can_run": can_run,
                    "can_write_project": can_write_project,
                    "server_cost": project.server_cost,
                    "exp_cost": exp_cost,
                    "exp_time": exp_time,
                    "api_url": reverse("access_project", kwargs=kwargs),
                    "username": username,
                    "plan": plan,
                    "remaining_private_sims": remaining_private_sims,
                    "project": str(project),
                }
            )
        else:
            if plan["name"] == "free" and user.is_authenticated:
                remaining_private_sims = user.profile.remaining_private_sims()

            return Response(
                {
                    "user_status": user_status,
                    "api_url": reverse("access_status"),
                    "username": username,
                    "plan": plan,
                    "remaining_private_sims": remaining_private_sims,
                }
            )
