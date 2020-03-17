import os

import stripe

from django.views import View, generic
from django.shortcuts import render, redirect, reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseServerError
from django.urls import resolve, Resolver404

from webapp.apps.users.models import Project

from . import webhooks
from .email import send_teams_interest_mail
from .models import (
    Customer,
    Product,
    Subscription,
    SubscriptionItem,
    UpdateStatus,
    timestamp_to_datetime,
)


stripe.api_key = os.environ.get("STRIPE_SECRET")
wh_secret = os.environ.get("WEBHOOK_SECRET")

white_listed_urls = (
    # next urls for plus plan
    "/billing/upgrade/?selected_plan=plus",
    "/billing/upgrade/monthly/?selected_plan=plus",
    "/billing/upgrade/yearly/?selected_plan=plus",
    # next urls for pro plan
    "/billing/upgrade/?selected_plan=pro",
    "/billing/upgrade/monthly/?selected_plan=pro",
    "/billing/upgrade/yearly/?selected_plan=pro",
)


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
            next_url = "update_payment_done"
            to = request.GET.get("next", None)
            if to is not None:
                # Try to resolve the url.
                try:
                    next_url = resolve(to).url_name
                except Resolver404:
                    if to in white_listed_urls:
                        next_url = to
            return redirect(next_url)
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


def parse_upgrade_params(request):
    upgrade_plan = request.GET.get("upgrade_plan", None)
    if upgrade_plan is not None and upgrade_plan.lower() not in (
        "free",
        "plus",
        "pro",
        "team",
    ):
        upgrade_plan = None

    selected_plan = request.GET.get("selected_plan", None)
    if selected_plan is not None and selected_plan.lower() not in (
        "free",
        "plus",
        "pro",
        "team",
    ):
        selected_plan = None
    return upgrade_plan, selected_plan


class UpgradePlan(View):
    template_name = "billing/upgrade_plan.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        # plan_duration optionally given in url: /billing/upgrade/[plan_duration]/
        plan_duration = kwargs.get("plan_duration", "monthly")
        upgrade_plan, selected_plan = parse_upgrade_params(request)
        customer = getattr(request.user, "customer", None)
        card_info = {"last4": None, "brand": None}
        current_plan = {"plan_duration": None, "name": "free"}
        if customer is not None:
            card_info = customer.card_info()
            product = Product.objects.get(name="Compute Studio Subscription")
            current_plan = customer.current_plan()
            result = UpdateStatus.nochange
            new_plan = None

            if upgrade_plan == "plus":
                if plan_duration == "monthly":
                    new_plan = product.plans.get(nickname="Monthly Plus Plan")
                else:
                    new_plan = product.plans.get(nickname="Yearly Plus Plan")

                result = customer.update_plan(new_plan)

            elif upgrade_plan == "pro":
                if plan_duration == "monthly":
                    new_plan = product.plans.get(nickname="Monthly Pro Plan")
                else:
                    new_plan = product.plans.get(nickname="Yearly Pro Plan")

                result = customer.update_plan(new_plan)

            elif upgrade_plan == "team":
                send_teams_interest_mail(customer.user)

            elif upgrade_plan == "free":
                result = customer.update_plan(None)

            current_plan = customer.current_plan()

            if result != UpdateStatus.nochange:
                next_url = reverse(
                    "upgrade_plan_duration_done",
                    kwargs=dict(
                        plan_duration=current_plan["plan_duration"] or plan_duration
                    ),
                )
                return redirect(next_url)

        return render(
            request,
            self.template_name,
            context={
                "plan_duration": plan_duration,
                "current_plan": current_plan,
                "card_info": card_info,
                "selected_plan": selected_plan,
            },
        )


class UpgradePlanDone(View):
    template_name = "billing/upgrade_plan.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        # plan_duration optionally given in url: /billing/upgrade/[plan_duration]/
        plan_duration = kwargs.get("plan_duration", "monthly")
        customer = getattr(request.user, "customer", None)
        if customer is not None:
            card_info = customer.card_info()
            current_si = customer.current_plan(as_dict=False)
            current_plan = customer.current_plan(si=current_si, as_dict=True)
            plan_name = current_si.plan.nickname
        else:
            card_info = {"last4": None, "brand": None}
            current_plan = {"plan_duration": None, "name": "free"}
            plan_name = "Free Plan"

        return render(
            request,
            self.template_name,
            context={
                "plan_duration": plan_duration,
                "current_plan": current_plan,
                "card_info": card_info,
                "update_completed": True,
                "update_completed_msg": f"You are now on the {plan_name}.",
            },
        )


class ListInvoices(View):
    template_name = "billing/invoices.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        invoices = []
        if getattr(request.user, "customer", None) is not None:
            for invoice in request.user.customer.invoices():
                invoices.append(
                    {
                        "hosted_invoice_url": invoice.hosted_invoice_url,
                        "created": timestamp_to_datetime(invoice.created).strftime(
                            "%Y-%m-%d"
                        ),
                        "amount": invoice.total,
                        "invoice_pdf": invoice.invoice_pdf,
                        "status": invoice.status,
                    }
                )
        return render(request, self.template_name, context={"invoices": invoices})
