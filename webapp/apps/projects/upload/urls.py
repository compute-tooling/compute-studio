

from django.conf.urls import url

from .views import (UploadInputsView, UploadOutputsView,
                    UploadOutputsDownloadView)


urlpatterns = [
    url(r'^$', UploadInputsView.as_view(),
        name='upload'),
    url(r'^(?P<pk>[-\d\w]+)/download/?$', UploadOutputsDownloadView.as_view(),
        name='upload_download'),
    url(r'^(?P<pk>[-\d\w]+)/', UploadOutputsView.as_view(),
        name='upload_results'),
]
