from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.SignUp.as_view(), name='signup'),
    path('profile/', views.UserProfile.as_view(), name='userprofile'),
    path('profile/cancel/', views.CancelSubscription.as_view(),
         name='cancel_subscription'),
    path('profile/cancel/done/', views.CancelSubscriptionDone.as_view(),
         name='cancel_subscription_done'),
    path('profile/delete/', views.DeleteUser.as_view(), name='delete_user'),
    path('profile/delete/done/', views.DeleteUserDone.as_view(),
         name='delete_user_done')
]
