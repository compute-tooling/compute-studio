from django.conf.urls import url
from django.urls import path

from webapp.apps.comp.views import (
    ModelPageView,
    NewSimView,
    EditSimView,
    OutputsDownloadView,
    OutputsView,
    InputsAPIView,
    CreateAPIView,
    DetailAPIView,
    RemoteDetailAPIView,
    ForkDetailAPIView,
    MyInputsAPIView,
    DetailMyInputsAPIView,
    NewSimulationAPIView,
    AuthorsAPIView,
    AuthorsDeleteAPIView,
    PermissionPendingView,
    PermissionGrantedView,
    SimulationAccessAPIView,
)

# API Routes:
# api/v1/ - create sims.
# api/v1/inputs/ - view inputs, post meta parameters.
# api/v1/<int:model_pk>/edit/ - view inputs from sim using model_pk.
# api/v1/<int:model_pk>/ - get all data related to sim, including inputs and outputs.

urlpatterns = [
    path("", ModelPageView.as_view(), name="app"),
    path("new/", NewSimView.as_view(), name="simulation"),
    path("api/v1/", CreateAPIView.as_view(), name="create_api"),
    path("api/v1/inputs/", InputsAPIView.as_view(), name="inputs_api"),
    path("api/v1/new/", NewSimulationAPIView.as_view(), name="inputs_api"),
    path("api/v1/<int:model_pk>/", DetailAPIView.as_view(), name="detail_api"),
    path(
        "api/v1/<int:model_pk>/edit/",
        DetailMyInputsAPIView.as_view(),
        name="detail_myinputs_api_model_pk",
    ),
    path(
        "api/v1/<int:model_pk>/remote/",
        RemoteDetailAPIView.as_view(),
        name="remote_detail_api",
    ),
    path(
        "api/v1/<int:model_pk>/fork/",
        ForkDetailAPIView.as_view(),
        name="fork_detail_api",
    ),
    path(
        "api/v1/<int:model_pk>/access/",
        SimulationAccessAPIView.as_view(),
        name="access_api",
    ),
    path(
        "api/v1/<int:model_pk>/authors/",
        AuthorsAPIView.as_view(),
        name="authors_add_api",
    ),
    path(
        "api/v1/<int:model_pk>/authors/<str:author>/",
        AuthorsDeleteAPIView.as_view(),
        name="authors_delete_api",
    ),
    path(
        "<int:model_pk>/access/<uuid:id>/grant/",
        PermissionGrantedView.as_view(),
        name="permissions_grant",
    ),
    path(
        "<int:model_pk>/access/<uuid:id>/",
        PermissionPendingView.as_view(),
        name="permissions_pending",
    ),
    path("<int:model_pk>/edit/", EditSimView.as_view(), name="edit"),
    path("<int:model_pk>/download/", OutputsDownloadView.as_view(), name="download"),
    path("<int:model_pk>/", EditSimView.as_view(), name="outputs"),
    path("<int:model_pk>/v0/", OutputsView.as_view(), name="v0_outputs"),
]
