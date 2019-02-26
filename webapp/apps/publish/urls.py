from django.conf.urls import url
from django.urls import path

from .views import ProjectView, ProjectDetailView, ProjectDetailAPIView


urlpatterns = [
    url(r"^$", ProjectView.as_view(), name="publish"),
    # path("<str:username>/<str:app_name>/detail/", ProjectDetailView.as_view(), name="project_detail"),
    path(
        "api/<str:username>/<str:app_name>/detail/",
        ProjectDetailAPIView.as_view(),
        name="project_detail_api",
    ),
]
