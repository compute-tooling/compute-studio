from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.Webhook.as_view(), name='webhook'),
]
