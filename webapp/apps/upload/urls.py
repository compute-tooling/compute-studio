

from django.conf.urls import url

from .views import (FileInputView, FileRunDetailView, FileRunDownloadView)


urlpatterns = [
    url(r'^$', FileInputView.as_view(),
        name='upload'),
    url(r'^(?P<pk>[-\d\w]+)/download/?$', FileRunDownloadView.as_view(),
        name='upload_download'),
    url(r'^(?P<pk>[-\d\w]+)/', FileRunDetailView.as_view(),
        name='upload_results'),
]
