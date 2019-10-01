from django.conf.urls import url
from django.urls import path

from .views import ProjectView, ProjectDetailView, ProjectDetailAPIView, ProjectAPIView


urlpatterns = [
    url(r"^$", ProjectView.as_view(), name="publish"),
    path(
        "api/<str:username>/<str:title>/detail/",
        ProjectDetailAPIView.as_view(),
        name="project_detail_api",
    ),
    path("api/", ProjectAPIView.as_view(), name="project_create_api"),
]
