import os

import stripe

from django.views import View, generic
from django.shortcuts import render, redirect, reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseServerError
from django.urls import resolve, Resolver404
from django.utils.safestring import mark_safe

from webapp.apps.users.models import Project

from . import webhooks
from .models import (
    Customer,
    Product,
    Subscription,
    SubscriptionItem,
    UpdateStatus,
    timestamp_to_datetime,
)

from .utils import update_payment, has_payment_method

stripe.api_key = os.environ.get("STRIPE_SECRET")
wh_secret = os.environ.get("WEBHOOK_SECRET")

white_listed_urls = set(
    [
        # next urls for pro plan
        "/billing/upgrade/?selected_plan=pro",
        "/billing/upgrade/monthly/?selected_plan=pro",
        "/billing/upgrade/yearly/?selected_plan=pro",
        "/billing/upgrade/monthly/aftertrial/",
        "/billing/upgrade/yearly/aftertrial/",
        "/billing/upgrade/monthly/aftertrial/?selected_plan=pro",
        "/billing/upgrade/yearly/aftertrial/?selected_plan=pro",
    ]
)


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
    if upgrade_plan is not None and upgrade_plan.lower() not in ("free", "pro",):
        upgrade_plan = None

    selected_plan = request.GET.get("selected_plan", None)
    if selected_plan is not None and selected_plan.lower() not in ("free", "pro",):
        selected_plan = None
    return upgrade_plan, selected_plan


class Plans(View):
    template_name = "billing/upgrade_plan.html"
    default_duration = "yearly"

    def get(self, request, *args, **kwargs):
        current_plan = {"plan_duration": None, "name": "free"}
        if getattr(request.user, "customer", None) is not None:
            current_plan = request.user.customer.current_plan()

        if current_plan["name"] == "free":
            duration = self.default_duration
        else:
            duration = current_plan["plan_duration"]

        return redirect(
            reverse("upgrade_plan_duration", kwargs=dict(plan_duration=duration))
        )


class AutoUpgradeAfterTrial(View):
    template_name = "billing/auto_upgrade.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        banner_msg = None
        plan_duration = kwargs["plan_duration"]
        customer: Customer = getattr(request.user, "customer", None)
        next_url = request.GET.get("next", None)
        card_info = customer.card_info()
        si = customer.current_plan(as_dict=False)
        current_plan = customer.current_plan(si=si)
        _, selected_plan = parse_upgrade_params(request)

        sub: Subscription = si.subscription
        if not sub.is_trial():
            return redirect(
                reverse(
                    "upgrade_plan_duration",
                    kwargs=dict(plan_duration=current_plan["plan_duration"]),
                ),
            )

        trial_end = sub.trial_end.date()
        cancel_at = sub.cancel_at

        # User is still on trial but has already opted in.
        if sub.is_trial() and cancel_at is None:
            banner_msg = (
                f"You will continue to be on the {si.plan.nickname} after your trial "
                f"ends on {sub.trial_end.date()}. Thanks for opting-in and enjoy the rest of "
                f"your trial!"
            )
            return render(
                request,
                self.template_name,
                context={
                    "plan_duration": plan_duration,
                    "current_plan": current_plan,
                    "card_info": card_info,
                    "selected_plan": selected_plan,
                    "next": next_url,
                    "banner_msg": banner_msg,
                    "trial_end": trial_end,
                    "has_payment_method": has_payment_method(request.user),
                },
            )

        return render(
            request,
            self.template_name,
            context={
                "plan_duration": plan_duration,
                "current_plan": current_plan,
                "card_info": card_info,
                "selected_plan": selected_plan,
                "next": next_url,
                "banner_msg": banner_msg,
                "trial_end": trial_end,
                "cancel_at": cancel_at.date() if cancel_at is not None else None,
                "has_payment_method": has_payment_method(request.user),
            },
        )


class AutoUpgradeAfterTrialConfirm(View):
    template_name = "billing/upgrade_plan.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        banner_msg = None
        plan_duration = kwargs["plan_duration"]
        customer = getattr(request.user, "customer", None)
        next_url = request.GET.get("next", None)

        # Redirect user if they do not have payment info.
        if not has_payment_method(request.user):
            pmt_url = reverse("update_payment")
            pmt_url += (
                f"?next=/billing/upgrade/{plan_duration}/aftertrial/?selected_plan=pro"
            )
            return redirect(pmt_url)

        card_info = customer.card_info()

        current_si = customer.current_plan(as_dict=False)
        if (
            current_si is None  # no subscription to upgrade.
            or not current_si.subscription.is_trial()  # no trial for opt-in after ending.
            or current_si.subscription.cancel_at is None  # already opt-ed in.
        ):
            return redirect(
                reverse(
                    "upgrade_plan_duration", kwargs=dict(plan_duration=plan_duration)
                )
            )

        sub: Subscription = current_si.subscription

        # Get plan for Pro subscription corresponding to selected duration.
        product = Product.objects.get(name="Compute Studio Subscription")
        if plan_duration == "monthly":
            new_plan = product.plans.get(nickname="Monthly Pro Plan")
        else:
            new_plan = product.plans.get(nickname="Yearly Pro Plan")

        if current_si.plan != new_plan:
            stripe.SubscriptionItem.modify(
                current_si.stripe_id, plan=new_plan.stripe_id
            )
            current_si.plan = new_plan
            current_si.save()

        stripe_sub = stripe.Subscription.modify(
            current_si.subscription.stripe_id,
            cancel_at=None,
            cancel_at_period_end=False,
        )

        current_si.subscription.update_from_stripe_obj(stripe_sub)
        current_plan = customer.current_plan(si=current_si)

        banner_msg = (
            f"You will continue to be on the {current_si.plan.nickname} after your trial "
            f"ends on {sub.trial_end.date()}. Thanks for opting-in and enjoy the rest of "
            f"your trial!"
        )

        return render(
            request,
            self.template_name,
            context={
                "plan_duration": plan_duration,
                "current_plan": current_plan,
                "card_info": card_info,
                "selected_plan": None,
                "next": next_url,
                "banner_msg": banner_msg,
                "trial_end": current_si.subscription.trial_end.date(),
                "cancel_at": None,
                "has_payment_method": has_payment_method(request.user),
            },
        )


class UpgradePlan(View):
    template_name = "billing/upgrade_plan.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        banner_msg = None
        plan_duration = kwargs.get("plan_duration")
        upgrade_plan, selected_plan = parse_upgrade_params(request)
        customer = getattr(request.user, "customer", None)
        card_info = {"last4": None, "brand": None}
        current_plan = {"plan_duration": None, "name": "free"}
        next_url = request.GET.get("next", None)
        cancel_at_period_end = False
        cancel_at = None
        if next_url is not None:
            request.session["post_upgrade_url"] = next_url

        if customer is not None:
            card_info = customer.card_info()
            product = Product.objects.get(name="Compute Studio Subscription")
            current_plan = customer.current_plan()
            result = UpdateStatus.nochange
            new_plan = None

            if upgrade_plan == "free":
                new_plan = product.plans.get(nickname="Free Plan")
                result = customer.update_plan(new_plan)

            elif upgrade_plan == "pro":
                if plan_duration == "monthly":
                    new_plan = product.plans.get(nickname="Monthly Pro Plan")
                else:
                    new_plan = product.plans.get(nickname="Yearly Pro Plan")

                result = customer.update_plan(new_plan)

            current_si = customer.current_plan(as_dict=False)
            current_plan = customer.current_plan(si=current_si)

            if result != UpdateStatus.nochange and request.session.get(
                "post_upgrade_url"
            ):
                return redirect(request.session.pop("post_upgrade_url"))
            elif result != UpdateStatus.nochange:
                done_next_url = reverse(
                    "upgrade_plan_duration_done",
                    kwargs=dict(
                        plan_duration=current_plan["plan_duration"] or plan_duration
                    ),
                )
                return redirect(done_next_url)

            if current_si is not None:
                sub: Subscription = current_si.subscription
                if sub is not None and sub.cancel_at is not None and sub.is_trial():
                    banner_msg = mark_safe(
                        f"""
                        <p>Your free C/S Pro trial ends on {sub.trial_end.date()}.</p>
                        <p>
                        <a class="btn btn-primary" href="/billing/upgrade/yearly/aftertrial/">
                            <strong>Upgrade to C/S Pro after trial</strong>
                        </a>
                        </p>
                        """
                    )

                elif sub is not None and sub.cancel_at is not None:
                    banner_msg = (
                        f"Your {current_si.plan.nickname} will be downgraded "
                        f"to a Free account on {sub.current_period_end.date()}."
                    )
                    cancel_at = sub.cancel_at.date()

        return render(
            request,
            self.template_name,
            context={
                "plan_duration": plan_duration,
                "current_plan": current_plan,
                "card_info": card_info,
                "selected_plan": selected_plan,
                "next": next_url,
                "banner_msg": banner_msg,
                "cancel_at_period_end": cancel_at_period_end,
                "cancel_at": cancel_at,
                "has_payment_method": has_payment_method(request.user),
            },
        )


class UpgradePlanDone(View):
    template_name = "billing/upgrade_plan.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        # plan_duration optionally given in url: /billing/upgrade/[plan_duration]/
        plan_duration = kwargs.get("plan_duration", "monthly")
        cancel_at_period_end = False
        cancel_at = None

        customer = getattr(request.user, "customer", None)
        if customer is not None:
            card_info = customer.card_info()
            current_si = customer.current_plan(as_dict=False)
            current_plan = customer.current_plan(si=current_si, as_dict=True)
            plan_name = "Free Plan"
            sub = None

            if current_si is not None:
                plan_name = current_si.plan.nickname
                sub = current_si.subscription

            if sub is not None and sub.cancel_at_period_end:
                banner_msg = (
                    f"Your {current_si.plan.nickname} will be downgraded "
                    f"to a Free account on {sub.current_period_end.date()}."
                )
                cancel_at_period_end = True
                if sub.cancel_at is None:
                    sub.update_from_stripe_obj(
                        stripe.Subscription.retrieve(sub.stripe_id)
                    )
                cancel_at = sub.cancel_at.date()

            else:
                banner_msg = f"You are now on the {plan_name}."
        else:
            card_info = {"last4": None, "brand": None}
            current_plan = {"plan_duration": None, "name": "free"}
            plan_name = "Free Plan"
            banner_msg = f"You are now on the {plan_name}."

        return render(
            request,
            self.template_name,
            context={
                "plan_duration": plan_duration,
                "current_plan": current_plan,
                "card_info": card_info,
                "banner_msg": banner_msg,
                "cancel_at_period_end": cancel_at_period_end,
                "cancel_at": cancel_at,
                "has_payment_method": has_payment_method(request.user),
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
                        "amount": "{0:.2f}".format(invoice.total / 100),
                        "invoice_pdf": invoice.invoice_pdf,
                        "status": invoice.status,
                    }
                )
        return render(request, self.template_name, context={"invoices": invoices})
