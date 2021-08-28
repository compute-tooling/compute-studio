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
from webapp.apps.publish import views as publishviews


urlpatterns = [
    # admin apps
    path("admin/", admin.site.urls),
    path("api-token-auth/", rf_views.obtain_auth_token),
    path("", include("webapp.apps.pages.urls")),
    path("apps/", include("webapp.apps.publish.urls")),
    path("projects/", include("webapp.apps.publish.urls")),
    path("publish/", include("webapp.apps.publish.urls")),
    path("new/", publishviews.ProjectView.as_view(), name="new_project"),
    path("users/", include("webapp.apps.users.urls")),
    path("users/", include("django.contrib.auth.urls")),
    path("billing/", include("webapp.apps.billing.urls")),
    path(
        "storage/screenshots/<str:data_id>",
        compviews.DataView.as_view(),
        name="data__view",
    ),
    path("outputs/api/", compviews.OutputsAPIView.as_view(), name="outputs_api"),
    path("inputs/api/", compviews.MyInputsAPIView.as_view(), name="myinputs_api"),
    path(
        "model-config/api/",
        compviews.ModelConfigAPIView.as_view(),
        name="modelconfig_api",
    ),
    url(r"^rest-auth/", include("rest_auth.urls")),
    url(r"^rest-auth/registration/", include("rest_auth.registration.urls")),
    path("api/v1/sims", compviews.UserSimsAPIView.as_view(), name="sim_api"),
    path("feed/", pageviews.LogView.as_view(), name="feed"),
    path("log/", pageviews.LogView.as_view(), name="log"),
    path("api/v1/feed", compviews.PublicSimsAPIView.as_view(), name="feed_api"),
    path("api/v1/log", compviews.PublicSimsAPIView.as_view(), name="log_api"),
    path(
        "api/v1/sims/<str:username>",
        compviews.ProfileSimsAPIView.as_view(),
        name="public_sim_api",
    ),
    path("api/v1/models", publishviews.ModelsAPIView.as_view(), name="models_api"),
    path(
        "api/v1/models/<str:username>",
        publishviews.ProfileModelsAPIView.as_view(),
        name="public_sim_api",
    ),
    path(
        "api/v1/models/recent/",
        publishviews.RecentModelsAPIView.as_view(),
        name="recent_models_api",
    ),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path(
        "<str:username>/<str:title>/",
        publishviews.ProjectDetailView.as_view(),
        name="app",
    ),
    path(
        "<str:username>/<str:title>/settings/about/",
        publishviews.ProjectReactView.as_view(),
        name="app_settings_about",
    ),
    path(
        "<str:username>/<str:title>/settings/configure/",
        publishviews.ProjectReactView.as_view(),
        name="app_settings_config",
    ),
    path(
        "<str:username>/<str:title>/settings/environment/",
        publishviews.ProjectReactView.as_view(),
        name="app_settings_env",
    ),
    path(
        "<str:username>/<str:title>/settings/access/",
        publishviews.ProjectReactView.as_view(),
        name="app_settings_access",
    ),
    path(
        "<str:username>/<str:title>/settings/",
        publishviews.ProjectReactView.as_view(),
        name="app_settings",
    ),
    path(
        "<str:username>/<str:title>/builds/<int:id>/",
        publishviews.BuildDetailReactView.as_view(),
        name="app_settings",
    ),
    path(
        "<str:username>/<str:title>/builds/new/",
        publishviews.ProjectReactView.as_view(),
        name="app_settings",
    ),
    path(
        "<str:username>/<str:title>/builds/",
        publishviews.ProjectReactView.as_view(),
        name="app_settings",
    ),
    # add project URL's here
    path("<str:username>/<str:title>/", include("webapp.apps.comp.urls")),
    path("<str:username>/", pageviews.ProfileView.as_view(), name="userprofile"),
]
