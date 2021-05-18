import cryptography
import jwt


from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from oauth2_provider.contrib.rest_framework import (
    OAuth2Authentication as BaseOAuth2Authentication,
)


from webapp.apps.users.models import (
    User,
    Cluster,
    cryptkeeper,
)


class ClusterAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class for authenticating requests from the compute
    cluster.
    """

    def authenticate(self, request):
        jwt_token = request.META.get("Authorization") or request.META.get(
            "HTTP_AUTHORIZATION"
        )
        cluster_user = request.META.get("Cluster-User") or request.META.get(
            "HTTP_CLUSTER_USER"
        )

        if jwt_token is None or cluster_user is None:
            print("Missing jwt token and/or cluster user.")
            return None

        try:
            cluster = Cluster.objects.get(service_account__user__username=cluster_user)
        except Cluster.DoesNotExist:
            print("Unknown user.")
            raise AuthenticationFailed("Invalid token")

        try:
            data = jwt.decode(
                jwt_token, cryptkeeper.decrypt(cluster.jwt_secret), algorithms=["HS256"]
            )
        except (
            jwt.DecodeError,
            cryptography.exceptions.InvalidKey,
            cryptography.fernet.InvalidToken,
        ):
            raise AuthenticationFailed("Invalid token")

        if str(cluster_user) != data["username"]:
            raise AuthenticationFailed("No such user")

        return (cluster.service_account.user, None)


class ClientOAuth2Authentication(BaseOAuth2Authentication):
    """
    Authenticator that forces request.user to be present even if the
    oauth2_provider package doesn't want it to be.

    Works around the change introduced in:
    https://github.com/evonove/django-oauth-toolkit/commit/628f9e6ba98007d2940bb1a4c28136c03d81c245

    Reference:
    https://github.com/evonove/django-oauth-toolkit/issues/38

    """

    def authenticate(self, request):
        super_result = super().authenticate(request)

        if super_result:
            # The request was found to be authentic.
            user, token = super_result
            if (
                user is None
                and token.application.authorization_grant_type == "client-credentials"
            ):
                user = token.application.user
            result = user, token
        else:
            result = super_result
        return result
