from django.views.generic.base import View
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from webapp.apps.users.permissions import RequiresActive, RequiresPayment

from webapp.settings import USE_STRIPE
from webapp.apps.billing.utils import has_payment_method
from webapp.apps.users.models import is_profile_active, get_project_or_404


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
        }
        return context


class AbstractRouter:
    projects = None
    payment_view = None
    login_view = None

    def handle(self, request, action, *args, **kwargs):
        print("router handle", args, kwargs)
        project = get_project_or_404(
            self.projects,
            user=request.user,
            owner__user__username__iexact=kwargs["username"],
            title__iexact=kwargs["title"],
        )
        if project.status == "running":
            if project.sponsor is None:
                return self.payment_view.as_view()(request, *args, **kwargs)
            else:
                return self.login_view.as_view()(request, *args, **kwargs)
        else:
            raise Http404()

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
            # Throw 404 on private apps to keep their names secret.
            if not obj.project.has_read_access(self.request.user):
                raise Http404()
            raise PermissionDenied()
        return obj


class RecordOutputsMixin:
    def record_outputs(self, sim, data):
        sim.run_time = sum(data["meta"]["task_times"])
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
