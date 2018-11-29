from django.conf.urls import url

from .views import (TaxcalcInputsView, TaxcalcOutputsView,
                    TaxcalcOutputsDownloadView)


urlpatterns = [
    url(r'^$', TaxcalcInputsView.as_view(), name='taxcalc'),
    url(r'^(?P<pk>[-\d\w]+)/download/?$', TaxcalcOutputsDownloadView.as_view(),
        name='taxcalc_download'),
    url(r'^(?P<pk>[-\d\w]+)/', TaxcalcOutputsView.as_view(),
        name='taxcalc_outputs'),
]
