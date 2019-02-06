from django.conf.urls import url

from .views import BaseView


urlpatterns = [url(r"^$", BaseView.as_view(), name="home")]
