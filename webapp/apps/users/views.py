from django.urls import reverse_lazy
from django.views import generic, View
from django.views.generic.edit import FormView
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.contrib.auth import get_user_model

from webapp.apps.billing.utils import USE_STRIPE

from .forms import UserCreationForm, CancelSubscriptionForm, DeleteUserForm
from .models import is_profile_active, Project


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


class UserProfile(View):
    template_name = "profile/profile_base.html"
    projects = Project.objects.all()

    def get(self, request, *args, **kwargs):
        username = kwargs["username"]
        print("user", request.user.username, username)
        if username == request.user.username:
            profile = request.user.profile
            return render(
                request,
                self.template_name,
                context={
                    "username": request.user.username,
                    "runs": profile.sims_breakdown(self.projects),
                    "cost_breakdown": profile.sims_breakdown(self.projects),
                },
            )
        User = get_user_model()
        if User.objects.filter(username=username):
            raise PermissionDenied()
        else:
            raise Http404()


class UserSettings(View):
    template_name = ("registration/settings_base.html",)

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
