from django.urls import path
from . import views

urlpatterns = [
    path("settings/", views.UserSettings.as_view(), name="user_settings"),
    path("signup/", views.SignUp.as_view(), name="signup"),
    path("cancel/", views.CancelSubscription.as_view(), name="cancel_subscription"),
    path(
        "cancel/done/",
        views.CancelSubscriptionDone.as_view(),
        name="cancel_subscription_done",
    ),
    path("delete/", views.DeleteUser.as_view(), name="delete_user"),
    path("delete/done/", views.DeleteUserDone.as_view(), name="delete_user_done"),
    path("status/", views.AccessStatusAPI.as_view(), name="access_status"),
    path(
        "status/<str:username>/<str:title>/",
        views.AccessStatusAPI.as_view(),
        name="access_project",
    ),
]
