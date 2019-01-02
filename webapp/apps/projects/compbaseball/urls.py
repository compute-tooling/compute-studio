from django.conf.urls import url

from .views import (CompbaseballInputsView, CompbaseballEditInputsView,
                    CompbaseballOutputsView, CompbaseballOutputsDownloadView)


urlpatterns = [
    url(r'^$', CompbaseballInputsView.as_view(), name='compbaseball'),
    url(r'^(?P<pk>[-\d\w]+)/edit/?$', CompbaseballEditInputsView.as_view(),
        name='compbaseball_edit'),
    url(r'^(?P<pk>[-\d\w]+)/download/?$', CompbaseballOutputsDownloadView.as_view(),
        name='compbaseball_download'),
    url(r'^(?P<pk>[-\d\w]+)/', CompbaseballOutputsView.as_view(),
        name='compbaseball_outputs'),
]
