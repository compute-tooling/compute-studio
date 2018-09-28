from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.Webhook.as_view(), name='webhook'),
    path('update/', views.UpdatePayment.as_view(), name='update_payment'),
    path('update/done/', views.UpdatePaymentDone.as_view(),
         name='update_payment_done'),
]
