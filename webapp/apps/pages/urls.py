from django.conf.urls import url

from .views import BaseView, Publish


urlpatterns = [
    url(r"^$", BaseView.as_view(), name="home"),
    # url(r'publish/', Publish.as_view(), name='publish'),
]
