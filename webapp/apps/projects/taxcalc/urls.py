from django.conf.urls import url

from .views import (taxcalc_inputs, TaxcalcRunDetailView,
                    TaxcalcRunDownloadView)


urlpatterns = [
    url(r'^$', taxcalc_inputs, name='taxcalc'),
    url(r'^(?P<pk>[-\d\w]+)/download/?$', TaxcalcRunDownloadView.as_view(),
        name='taxcalc_download'),
    url(r'^(?P<pk>[-\d\w]+)/', TaxcalcRunDetailView.as_view(),
        name='taxcalc_detail'),
]
