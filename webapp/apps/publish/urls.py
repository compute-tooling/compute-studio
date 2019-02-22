from django.conf.urls import url

from .views import PublishView


urlpatterns = [url(r"^$", PublishView.as_view(), name="publish")]
