from django.conf.urls import url

from .views import (TaxcalcInputsView, TaxcalcRunDetailView,
                    TaxcalcRunDownloadView)


urlpatterns = [
    url(r'^$', TaxcalcInputsView.as_view(), name='taxcalc'),
    url(r'^(?P<pk>[-\d\w]+)/download/?$', TaxcalcRunDownloadView.as_view(),
        name='taxcalc_download'),
    url(r'^(?P<pk>[-\d\w]+)/', TaxcalcRunDetailView.as_view(),
        name='taxcalc_detail'),
]
