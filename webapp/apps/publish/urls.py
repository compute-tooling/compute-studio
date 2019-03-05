from django.conf.urls import url
from django.urls import path

from .views import (
    ProjectView,
    ProjectDetailView,
    ProjectDetailAPIView,
    ProjectCreateAPIView,
)


urlpatterns = [
    url(r"^$", ProjectView.as_view(), name="publish"),
    path(
        "api/<str:username>/<str:app_name>/detail/",
        ProjectDetailAPIView.as_view(),
        name="project_detail_api",
    ),
    path("api/", ProjectCreateAPIView.as_view(), name="project_create_api"),
]
