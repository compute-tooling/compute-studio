import os

import stripe

from django.views import View, generic
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import (HttpResponse, HttpResponseNotFound,
                         HttpResponseServerError)

from . import webhooks


stripe.api_key = os.environ.get('STRIPE_SECRET')
wh_secret = os.environ.get('WEBHOOK_SECRET')


class Webhook(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(Webhook, self).dispatch(*args, **kwargs)

    def post(self, request):
        payload = request.body
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']
        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, wh_secret
            )
        except ValueError as e:
            # Invalid payload
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return HttpResponse(status=400)

        webhooks.process_event(event)

        return HttpResponse(status=200)


class UpdatePayment(View):
    template_name = 'billing/update_pmt_info.html'

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        # get stripe token and update web db and stripe db
        stripe_token = request.POST['stripeToken']
        try:
            if hasattr(request.user, 'customer'):
                request.user.customer.update_source(stripe_token)
                return redirect('update_payment_done')
            else:
                return HttpResponseNotFound('Customer object not found')
        except Exception as e:
            import traceback; traceback.print_exc()
            msg = ('Something has gone wrong. Contact us at admin@comp.com to '
                   'resolve this issue')
            return HttpResponseServerError(msg)

class UpdatePaymentDone(generic.TemplateView):
    template_name = 'billing/update_pmt_info_done.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
