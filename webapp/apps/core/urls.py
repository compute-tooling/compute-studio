from django.conf.urls import url
from django.urls import path

from .views import RouterView, EditInputsView, OutputsView, OutputsDownloadView


urlpatterns = [
    path("", RouterView.as_view(), name="inputs"),
    path("<int:pk>/edit/", EditInputsView.as_view(), name="edit"),
    path("<int:pk>/download/", OutputsDownloadView.as_view(), name="download"),
    path("<int:pk>/", OutputsView.as_view(), name="outputs"),
]
