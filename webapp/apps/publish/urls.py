from django.conf.urls import url
from django.urls import path

from .views import (
    ProjectView,
    ProjectDetailView,
    ProjectDetailAPIView,
    ProjectAPIView,
    DeploymentAPIView,
    EmbedApprovalView,
    EmbedApprovalDetailView,
    RunningDeploymentsView,
)


urlpatterns = [
    url(r"^$", ProjectView.as_view(), name="publish"),
    path(
        "api/<str:username>/<str:title>/embedapprovals/",
        EmbedApprovalView.as_view(),
        name="embed_approval",
    ),
    path(
        "api/<str:username>/<str:title>/embedapprovals/<str:ea_name>/",
        EmbedApprovalDetailView.as_view(),
        name="embed_approval_detail",
    ),
    path(
        "api/<str:username>/<str:title>/rds/<str:rd_name>/",
        RunningDeploymentsView.as_view(),
        name="running_deployments_detail",
    ),
    path(
        "api/<str:username>/<str:title>/detail/",
        ProjectDetailAPIView.as_view(),
        name="project_detail_api",
    ),
    path(
        "api/<str:username>/<str:title>/deployments/",
        DeploymentAPIView.as_view(),
        name="project_deployments_api",
    ),
    path("api/", ProjectAPIView.as_view(), name="project_create_api"),
]
