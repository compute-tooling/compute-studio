import os

import stripe

from django.views import View, generic
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseServerError

from webapp.apps.users.models import Project

from . import webhooks
from .email import send_teams_interest_mail
from .models import Customer, Product, Subscription, SubscriptionItem


stripe.api_key = os.environ.get("STRIPE_SECRET")
wh_secret = os.environ.get("WEBHOOK_SECRET")


def update_payment(user, stripe_token):
    if hasattr(user, "customer"):
        user.customer.update_source(stripe_token)
    else:  # create customer.
        stripe_customer = stripe.Customer.create(email=user.email, source=stripe_token)
        customer = Customer.construct(stripe_customer, user=user)
        if Project.objects.count() > 0:
            customer.sync_subscriptions()
        else:
            print("No projects yet.")


class Webhook(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(Webhook, self).dispatch(*args, **kwargs)

    def post(self, request):
        payload = request.body
        sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
        event = None

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, wh_secret)
        except ValueError as e:
            # Invalid payload
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return HttpResponse(status=400)

        webhooks.process_event(event)

        return HttpResponse(status=200)


class UpdatePayment(View):
    update_template = "billing/update_pmt_info.html"
    add_template = "billing/add_pmt_info.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        if hasattr(request.user, "customer") and request.user.customer is not None:
            return render(request, self.update_template)
        else:
            return render(request, self.add_template)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        # get stripe token and update web db and stripe db
        stripe_token = request.POST["stripeToken"]
        try:
            update_payment(request.user, stripe_token)
            return redirect("update_payment_done")
        except Exception as e:
            import traceback

            traceback.print_exc()
            msg = (
                "Something has gone wrong. Contact us at admin@compute.studio to "
                "resolve this issue"
            )
            return HttpResponseServerError(msg)


class UpdatePaymentDone(generic.TemplateView):
    template_name = "billing/update_pmt_info_done.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class UpgradePlan(View):
    template_name = "billing/upgrade_plan.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        plan_duration = request.GET.get("plan_duration", "monthly")
        if plan_duration not in ("monthly", "yearly"):
            plan_duration = "monthly"

        upgrade_plan = request.GET.get("upgrade_plan", None)
        if upgrade_plan is not None and upgrade_plan.lower() not in (
            "free",
            "pro",
            "team",
        ):
            upgrade_plan = None

        customer = getattr(request.user, "customer", None)

        card_info = {"last4": None, "brand": None}
        current_plan = {"plan_duration": None, "name": "free"}
        if customer is not None:
            card_info = customer.card_info()
            product = Product.objects.get(name="Compute Studio Subscription")
            current_plan = customer.current_plan()

            if upgrade_plan == "pro":
                if plan_duration == "monthly":
                    new_plan = product.plans.get(nickname="Monthly Pro Plan")
                else:
                    new_plan = product.plans.get(nickname="Yearly Pro Plan")

                customer.update_plan(new_plan)

            elif upgrade_plan == "team":
                send_teams_interest_mail(customer.user)

            elif upgrade_plan == "free":
                customer.update_plan(None)

            current_plan = customer.current_plan()

        return render(
            request,
            self.template_name,
            context={
                "plan_duration": plan_duration,
                "current_plan": current_plan,
                "card_info": card_info,
            },
        )

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        # get stripe token and update web db and stripe db
        stripe_token = request.POST["stripeToken"]
        try:
            update_payment(request.user, stripe_token)
            return redirect("upgrade_plan")
        except Exception:
            import traceback

            traceback.print_exc()
            msg = (
                "Something has gone wrong. Contact us at admin@compute.studio to "
                "resolve this issue"
            )
            return HttpResponseServerError(msg)
