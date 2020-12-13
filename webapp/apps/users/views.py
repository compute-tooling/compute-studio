from django.urls import reverse_lazy, reverse
from django.views import generic, View
from django.views.generic.edit import FormView
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.contrib.auth import get_user_model, login
from django.utils.safestring import mark_safe

from rest_framework.views import APIView
from rest_framework.response import Response

from webapp.settings import USE_STRIPE

from .forms import UserCreationForm, CancelSubscriptionForm, DeleteUserForm
from .models import is_profile_active, Project, create_profile_from_user


from django.dispatch import receiver

from allauth.account.signals import user_signed_up


@receiver(user_signed_up)
def user_signed_up_callback(request, user, **kwargs):
    create_profile_from_user(user)


class SignUp(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("home")
    template_name = "registration/signup.html"

    def get_success_url(self):
        if self.request.GET.get("next"):
            return self.request.GET.get("next")

        return super().get_success_url()

    def form_valid(self, form):
        res = super().form_valid(form)
        login(self.request, self.object, "django.contrib.auth.backends.ModelBackend")
        return res

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["use_stripe"] = USE_STRIPE
        return context


class UserSettings(View):
    template_name = ("registration/settings.html",)

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        banner_msg = None
        if getattr(request.user, "customer", None) is not None:
            current_si = request.user.customer.current_plan(as_dict=False)
            if current_si is not None and current_si.subscription.is_trial():
                banner_msg = mark_safe(
                    f"""
                        <p>Your free C/S Pro trial ends on {current_si.subscription.trial_end.date()}.</p>
                        <p>
                        <a class="btn btn-primary" href="/billing/upgrade/yearly/aftertrial/">
                            <strong>Upgrade to C/S Pro after trial</strong>
                        </a>
                        </p>
                        """
                )

        return render(
            request,
            self.template_name,
            context={"username": request.user.username, "banner_msg": banner_msg},
        )


class CancelSubscription(generic.edit.UpdateView):
    template_name = "registration/cancel_subscription.html"
    form_class = CancelSubscriptionForm
    success_url = reverse_lazy("cancel_subscription_done")

    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_profile_active))
    def get(self, request, *args, **kwargs):
        return super().get(self, request, *args, **kwargs)

    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_profile_active))
    def post(self, request, *args, **kwargs):
        return super().post(self, request, *args, **kwargs)

    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_profile_active))
    def put(self, request, *args, **kwargs):
        return super().put(self, request, *args, **kwargs)

    def get_object(self):
        return self.request.user


class CancelSubscriptionDone(generic.TemplateView):
    template_name = "registration/cancel_subscription_done.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class DeleteUser(generic.edit.UpdateView):
    template_name = "registration/delete_user.html"
    form_class = DeleteUserForm
    success_url = reverse_lazy("delete_user_done")

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        return super().get(self, request, *args, **kwargs)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        return super().post(self, request, *args, **kwargs)

    @method_decorator(login_required)
    def put(self, request, *args, **kwargs):
        return super().put(self, request, *args, **kwargs)

    def get_object(self):
        return self.request.user


class DeleteUserDone(generic.TemplateView):
    template_name = "registration/delete_user_done.html"

    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
