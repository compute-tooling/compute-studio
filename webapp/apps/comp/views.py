import itertools
from io import BytesIO
from zipfile import ZipFile
import json
import time
import os

from bokeh.resources import CDN
import requests

from django.utils import timezone
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

import s3like

from webapp.settings import DEBUG

from webapp.apps.billing.models import SubscriptionItem, UsageRecord
from webapp.apps.billing.utils import USE_STRIPE, ChargeRunMixin, has_payment_method
from webapp.apps.users.models import Project, is_profile_active

from .abstractrouter import AbstractRouterView
from .constants import WEBAPP_VERSION
from .forms import InputsForm
from .models import Simulation
from .compute import Compute, JobFailError
from .ioutils import get_ioutils
from .parser import APIParser
from .submit import handle_submission, BadPost, APISubmit
from .tags import TAGS
from .exceptions import AppError, ValidationError
from .serializers import OutputsSerializer, InputsSerializer


OBJ_STORAGE_URL = os.environ.get("OBJ_STORAGE_URL")


class InputsMixin:
    """
    Define class attributes and common methods for inputs form views.
    """

    template_name = "comp/inputs_form.html"
    has_errors = False
    webapp_version = WEBAPP_VERSION

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


class InputsView(InputsMixin, View):
    projects = Project.objects.all()

    def get(self, request, *args, **kwargs):
        print("method=GET", request.GET, kwargs)
        project = self.projects.get(
            owner__user__username=kwargs["username"], title=kwargs["title"]
        )
        ioutils = get_ioutils(project)
        inputs_form = InputsForm(project, ioutils.displayer)
        # set cleaned_data with is_valid call
        inputs_form.is_valid()
        inputs_form.clean()
        context = self.project_context(request, project)
        return self._render_inputs_form(request, project, inputs_form, ioutils, context)

    def post(self, request, *args, **kwargs):
        print("method=POST", request.POST)
        compute = Compute()
        project = self.projects.get(
            owner__user__username=kwargs["username"], title=kwargs["title"]
        )
        ioutils = get_ioutils(project)
        if request.POST.get("reset", ""):
            inputs_form = InputsForm(project, ioutils.displayer, request.POST.dict())
            if inputs_form.is_valid():
                inputs_form.clean()
            else:
                inputs_form = InputsForm(project, ioutils.displayer)
                inputs_form.is_valid()
                inputs_form.clean()
            context = self.project_context(request, project)
            return self._render_inputs_form(
                request, project, inputs_form, ioutils, context
            )

        try:
            result = handle_submission(request, project, ioutils, compute)
        except AppError as ae:
            try:
                send_mail(
                    f"COMP AppError",
                    f"An error has occurred:\n {ae.parameters}\n causing: {ae.traceback}\n user:{request.user.username}\n project: {project.app_url}.",
                    "henrymdoupe@gmail.com",
                    ["henrymdoupe@gmail.com"],
                    fail_silently=True,
                )
            # Http 401 exception if mail credentials are not set up.
            except Exception as e:
                pass
            return render(
                request,
                "comp/app_error.html",
                context={"params": ae.parameters, "traceback": ae.traceback},
            )

        # case where validation failed
        if isinstance(result, BadPost):
            return result.http_response

        # No errors--submit to model
        if result.save is not None:
            print("redirecting...", result.save.runmodel_instance.get_absolute_url())
            return redirect(result.save.runmodel_instance)
        else:
            inputs_form = result.submit.form
            valid_meta_params = result.submit.valid_meta_params
            has_errors = result.submit.has_errors

        ioutils.displayer.meta_parameters = valid_meta_params
        context = dict(
            form=inputs_form,
            default_form=ioutils.displayer.defaults(flat=False),
            webapp_version=self.webapp_version,
            has_errors=self.has_errors,
            **self.project_context(request, project),
        )
        return render(request, self.template_name, context)

    def _render_inputs_form(self, request, project, inputs_form, ioutils, context):
        valid_meta_params = {}
        parsed_meta_parameters = ioutils.displayer.parsed_meta_parameters()
        for mp_name in parsed_meta_parameters.parameters:
            valid_meta_params[mp_name] = inputs_form.cleaned_data[mp_name]
        ioutils.displayer.meta_parameters = valid_meta_params
        context = dict(
            form=inputs_form,
            default_form=ioutils.displayer.defaults(flat=False),
            webapp_version=self.webapp_version,
            has_errors=self.has_errors,
            **context,
        )
        return render(request, self.template_name, context)


class RequiresLoginInputsView(InputsView):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_profile_active, login_url="/users/login/"))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RequiresPmtInputsView(InputsView):
    """
    This class adds a paywall to the _InputsView class.
    """

    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_profile_active, login_url="/users/login/"))
    @method_decorator(
        user_passes_test(has_payment_method, login_url="/billing/update/")
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RouterView(InputsMixin, AbstractRouterView):
    projects = Project.objects.all()
    placeholder_template = "comp/model_placeholder.html"
    payment_view = RequiresPmtInputsView
    login_view = RequiresLoginInputsView

    def unauthorized_get(self, request, project):
        context = self.project_context(request, project)
        return render(request, self.placeholder_template, context)

    def get(self, request, *args, **kwargs):
        return self.handle(request, True, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.handle(request, False, *args, **kwargs)


class GetOutputsObjectMixin:
    def get_object(self, model_pk, username, title):
        return get_object_or_404(
            self.model,
            model_pk=model_pk,
            project__title=title,
            project__owner__user__username=username,
        )


class EditInputsView(GetOutputsObjectMixin, InputsMixin, View):
    model = Simulation

    def get(self, request, *args, **kwargs):
        print("edit method=GET", request.GET)
        self.object = self.get_object(
            kwargs["model_pk"], kwargs["username"], kwargs["title"]
        )
        project = self.object.project
        ioutils = get_ioutils(project)
        parsed_meta_parameters = ioutils.displayer.parsed_meta_parameters()
        initial = {}
        for k, v in self.object.inputs.raw_gui_inputs.items():
            if v not in ("", None):
                initial[k] = v
        for mp_name in parsed_meta_parameters.parameters:
            mp_val = self.object.inputs.meta_parameters.get(mp_name, None)
            if mp_val is not None:
                initial[mp_name] = mp_val
        inputs_form = InputsForm(project, ioutils.displayer, initial=initial)
        # clean data with is_valid call.
        inputs_form.is_valid()
        unknown_fields = False
        for field, val in inputs_form.initial.items():
            if val not in (None, ""):
                try:
                    inputs_form.fields[field].initial = val
                except KeyError:
                    unknown_fields = True
        unknown_fields = mark_safe(unknown_fields)
        # is_bound is turned off so that the `initial` data is displayed.
        # Note that form is validated and cleaned with is_bound call.
        inputs_form.is_bound = False
        context = self.project_context(request, project)
        context.update(
            {
                "object": self.object,
                "unknown_fields": unknown_fields,
                "model_parameters": self.object.inputs.display_params,
            }
        )
        return self._render_inputs_form(request, project, ioutils, inputs_form, context)

    def _render_inputs_form(self, request, project, ioutils, inputs_form, context):
        valid_meta_params = {}
        parsed_meta_parameters = ioutils.displayer.parsed_meta_parameters()
        for mp_name in parsed_meta_parameters.parameters:
            valid_meta_params[mp_name] = (
                inputs_form.initial.get(mp_name, None) or inputs_form[mp_name].data
            )
        ioutils.displayer.meta_parameters = valid_meta_params
        context = dict(
            form=inputs_form,
            default_form=ioutils.displayer.defaults(flat=False),
            webapp_version=self.webapp_version,
            has_errors=self.has_errors,
            **context,
        )
        return render(request, self.template_name, context)


class RecordOutputsMixin(ChargeRunMixin):
    def record_outputs(self, sim, data):
        self.charge_run(sim, data["meta"], use_stripe=USE_STRIPE)
        sim.meta_data = data["meta"]
        sim.model_version = data.get("model_version", "NA")
        # successful run
        if data["status"] == "SUCCESS":
            sim.status = "SUCCESS"
            sim.outputs = data["result"]
            sim.save()
        # failed run, exception is caught
        else:
            sim.status = "FAIL"
            sim.traceback = data["traceback"]
            sim.save()


class OutputsAPIView(RecordOutputsMixin, APIView):
    """
    API endpoint used by the workers to update the Simulation object with the
    simulation results.
    """

    def put(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.username == "comp-api-user":
            ser = OutputsSerializer(data=request.data)
            if ser.is_valid():
                data = ser.validated_data
                sim = get_object_or_404(Simulation, job_id=data["job_id"])
                if sim.status == "PENDING":
                    self.record_outputs(sim, data)
                return Response(status=status.HTTP_200_OK)
            else:
                return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)


class ETAMixin:
    def compute_eta(self, reference_time):
        exp_comp_dt = self.object.exp_comp_datetime
        dt = exp_comp_dt - reference_time
        exp_num_minutes = dt.total_seconds() / 60.0
        exp_num_minutes = round(exp_num_minutes, 2)
        exp_num_minutes = exp_num_minutes if exp_num_minutes > 0 else 0
        return exp_num_minutes


class OutputsView(ETAMixin, GetOutputsObjectMixin, RecordOutputsMixin, DetailView):
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
                f"COMP Sim fail",
                f"An error has occurred at {username}/{title}/{model_pk}",
                "henrymdoupe@gmail.com",
                ["henrymdoupe@gmail.com"],
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
        compute = Compute()
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
        else:
            job_id = str(self.object.job_id)
            try:
                job_ready = compute.results_ready(job_id)
            except JobFailError as jfe:
                self.object.traceback = ""
                self.object.save()
                return self.fail(model_pk, username, title)
            # something happened and the exception was not caught
            if job_ready == "FAIL":
                result = compute.get_results(job_id)
                if result["traceback"]:
                    traceback_ = result["traceback"]
                else:
                    traceback_ = "Error: The traceback for this error is unavailable."
                self.object.traceback = traceback_
                self.object.status = "WORKER_FAILURE"
                self.object.save()
                return self.fail(model_pk, username, title)
            else:
                if request.method == "POST":
                    # if not ready yet, insert number of minutes remaining
                    exp_num_minutes = self.compute_eta(timezone.now())
                    orig_eta = self.compute_eta(self.object.creation_date)
                    return JsonResponse(
                        {"eta": exp_num_minutes, "origEta": orig_eta}, status=202
                    )
                else:
                    context = {"eta": "100", "origEta": "0"}
                    return render(request, "comp/not_ready.html", context)

    def render_outputs(self, request):
        return {"v0": self.render_v0, "v1": self.render_v1}[
            self.object.outputs["version"]
        ](request)

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

    def render_v1(self, request):
        renderable = {"renderable": self.object.outputs["outputs"]["renderable"]}
        outputs = s3like.read_from_s3like(renderable)
        return render(
            request,
            "comp/outputs/v1/sim_detail.html",
            {
                "outputs": outputs,
                "object": self.object,
                "result_header": "Results",
                "bokeh_scripts": {
                    "cdn_js": CDN.js_files[0],
                    "cdn_css": CDN.css_files[0],
                    "widget_js": CDN.js_files[1],
                    "widget_css": CDN.css_files[1],
                },
            },
        )

    def is_from_file(self):
        if hasattr(self.object.inputs, "raw_gui_field_inputs"):
            return not self.object.inputs.raw_gui_field_inputs
        else:
            return False

    def inputs_to_display(self):
        if hasattr(self.object.inputs, "inputs_file"):
            return json.dumps(self.object.inputs.inputs_file, indent=2)
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
        endpoint = s3like.OBJ_STORAGE_EDGE.replace("https://", "")
        url = f"https://{s3like.OBJ_STORAGE_BUCKET}.{endpoint}/{zip_loc}"
        zip_resp = requests.get(url)
        zip_data = BytesIO(zip_resp.content)
        resp = HttpResponse(zip_data.getvalue(), content_type="application/zip")
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


class InputsAPIView(APIView):
    queryset = Project.objects.all()

    def get_inputs(self, kwargs, meta_parameters=None):
        project = get_object_or_404(
            self.queryset,
            owner__user__username=kwargs["username"],
            title=kwargs["title"],
        )
        ioutils = get_ioutils(project)
        if meta_parameters is not None:
            try:
                parsed_mp = ioutils.displayer.parsed_meta_parameters()
                ioutils.displayer.meta_parameters = parsed_mp.validate(
                    meta_parameters, throw_errors=True
                )
            except ValidationError as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        meta_parameters, model_parameters = ioutils.displayer.package_defaults()
        return Response(
            {"meta_parameters": meta_parameters, "model_parameters": model_parameters}
        )

    def get(self, request, *args, **kwargs):
        print("sim api method=GET", request.GET, kwargs)
        return self.get_inputs(kwargs)

    def post(self, request, *args, **kwargs):
        print("sim api method=GET", request.GET, kwargs)
        ser = InputsSerializer(data=request.data)
        if ser.is_valid():
            data = ser.validated_data
            if "meta_parameters" in data:
                meta_parameters = data["meta_parameters"]
            else:
                meta_parameters = {}
            return self.get_inputs(kwargs, meta_parameters)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateAPIView(APIView):
    queryset = Project.objects.all()

    def post(self, request, *args, **kwargs):
        compute = Compute()
        project = get_object_or_404(
            self.queryset,
            owner__user__username=kwargs["username"],
            title=kwargs["title"],
        )
        ioutils = get_ioutils(project, Parser=APIParser)

        try:
            result = handle_submission(
                request, project, ioutils, compute, submit_class=APISubmit
            )
        except AppError as ae:
            try:
                send_mail(
                    f"COMP AppError",
                    (
                        f"An error has occurred:\n {ae.parameters}\n causing: "
                        f"{ae.traceback}\n user:{request.user.username}\n "
                        f"project: {project.app_url}."
                    ),
                    "henrymdoupe@gmail.com",
                    ["henrymdoupe@gmail.com"],
                    fail_silently=True,
                )
            # Http 401 exception if mail credentials are not set up.
            except Exception as e:
                pass

            return Response(ae.traceback, status=status.HTTP_400_BAD_REQUEST)

        # case where validation failed
        if isinstance(result, BadPost):
            return result.http_response

        # No errors--submit to model
        if result.save is not None:
            print("redirecting...", result.save.runmodel_instance.get_absolute_url())
            data = {
                "meta_parameters": result.submit.model.meta_parameters,
                "model_parameters": result.submit.model.model_parameters,
                "inputs_file": result.submit.model.inputs_file,
                "outputs_url": result.save.runmodel_instance.get_absolute_api_url(),
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response(
                result.submit.model.errors_warnings, status=status.HTTP_400_BAD_REQUEST
            )


class DetailAPIView(ETAMixin, GetOutputsObjectMixin, APIView):
    model = Simulation

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(
            kwargs["model_pk"], kwargs["username"], kwargs["title"]
        )
        inputs = InputsSerializer(self.object.inputs)
        if self.object.outputs:
            downloadable = {
                "downloadable": self.object.outputs["outputs"]["downloadable"]
            }
            outputs = s3like.read_from_s3like(downloadable)
            return Response(
                {"outputs": outputs, "inputs": inputs.data}, status=status.HTTP_200_OK
            )
        elif self.object.traceback is not None:
            return Response(
                {"traceback": self.object.traceback, "inputs": inputs.data},
                status=status.HTTP_200_OK,
            )
        job_id = str(self.object.job_id)
        compute = Compute()
        try:
            job_ready = compute.results_ready(job_id)
        except JobFailError as jfe:
            self.object.traceback = ""
            self.object.save()
            return Response(
                {"error": "model error"}, status=status.HTTP_400_BAD_REQUEST
            )
        # something happened and the exception was not caught
        if job_ready == "FAIL":
            result = compute.get_results(job_id)
            if result["traceback"]:
                traceback_ = result["traceback"]
            else:
                traceback_ = "Error: The traceback for this error is unavailable."
            self.object.traceback = traceback_
            self.object.status = "WORKER_FAILURE"
            self.object.save()
            return Response(
                {"error": "model error"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "eta": self.compute_eta(timezone.now()),
                "inputs": inputs.data,
                "outputs": None,
            },
            status=status.HTTP_200_OK,
        )
