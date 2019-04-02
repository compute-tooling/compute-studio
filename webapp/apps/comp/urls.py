from django.conf.urls import url
from django.urls import path

from .views import RouterView, EditInputsView, OutputsView, OutputsDownloadView


urlpatterns = [
    path("", RouterView.as_view(), name="app"),
    path("<int:model_pk>/edit/", EditInputsView.as_view(), name="edit"),
    path("<int:model_pk>/download/", OutputsDownloadView.as_view(), name="download"),
    path("<int:model_pk>/", OutputsView.as_view(), name="outputs"),
]
