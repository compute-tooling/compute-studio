from .views import (
    ModelPageView,
    NewSimView,
    EditSimView,
    OutputsDownloadView,
    OutputsView,
    PermissionPendingView,
    PermissionGrantedView,
    DataView,
)

from .api import (
    InputsAPIView,
    CreateAPIView,
    DetailAPIView,
    RemoteDetailAPIView,
    ForkDetailAPIView,
    OutputsAPIView,
    DetailMyInputsAPIView,
    MyInputsAPIView,
    NewSimulationAPIView,
    AuthorsAPIView,
    AuthorsDeleteAPIView,
    SimulationAccessAPIView,
    UserSimsAPIView,
    PublicSimsAPIView,
    ProfileSimsAPIView,
)
