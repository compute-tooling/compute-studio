import os

import stripe

from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse

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