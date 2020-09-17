from django.conf.urls import url
from django.urls import path

from .views import (
    ProjectView,
    ProjectDetailView,
    ProjectDetailAPIView,
    ProjectAPIView,
    TagsAPIView,
    EmbedApprovalView,
    EmbedApprovalDetailView,
    DeploymentsView,
    DeploymentsDetailView,
    DeploymentsIdView,
)


urlpatterns = [
    url(r"^$", ProjectView.as_view(), name="publish"),
    path(
        "api/v1/<str:username>/<str:title>/embedapprovals/",
        EmbedApprovalView.as_view(),
        name="embed_approval",
    ),
    path(
        "api/v1/<str:username>/<str:title>/embedapprovals/<str:ea_name>/",
        EmbedApprovalDetailView.as_view(),
        name="embed_approval_detail",
    ),
    path(
        "api/v1/<str:username>/<str:title>/deployments/<str:dep_name>/",
        DeploymentsDetailView.as_view(),
        name="deployments_detail",
    ),
    path(
        "api/v1/<str:username>/<str:title>/",
        ProjectDetailAPIView.as_view(),
        name="project_detail_api",
    ),
    path(
        "api/v1/<str:username>/<str:title>/tags/",
        TagsAPIView.as_view(),
        name="project_tags_api",
    ),
    path(
        "api/v1/deployments/<str:id>/",
        DeploymentsIdView.as_view(),
        name="deployments_id_view",
    ),
    path("api/v1/deployments/", DeploymentsView.as_view(), name="list_deployments_api"),
    path("api/v1/", ProjectAPIView.as_view(), name="project_create_api"),
]
