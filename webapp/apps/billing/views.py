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
from .models import Customer


stripe.api_key = os.environ.get("STRIPE_SECRET")
wh_secret = os.environ.get("WEBHOOK_SECRET")


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
            if hasattr(request.user, "customer"):
                request.user.customer.update_source(stripe_token)
            else:  # create customer.
                stripe_customer = stripe.Customer.create(
                    email=request.user.email, source=stripe_token
                )
                customer = Customer.construct(stripe_customer, user=request.user)
                if Project.objects.count() > 0:
                    customer.sync_subscriptions()
                else:
                    print("No projects yet.")
            return redirect("update_payment_done")
        except Exception as e:
            import traceback

            traceback.print_exc()
            msg = (
                "Something has gone wrong. Contact us at admin@comp.com to "
                "resolve this issue"
            )
            return HttpResponseServerError(msg)


class UpdatePaymentDone(generic.TemplateView):
    template_name = "billing/update_pmt_info_done.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
