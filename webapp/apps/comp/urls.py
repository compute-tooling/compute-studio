from django.conf.urls import url
from django.urls import path

from webapp.apps.comp.views import (
    RouterView,
    EditInputsView,
    EditSimView,
    OutputsDownloadView,
    OutputsView,
    InputsAPIView,
    APIRouterView,
    DetailAPIView,
    MyInputsAPIView,
    DetailMyInputsAPIView,
)

# API Routes:
# api/v1/ - create sims.
# api/v1/inputs/ - view inputs, post meta parameters.
# api/v1/inputs/<str:hashid>/ - view inputs, check inputs validation status on created sim.
# api/v1/<int:model_pk>/edit/ - view inputs from sim using model_pk.
# api/v1/<int:model_pk>/ - get all data related to sim, including inputs and outputs.

urlpatterns = [
    path("", RouterView.as_view(), name="app"),
    path("api/v1/", APIRouterView.as_view(), name="create_api"),
    path("api/v1/inputs/", InputsAPIView.as_view(), name="inputs_api"),
    path(
        "api/v1/inputs/<str:hashid>/",
        DetailMyInputsAPIView.as_view(),
        name="detail_myinputs_api",
    ),
    path("api/v1/<int:model_pk>/", DetailAPIView.as_view(), name="detail_api"),
    path(
        "api/v1/<int:model_pk>/edit/",
        DetailMyInputsAPIView.as_view(),
        name="detail_myinputs_api_model_pk",
    ),
    path("<int:model_pk>/edit/", EditSimView.as_view(), name="edit"),
    path("<int:model_pk>/download/", OutputsDownloadView.as_view(), name="download"),
    path("inputs/<str:hashid>/", EditInputsView.as_view(), name="edit_inputs"),
    path("<int:model_pk>/", OutputsView.as_view(), name="outputs"),
]
