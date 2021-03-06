from django.urls import path
from . import views

urlpatterns = [
    path("webhook/", views.Webhook.as_view(), name="webhook"),
    path("update/", views.UpdatePayment.as_view(), name="update_payment"),
    path("update/done/", views.UpdatePaymentDone.as_view(), name="update_payment_done"),
    path("upgrade/", views.Plans.as_view(), name="upgrade_plan"),
    path(
        "upgrade/<str:plan_duration>/aftertrial/",
        views.AutoUpgradeAfterTrial.as_view(),
        name="upgrade_aftertrial",
    ),
    path(
        "upgrade/<str:plan_duration>/aftertrial/confirm/",
        views.AutoUpgradeAfterTrialConfirm.as_view(),
        name="upgrade_aftertrial_confirm",
    ),
    path(
        "upgrade/<str:plan_duration>/",
        views.UpgradePlan.as_view(),
        name="upgrade_plan_duration",
    ),
    path(
        "upgrade/<str:plan_duration>/done/",
        views.UpgradePlanDone.as_view(),
        name="upgrade_plan_duration_done",
    ),
    path("invoices/", views.ListInvoices.as_view(), name="list_invoices"),
]
