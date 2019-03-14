from django.conf.urls import url

from .views import (
    MatchupsInputsView,
    MatchupsEditInputsView,
    MatchupsOutputsView,
    MatchupsOutputsDownloadView,
)


urlpatterns = [
    # url(r'^$', MatchupsInputsView.as_view(), name='matchups'),
    # url(r'^(?P<pk>[-\d\w]+)/edit/?$', MatchupsEditInputsView.as_view(),
    #     name='matchups_edit'),
    # url(r'^(?P<pk>[-\d\w]+)/download/?$', MatchupsOutputsDownloadView.as_view(),
    #     name='matchups_download'),
    # url(r'^(?P<pk>[-\d\w]+)/', MatchupsOutputsView.as_view(),
    #     name='matchups_outputs'),
]
