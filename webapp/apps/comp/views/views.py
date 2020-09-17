import itertools
from io import BytesIO
from zipfile import ZipFile
import json
import time
import os

from bokeh.resources import CDN
import requests

from django.db import models
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin, DetailView
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404, JsonResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.utils.safestring import mark_safe


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import fsspec as fs
import cs_storage

from webapp.settings import DEBUG, DEFAULT_VIZ_HOST

from webapp.apps.billing.utils import has_payment_method
from webapp.apps.users.models import (
    Project,
    EmbedApproval,
    Deployment,
    is_profile_active,
    get_project_or_404,
)

from webapp.apps.comp.constants import WEBAPP_VERSION
from webapp.apps.comp import exceptions
from webapp.apps.comp.models import Inputs, Simulation, PendingPermission
from webapp.apps.comp.compute import Compute, JobFailError
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.tags import TAGS
from webapp.apps.comp.exceptions import AppError, ValidationError
from webapp.apps.comp.serializers import OutputsSerializer


from .core import InputsMixin, GetOutputsObjectMixin

BUCKET = os.environ.get("BUCKET")


class ModelPageView(InputsMixin, View):
    projects = Project.objects.all()
    template_name = "comp/model.html"

    def get(self, request, *args, **kwargs):
        print("method=GET", request.GET, kwargs)
        project = get_project_or_404(
            self.projects,
            user=request.user,
            owner__user__username__iexact=kwargs["username"],
            title__iexact=kwargs["title"],
        )
        context = self.project_context(request, project)
        context["show_readme"] = True
        return render(request, self.template_name, context)


class NewSimView(InputsMixin, View):
    projects = Project.objects.all()

    def get(self, request, *args, **kwargs):
        print("method=GET", request.GET, kwargs)
        project = get_project_or_404(
            self.projects,
            user=self.request.user,
            owner__user__username__iexact=kwargs["username"],
            title__iexact=kwargs["title"],
        )
        context = self.project_context(request, project)
        context["show_readme"] = False
        context["tech"] = project.tech
        if request.user.is_authenticated and getattr(request.user, "profile", None):
            sim = Simulation.objects.new_sim(user=request.user, project=project)
            return redirect(sim.get_absolute_edit_url())
        else:
            return render(request, self.template_name, context)


class PermissionPendingView(View):
    queryset = PendingPermission.objects.all()
    template = "comp/permissions/confirm.html"
    expired_template = "comp/permissions/expired.html"

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/users/login/?next={request.path}")
        pp = get_object_or_404(self.queryset, id=kwargs["id"])
        if (
            getattr(request.user, "profile", None) is not None
            and pp.profile == request.user.profile
        ):
            if pp.is_expired():
                return render(request, self.expired_template)
            else:
                return render(request, self.template, context={"pp": pp})

        raise PermissionDenied()


class PermissionGrantedView(View):
    queryset = PendingPermission.objects.all()
    expired_template = "comp/permissions/expired.html"

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/users/login/?next={request.path}")
        pp = get_object_or_404(self.queryset, id=kwargs["id"])
        if (
            getattr(request.user, "profile", None) is not None
            and pp.profile == request.user.profile
        ):
            try:
                pp.add_author()
                return redirect(pp.sim.get_absolute_url())
            except exceptions.PermissionExpiredException:
                return render(request, self.expired_template)

        raise PermissionDenied()


class EditSimView(GetOutputsObjectMixin, InputsMixin, View):
    model = Simulation

    def get(self, request, *args, **kwargs):
        print("edit method=GET", request.GET)
        self.object = self.get_object(
            kwargs["model_pk"], kwargs["username"], kwargs["title"]
        )
        if self.object.outputs_version() == "v0" and not request.path.endswith("edit/"):
            return redirect(self.object.get_absolute_url())
        project = self.object.project
        context = self.project_context(request, project)
        context["show_readme"] = False
        context["tech"] = project.tech
        context["sim"] = self.object.context(request=request)
        return render(request, self.template_name, context)


class VizView(InputsMixin, View):
    model = Project
    template_name = "comp/viz.html"

    def get(self, request, *args, **kwargs):
        print("viz method=GET", request.GET)
        project = get_object_or_404(
            self.model,
            owner__user__username__iexact=kwargs["username"],
            title__iexact=kwargs["title"],
        )
        if project.tech == "python-paramtools":
            return redirect(f"/{project.owner}/{project.title}/new/")
        context = self.project_context(request, project)
        if is_profile_active(request.user):
            owner = request.user.profile
        else:
            owner = None
        deployment, _ = Deployment.objects.get_or_create_deployment(
            project=project, name=kwargs.get("rd_name", "default"), owner=owner
        )
        context["show_readme"] = False
        context["tech"] = project.tech
        context["object"] = project
        context["deployment"] = deployment
        context["viz_host"] = DEFAULT_VIZ_HOST
        context["protocol"] = "https"
        return render(request, self.template_name, context)


class EmbedView(InputsMixin, View):
    model = EmbedApproval
    template_name = "comp/embed.html"

    def get(self, request, *args, **kwargs):
        print("embed method=GET", request.GET)
        embed_approval = get_object_or_404(
            EmbedApproval,
            project__owner__user__username__iexact=kwargs["username"],
            project__title__iexact=kwargs["title"],
            name__iexact=kwargs["ea_name"],
        )
        project = embed_approval.project
        deployment, _ = Deployment.objects.get_or_create_deployment(
            project=project, name=kwargs["ea_name"], embed_approval=embed_approval
        )

        context = {
            "object": project,
            "deployment": deployment,
            "protocol": "https",
            "viz_host": DEFAULT_VIZ_HOST,
        }
        response = render(request, self.template_name, context)

        response["Content-Security-Policy"] = f"frame-ancestors {embed_approval.url}"

        return response


class OutputsView(GetOutputsObjectMixin, DetailView):
    """
    This view is the single page of diplaying a progress bar for how
    close the job is to finishing, and then it will also display the
    job results if the job is done. Finally, it will render a 'job failed'
    page if the job has failed.

    Cases:
        case 1: result is ready and successful

        case 2: model run failed

        case 3: query results
          case 3a: all jobs have completed
          case 3b: not all jobs have completed
    """

    model = Simulation
    is_editable = True

    def fail(self, model_pk, username, title):
        try:
            send_mail(
                f"Compute Studio Sim fail",
                f"An error has occurred at {username}/{title}/{model_pk}",
                "notifications@compute.studio",
                ["hank@compute.studio"],
                fail_silently=True,
            )
        # Http 401 exception if mail credentials are not set up.
        except Exception as e:
            pass
            # if DEBUG:
            #     raise e
        return render(
            self.request, "comp/failed.html", {"traceback": self.object.traceback}
        )

    def dispatch(self, request, *args, **kwargs):
        model_pk, username, title = (
            kwargs["model_pk"],
            kwargs["username"],
            kwargs["title"],
        )
        self.object = self.get_object(model_pk, username, title)
        if self.object.outputs or self.object.aggr_outputs:
            return self.render_outputs(request)
        elif self.object.traceback is not None:
            return self.fail(model_pk, username, title)

    def render_outputs(self, request):
        return {"v0": self.render_v0, "v1": self.render_v1}[
            self.object.outputs["version"]
        ](request)

    def render_v1(self, request):
        return redirect(self.object.get_absolute_url())

    def render_v0(self, request):
        return render(
            request,
            "comp/outputs/v0/sim_detail.html",
            {
                "object": self.object,
                "result_header": "Results",
                "tags": TAGS[self.object.project.title],
            },
        )

    def is_from_file(self):
        if hasattr(self.object.inputs, "raw_gui_field_inputs"):
            return not self.object.inputs.raw_gui_field_inputs
        else:
            return False

    def inputs_to_display(self):
        if hasattr(self.object.inputs, "custom_adjustment"):
            return json.dumps(self.object.inputs.custom_adjustment, indent=2)
        else:
            return ""


class OutputsDownloadView(GetOutputsObjectMixin, View):
    model = Simulation

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(
            kwargs["model_pk"], kwargs["username"], kwargs["title"]
        )
        if not self.object.outputs:
            raise Http404
        return {"v0": self.render_v0, "v1": self.render_v1}[
            self.object.outputs["version"]
        ](request)

    def render_v0(self, request):
        # option to download the raw JSON for testing purposes.
        if request.GET.get("raw_json", False):
            return self.render_json()
        downloadables = list(
            itertools.chain.from_iterable(
                output["downloadable"] for output in self.object.outputs["outputs"]
            )
        )
        downloadables += list(
            itertools.chain.from_iterable(
                output["downloadable"] for output in self.object.outputs["aggr_outputs"]
            )
        )
        s = BytesIO()
        z = ZipFile(s, mode="w")
        for i in downloadables:
            z.writestr(i["filename"], i["text"])
        z.close()
        resp = HttpResponse(s.getvalue(), content_type="application/zip")
        resp[
            "Content-Disposition"
        ] = f"attachment; filename={self.object.zip_filename()}"
        return resp

    def render_v1(self, request):
        if request.GET.get("raw_json", False):
            return self.render_json()
        zip_loc = self.object.outputs["outputs"]["downloadable"]["ziplocation"]
        with fs.open(f"gcs://{BUCKET}/{zip_loc}", "rb",) as f:
            resp = HttpResponse(f, content_type="application/zip")
            resp[
                "Content-Disposition"
            ] = f"attachment; filename={self.object.zip_filename()}"
            return resp

    def render_json(self):
        raw_json = json.dumps(
            {
                "meta": self.object.meta_data,
                "result": self.object.outputs,
                "status": "SUCCESS",  # keep success hardcoded for now.
            },
            indent=4,
        )
        resp = HttpResponse(raw_json, content_type="text/plain")
        resp[
            "Content-Disposition"
        ] = f"attachment; filename={self.object.json_filename()}"
        return resp


class DataView(View):
    def get(self, request, *args, **kwargs):
        data_id = kwargs["data_id"]

        if data_id.endswith(".png"):
            data_id = data_id[:-4]

        self.object = Simulation.objects.get_object_from_screenshot(
            data_id, http_404_on_fail=True
        )

        if not self.object.has_read_access(request.user):
            raise PermissionDenied()

        pic = cs_storage.read_screenshot(kwargs["data_id"])

        return HttpResponse(pic, content_type="image/png")
