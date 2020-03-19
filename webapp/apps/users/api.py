from django.contrib.auth import get_user_model
from django.db.models import Q, BooleanField, Case, When, Value
from rest_framework.views import APIView
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication,
)

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
            User.objects.filter(
                Q(username__icontains=search_term) | Q(email__iexact=search_term)
            )
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
