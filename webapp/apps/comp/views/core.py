from django.views.generic.base import View
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from webapp.apps.billing.utils import has_payment_method, ChargeRunMixin, USE_STRIPE
from webapp.apps.users.models import is_profile_active


class InputsMixin:
    """
    Define class attributes and common methods for inputs form views.
    """

    template_name = "comp/inputs_form.html"
    has_errors = False
    webapp_version = ""

    def project_context(self, request, project):
        user = request.user
        provided_free = project.sponsor is not None
        user_can_run = self.user_can_run(user, project)
        rate = round(project.server_cost, 2)
        exp_cost, exp_time = project.exp_job_info(adjust=True)

        context = {
            "rate": f"${rate}/hour",
            "project_name": project.title,
            "owner": project.owner.user.username,
            "app_description": project.safe_description,
            "app_oneliner": project.oneliner,
            "user_can_run": user_can_run,
            "exp_cost": f"${exp_cost}",
            "exp_time": f"{exp_time} seconds",
            "provided_free": provided_free,
            "app_url": project.app_url,
        }
        return context

    def user_can_run(self, user, project):
        """
        The user_can_run method determines if the user has sufficient
        credentials for running this model. The result of this method is
        used to determine which buttons and information is displayed to the
        user regarding their credential status (not logged in v. logged in
        without payment v. logged in with payment). Note that this is actually
        enforced by RequiresLoginInputsView and RequiresPmtView.
        """
        # only requires login and active account.
        if project.sponsor is not None:
            return user.is_authenticated and is_profile_active(user)
        else:  # requires payment method too.
            return (
                user.is_authenticated
                and is_profile_active(user)
                and has_payment_method(user)
            )


class AbstractRouter:
    projects = None
    payment_view = None
    login_view = None

    def handle(self, request, is_get, *args, **kwargs):
        print("router handle", args, kwargs)
        project = get_object_or_404(
            self.projects,
            owner__user__username=kwargs["username"],
            title=kwargs["title"],
        )
        if project.status in ["updating", "live"]:
            if project.sponsor is None:
                return self.payment_view.as_view()(request, *args, **kwargs)
            else:
                return self.login_view.as_view()(request, *args, **kwargs)
        else:
            if is_get:
                return self.unauthorized_get(request, project)
            else:
                raise PermissionDenied()

    def unauthorized_get(self, request, project):
        return PermissionDenied()

    def get(self, request, *args, **kwargs):
        return self.handle(request, True, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.handle(request, False, *args, **kwargs)


class AbstractRouterView(AbstractRouter, View):
    pass


class AbstractRouterAPIView(AbstractRouter, APIView):
    def get(self, request, *args, **kwargs):
        return AbstractRouter.get(self, request._request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return AbstractRouter.post(self, request._request, *args, **kwargs)


class GetOutputsObjectMixin:
    def get_object(self, model_pk, username, title):
        return get_object_or_404(
            self.model,
            model_pk=model_pk,
            project__title=title,
            project__owner__user__username=username,
        )


class GetInputsObjectMixin:
    def get_object(self, inputs_pk, username, title):
        return get_object_or_404(
            self.model,
            pk=inputs_pk,
            project__title=title,
            project__owner__user__username=username,
        )


class RecordOutputsMixin(ChargeRunMixin):
    def record_outputs(self, sim, data):
        self.charge_run(sim, data["meta"], use_stripe=USE_STRIPE)
        sim.meta_data = data["meta"]
        sim.model_version = data.get("model_version", "NA")
        # successful run
        if data["status"] == "SUCCESS":
            sim.status = "SUCCESS"
            sim.outputs = {"outputs": data["outputs"], "version": data["version"]}
            sim.save()
        # failed run, exception is caught
        else:
            sim.status = "FAIL"
            sim.traceback = data["traceback"]
            sim.save()
