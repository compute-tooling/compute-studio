import cryptography
import jwt


from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed


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
