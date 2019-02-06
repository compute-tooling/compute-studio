from django.urls import path

from . import views


urlpatterns = [
    path("publish/", views.PublishView.as_view(), name="publish"),
    path("publish/functions/", views.FunctionsView.as_view(), name="functions"),
    path("publishenvironment/", views.EnvironmentView.as_view(), name="environment"),
    path("publish/ioschema/", views.IOSchemaView.as_view(), name="ioschema"),
]
