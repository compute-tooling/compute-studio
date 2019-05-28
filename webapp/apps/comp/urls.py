from django.conf.urls import url
from django.urls import path

from webapp.apps.comp.views import (
    RouterView,
    EditInputsView,
    OutputsDownloadView,
    OutputsView,
    InputsAPIView,
    APIRouterView,
    DetailAPIView,
)

urlpatterns = [
    path("", RouterView.as_view(), name="app"),
    path("api/v1/", APIRouterView.as_view(), name="create_api"),
    path("api/v1/inputs/", InputsAPIView.as_view(), name="inputs_api"),
    path("api/v1/<int:model_pk>", DetailAPIView.as_view(), name="detail_api"),
    path("<int:model_pk>/edit/", EditInputsView.as_view(), name="edit"),
    path("<int:model_pk>/download/", OutputsDownloadView.as_view(), name="download"),
    path("<int:model_pk>/", OutputsView.as_view(), name="outputs"),
]
