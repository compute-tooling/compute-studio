from django.urls import reverse_lazy, reverse
from django.views import generic, View
from django.views.generic.edit import FormView
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response

from webapp.settings import USE_STRIPE
from webapp.apps.publish.views import GetProjectMixin

from .forms import UserCreationForm, CancelSubscriptionForm, DeleteUserForm
from .models import is_profile_active, Project, create_profile_from_user


from django.dispatch import receiver

from allauth.account.signals import user_signed_up


@receiver(user_signed_up)
def user_signed_up_callback(request, user, **kwargs):
    create_profile_from_user(user)


class SignUp(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"

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
        return render(
            request, self.template_name, context={"username": request.user.username}
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


class AccessStatusAPI(GetProjectMixin, APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        plan = {"name": "free", "plan_duration": None}
        if user.is_authenticated and user.profile:
            user_status = user.profile.status
            username = user.username
            if getattr(user, "customer", None) is not None:
                plan = user.customer.current_plan()
        else:
            user_status = "anon"
            username = None

        if kwargs:
            project = self.get_object(**kwargs)
            exp_cost, exp_time = project.exp_job_info(adjust=True)
            if user.is_authenticated and user.profile:
                can_run = user.profile.can_run(project)
                can_write_project = project.has_write_access(user)
            else:
                can_run = False
                can_write_project = False

            return Response(
                {
                    "is_sponsored": project.is_sponsored,
                    "sponsor_message": project.sponsor_message,
                    "user_status": user_status,
                    "can_run": can_run,
                    "can_write_project": can_write_project,
                    "server_cost": project.server_cost,
                    "exp_cost": exp_cost,
                    "exp_time": exp_time,
                    "api_url": reverse("access_project", kwargs=kwargs),
                    "username": username,
                    "plan": plan,
                }
            )
        else:
            return Response(
                {
                    "user_status": user_status,
                    "api_url": reverse("access_status"),
                    "username": username,
                    "plan": plan,
                }
            )
