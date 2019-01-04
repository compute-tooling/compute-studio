from django.conf.urls import url

from .views import ({Project}InputsView, {Project}EditInputsView,
                    {Project}OutputsView, {Project}OutputsDownloadView)


urlpatterns = [
    url(r'^$', {Project}InputsView.as_view(), name='{project}'),
    url(r'^(?P<pk>[-\d\w]+)/edit/?$', {Project}EditInputsView.as_view(),
        name='{project}_edit'),
    url(r'^(?P<pk>[-\d\w]+)/download/?$', {Project}OutputsDownloadView.as_view(),
        name='{project}_download'),
    url(r'^(?P<pk>[-\d\w]+)/', {Project}OutputsView.as_view(),
        name='{project}_outputs'),
]
