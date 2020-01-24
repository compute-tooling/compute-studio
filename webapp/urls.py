"""webapp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import url
from rest_framework.authtoken import views as rf_views

from webapp.apps.comp import views as compviews
from webapp.apps.publish import views as publishviews
from webapp.apps.pages import views as pageviews


urlpatterns = [
    # admin apps
    path("admin/", admin.site.urls),
    path("api-token-auth/", rf_views.obtain_auth_token),
    path("", include("webapp.apps.pages.urls")),
    path("publish/", include("webapp.apps.publish.urls")),
    path("users/", include("webapp.apps.users.urls")),
    path("users/", include("django.contrib.auth.urls")),
    path("billing/", include("webapp.apps.billing.urls")),
    path("outputs/api/", compviews.OutputsAPIView.as_view(), name="outputs_api"),
    path("inputs/api/", compviews.MyInputsAPIView.as_view(), name="myinputs_api"),
    path(
        "simperms/<uuid:id>/grant/",
        compviews.PermissionGrantedView.as_view(),
        name="permissions_grant",
    ),
    path(
        "simperms/<uuid:id>/",
        compviews.PermissionPendingView.as_view(),
        name="permissions_pending",
    ),
    url(r"^rest-auth/", include("rest_auth.urls")),
    url(r"^rest-auth/registration/", include("rest_auth.registration.urls")),
    path(
        "<str:username>/<str:title>/detail/",
        publishviews.ProjectDetailView.as_view(),
        name="project_detail",
    ),
    # add project URL's here
    path("<str:username>/<str:title>/", include("webapp.apps.comp.urls")),
    path("<str:username>/", pageviews.ProfileView.as_view(), name="userprofile"),
]
