import itertools
from io import BytesIO
from zipfile import ZipFile
import json

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

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from webapp.settings import DEBUG

from webapp.apps.billing.models import SubscriptionItem, UsageRecord
from webapp.apps.billing.utils import USE_STRIPE, ChargeRunMixin, has_payment_method
from webapp.apps.users.models import Project, is_profile_active

from webapp.apps.contrib.ioregister import register

from .constants import WEBAPP_VERSION
from .forms import InputsForm
from .models import Simulation
from .compute import Compute, JobFailError
from .displayer import Displayer
from .submit import handle_submission, BadPost
from .tags import TAGS
from .exceptions import AppError
from .serializers import OutputsSerializer


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


class RouterView(InputsMixin, View):
    projects = Project.objects.all()
    placeholder_template = "comp/model_placeholder.html"

    def handle(self, request, is_get, *args, **kwargs):
        print("router handle", args, kwargs)
        project = get_object_or_404(
            self.projects,
            owner__user__username=kwargs["username"],
            title=kwargs["title"],
        )
        if project.status in ["updating", "live"]:
            if project.sponsor is None:
                return RequiresPmtInputsView.as_view()(request, *args, **kwargs)
            else:
                return RequiresLoginInputsView.as_view()(request, *args, **kwargs)
        else:
            if is_get:
                context = self.project_context(request, project)
                return render(request, self.placeholder_template, context)
            else:
                raise PermissionDenied()

    def get(self, request, *args, **kwargs):
        return self.handle(request, True, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.handle(request, False, *args, **kwargs)


class InputsView(InputsMixin, View):
    projects = Project.objects.all()

    def get(self, request, *args, **kwargs):
        print("method=GET", request.GET, kwargs)
        project = self.projects.get(
            owner__user__username=kwargs["username"], title=kwargs["title"]
        )
        ioclasses = register[project.inputs_style]
        inputs_form = InputsForm(project, ioclasses)
        # set cleaned_data with is_valid call
        inputs_form.is_valid()
        inputs_form.clean()
        context = self.project_context(request, project)
        return self._render_inputs_form(
            request, project, inputs_form, ioclasses, context
        )

    def post(self, request, *args, **kwargs):
        print("method=POST", request.POST)
        compute = Compute()
        project = self.projects.get(
            owner__user__username=kwargs["username"], title=kwargs["title"]
        )
        ioclasses = register[project.inputs_style]

        if request.POST.get("reset", ""):
            inputs_form = InputsForm(project, ioclasses, request.POST.dict())
            if inputs_form.is_valid():
                inputs_form.clean()
            else:
                inputs_form = InputsForm(project, ioclasses)
                inputs_form.is_valid()
                inputs_form.clean()
            context = self.project_context(request, project)
            return self._render_inputs_form(
                request, project, inputs_form, ioclasses, context
            )

        try:
            result = handle_submission(request, project, ioclasses, compute)
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
                if not DEBUG:
                    raise e
            return render(
                request,
                "comp/app_error.html",
                context={"params": ae.parameters, "traceback": ae.traceback},
            )

        # case where validation failed
        if isinstance(result, BadPost):
            return submission.http_response_404

        # No errors--submit to model
        if result.save is not None:
            print("redirecting...", result.save.runmodel_instance.get_absolute_url())
            return redirect(result.save.runmodel_instance)
        else:
            inputs_form = result.submit.form
            valid_meta_params = result.submit.valid_meta_params
            has_errors = result.submit.has_errors

        displayer = ioclasses.Displayer(project, ioclasses, **valid_meta_params)
        context = dict(
            form=inputs_form,
            default_form=displayer.defaults(flat=False),
            webapp_version=self.webapp_version,
            has_errors=self.has_errors,
            **self.project_context(request, project),
        )
        return render(request, self.template_name, context)

    def _render_inputs_form(self, request, project, inputs_form, ioclasses, context):
        valid_meta_params = {}
        for mp in project.parsed_meta_parameters.parameters:
            valid_meta_params[mp.name] = inputs_form.cleaned_data[mp.name]
        displayer = ioclasses.Displayer(project, ioclasses, **valid_meta_params)
        context = dict(
            form=inputs_form,
            default_form=displayer.defaults(flat=False),
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
        ioclasses = register[project.inputs_style]

        initial = {}
        for k, v in self.object.inputs.raw_gui_inputs.items():
            if v not in ("", None):
                initial[k] = v
        for mp in project.parsed_meta_parameters.parameters:
            mp_val = self.object.inputs.meta_parameters.get(mp.name, None)
            if mp_val is not None:
                initial[mp.name] = mp_val

        inputs_form = InputsForm(project, ioclasses, initial=initial)
        # clean data with is_valid call.
        inputs_form.is_valid()
        # is_bound is turned off so that the `initial` data is displayed.
        # Note that form is validated and cleaned with is_bound call.
        inputs_form.is_bound = False
        context = self.project_context(request, project)
        return self._render_inputs_form(
            request, project, ioclasses, inputs_form, context
        )

    def post(self, request, *args, **kwargs):
        return HttpResponseNotFound("<h1>Post not allowed to edit page</h1>")

    def _render_inputs_form(self, request, project, ioclasses, inputs_form, context):
        valid_meta_params = {}
        for mp in project.parsed_meta_parameters.parameters:
            valid_meta_params[mp.name] = (
                inputs_form.initial.get(mp.name, None) or inputs_form[mp.name].data
            )
        displayer = ioclasses.Displayer(project, ioclasses, **valid_meta_params)
        context = dict(
            form=inputs_form,
            default_form=displayer.defaults(flat=False),
            webapp_version=self.webapp_version,
            has_errors=self.has_errors,
            **context,
        )
        return render(request, self.template_name, context)


class RecordOutputsMixin(ChargeRunMixin):
    def record_outputs(self, sim, data):
        self.charge_run(sim, data["meta"], use_stripe=USE_STRIPE)
        sim.meta_data = data["meta"]
        # successful run
        if data["status"] == "SUCCESS":
            sim.outputs = data["result"]["outputs"]
            sim.aggr_outputs = data["result"]["aggr_outputs"]
            sim.save()
        # failed run, exception is caught
        else:
            sim.traceback = data["traceback"]
            sim.save()


class OutputsAPIView(RecordOutputsMixin, APIView):
    """
    API endpoint used by the workers to update the Simulation object with the
    simulation results.
    """

    def put(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.username == "comp-api":
            ser = OutputsSerializer(data=request.data)
            if ser.is_valid():
                data = ser.validated_data
                sim = Simulation.objects.get(job_id=data["job_id"])
                self.record_outputs(sim, data)
                return Response(status=status.HTTP_200_OK)
            else:
                return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)


class OutputsView(GetOutputsObjectMixin, RecordOutputsMixin, DetailView):
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
            if not DEBUG:
                raise e
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
            return render(
                request,
                "comp/sim_detail.html",
                {
                    "object": self.object,
                    "result_header": "Results",
                    "tags": TAGS[self.object.project.title],
                },
            )
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
                result = compute.get_results(job_id, job_failure=True)
                if not result["traceback"]:
                    error_msg = "Error: stack trace for this error is " "unavailable"
                val_err_idx = error_msg.rfind("Error")
                error_contents = error_msg[val_err_idx:].replace(" ", "&nbsp;")
                self.object.traceback = error_contents
                self.object.save()
                return self.fail(model_pk, username, title)
            elif job_ready == "YES":
                try:
                    results = compute.get_results(job_id)
                except Exception as e:
                    self.object.traceback = str(e)
                    self.object.save()
                    return self.fail(model_pk, username, title)
                self.record_outputs(self.object, results)
                if results["status"] != "SUCCESS":
                    return self.fail(model_pk, username, title)
                else:
                    return render(
                        request,
                        "comp/sim_detail.html",
                        {
                            "object": self.object,
                            "result_header": "Results",
                            "tags": TAGS[self.object.project.title],
                        },
                    )
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

    def compute_eta(self, reference_time):
        exp_comp_dt = self.object.exp_comp_datetime
        dt = exp_comp_dt - reference_time
        exp_num_minutes = dt.total_seconds() / 60.0
        exp_num_minutes = round(exp_num_minutes, 2)
        exp_num_minutes = exp_num_minutes if exp_num_minutes > 0 else 0
        return exp_num_minutes


class OutputsDownloadView(GetOutputsObjectMixin, View):
    model = Simulation

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(
            kwargs["model_pk"], kwargs["username"], kwargs["title"]
        )

        if (
            not (self.object.outputs or self.object.aggr_outputs)
            or self.object.traceback
        ):
            return redirect(self.object)

        # option to download the raw JSON for testing purposes.
        if request.GET.get("raw_json", False):
            raw_json = json.dumps(
                {
                    "meta": self.object.meta_data,
                    "result": {
                        "outputs": self.object.outputs,
                        "aggr_outputs": self.object.aggr_outputs,
                    },
                    "status": "SUCCESS",  # keep success hardcoded for now.
                },
                indent=4,
            )
            resp = HttpResponse(raw_json, content_type="text/plain")
            resp[
                "Content-Disposition"
            ] = f"attachment; filename={self.object.json_filename()}"
            return resp

        try:
            downloadables = list(
                itertools.chain.from_iterable(
                    output["downloadable"] for output in self.object.outputs
                )
            )
            downloadables += list(
                itertools.chain.from_iterable(
                    output["downloadable"] for output in self.object.aggr_outputs
                )
            )
        except KeyError:
            raise Http404
        if not downloadables:
            raise Http404

        s = BytesIO()
        z = ZipFile(s, mode="w")
        for i in downloadables:
            z.writestr(i["filename"], i["text"])
        z.close()
        resp = HttpResponse(s.getvalue(), content_type="application/zip")
        resp[
            "Content-Disposition"
        ] = f"attachment; filename={self.object.zip_filename()}"
        s.close()
        return resp
