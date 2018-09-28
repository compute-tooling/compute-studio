from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.SignUp.as_view(), name='signup'),
    path('profile/', views.UserProfile.as_view(), name='userprofile'),
    path('profile/cancel/', views.CancelSubscription.as_view(),
         name='cancel_subscription'),
    path('profile/cancel/done/', views.CancelSubscriptionDone.as_view(),
         name='cancel_subscription_done')
]
