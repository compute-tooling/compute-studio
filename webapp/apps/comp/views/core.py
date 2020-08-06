from django.views.generic.base import View
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from webapp.apps.users.permissions import RequiresActive, RequiresPayment

from webapp.settings import USE_STRIPE
from webapp.apps.billing.utils import has_payment_method, ChargeRunMixin
from webapp.apps.users.models import is_profile_active


class InputsMixin:
    """
    Define class attributes and common methods for inputs form views.
    """

    template_name = "comp/inputs_form.html"
    has_errors = False

    def project_context(self, request, project):
        context = {
            "project_status": project.status,
            "project_name": project.title,
            "owner": project.owner.user.username,
            "app_description": project.safe_description,
            "app_oneliner": project.oneliner,
            "app_url": project.app_url,
            "visualizations": project.visualizations.all(),
        }
        return context


class AbstractRouter:
    projects = None
    payment_view = None
    login_view = None

    def handle(self, request, action, *args, **kwargs):
        print("router handle", args, kwargs)
        project = get_object_or_404(
            self.projects,
            owner__user__username__iexact=kwargs["username"],
            title__iexact=kwargs["title"],
        )

        if project.status in ["updating", "live"]:
            if project.sponsor is None:
                return self.payment_view.as_view()(request, *args, **kwargs)
            else:
                return self.login_view.as_view()(request, *args, **kwargs)
        else:
            if action == "GET":
                return self.unauthenticated_get(request, *args, **kwargs)
            else:
                raise PermissionDenied()

    def unauthenticated_get(self, request, *args, **kwargs):
        return PermissionDenied()

    def get(self, request, *args, **kwargs):
        return self.handle(request, "GET", *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.handle(request, "POST", *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.handle(request, "PUT", *args, **kwargs)


class AbstractRouterView(AbstractRouter, View):
    pass


class AbstractRouterAPIView(AbstractRouter, APIView):
    def get(self, request, *args, **kwargs):
        return AbstractRouter.get(self, request._request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return AbstractRouter.post(self, request._request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return AbstractRouter.put(self, request._request, *args, **kwargs)


class GetOutputsObjectMixin:
    def get_object(self, model_pk, username, title):
        obj = get_object_or_404(
            self.model,
            model_pk=model_pk,
            project__title__iexact=title,
            project__owner__user__username__iexact=username,
        )
        if not obj.has_read_access(self.request.user):
            raise PermissionDenied()
        return obj


class GetVizObjectMixin:
    def get_object(self, username, title, viz_title):
        obj = get_object_or_404(
            self.model,
            title=viz_title,
            project__title__iexact=title,
            project__owner__user__username__iexact=username,
        )
        # TODO: ...
        # if not obj.has_read_access(self.request.user):
        #     raise PermissionDenied()
        return obj


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
            if isinstance(sim.traceback, str) and len(sim.traceback) > 8000:
                sim.traceback = sim.traceback[:8000]
            sim.save()


class RequiresLoginPermissions:
    permission_classes = (IsAuthenticatedOrReadOnly & RequiresActive,)


class RequiresPmtPermissions:
    permission_classes = (IsAuthenticatedOrReadOnly & RequiresActive & RequiresPayment,)
