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

from webapp.apps.billing.models import SubscriptionItem, UsageRecord
from webapp.apps.billing.utils import USE_STRIPE, ChargeRunMixin
from webapp.apps.users.models import Project, is_profile_active

from webapp.apps.contrib.ioregister import register

from .constants import WEBAPP_VERSION
from .forms import InputsForm
from .models import Simulation
from .compute import Compute, JobFailError
from .displayer import Displayer
from .submit import handle_submission, BadPost
from .tags import TAGS


class InputsMixin:
    """
    Define class attributes and common methods for inputs form views.
    """

    template_name = "comp/inputs_form.html"
    has_errors = False
    webapp_version = WEBAPP_VERSION

    def project_context(self, request, project):
        user = request.user
        can_run = user.is_authenticated and is_profile_active(user)
        provided_free = project.sponsor is not None
        can_run = can_run or provided_free
        rate = round(project.server_cost, 2)
        exp_cost, exp_time = project.exp_job_info(adjust=True)

        context = {
            "rate": f"${rate}/hour",
            "project_name": project.title,
            "owner": project.owner.user.username,
            "app_description": project.safe_description,
            "can_run": can_run,
            "exp_cost": f"${exp_cost}",
            "exp_time": f"{exp_time} seconds",
            "provided_free": provided_free,
            "app_url": project.app_url,
        }
        return context


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
                return InputsView.as_view()(request, *args, **kwargs)
            else:
                return UnrestrictedInputsView.as_view()(request, *args, **kwargs)
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


class UnrestrictedInputsView(InputsMixin, View):
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

        result = handle_submission(request, project, ioclasses, compute)
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


class InputsView(UnrestrictedInputsView):
    """
    This class adds a paywall to the _InputsView class.
    """

    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_profile_active, login_url="/users/login/"))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class GetOutputsObjectMixin:
    def get_object(self, pk, username, title):
        return self.model.objects.get(
            pk=pk, project__title=title, project__owner__user__username=username
        )


class EditInputsView(GetOutputsObjectMixin, InputsMixin, View):
    model = Simulation

    def get(self, request, *args, **kwargs):
        print("edit method=GET", request.GET)
        self.object = self.get_object(kwargs["pk"], kwargs["username"], kwargs["title"])
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


class OutputsView(GetOutputsObjectMixin, ChargeRunMixin, DetailView):
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

    def fail(self):
        return render(
            self.request, "comp/failed.html", {"error_msg": self.object.error_text}
        )

    def dispatch(self, request, *args, **kwargs):
        compute = Compute()
        self.object = self.get_object(kwargs["pk"], kwargs["username"], kwargs["title"])
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
        elif self.object.error_text is not None:
            return self.fail()
        else:
            job_id = str(self.object.job_id)
            try:
                job_ready = compute.results_ready(job_id)
            except JobFailError as jfe:
                self.object.error_text = ""
                self.object.save()
                return self.fail()
            if job_ready == "FAIL":
                error_msg = compute.get_results(job_id, job_failure=True)
                if not error_msg:
                    error_msg = "Error: stack trace for this error is " "unavailable"
                val_err_idx = error_msg.rfind("Error")
                error_contents = error_msg[val_err_idx:].replace(" ", "&nbsp;")
                self.object.error_text = error_contents
                self.object.save()
                return self.fail()
            if job_ready == "YES":
                try:
                    results = compute.get_results(job_id)
                except Exception as e:
                    self.object.error_text = str(e)
                    self.object.save()
                    return self.fail()
                self.charge_run(results["meta"], use_stripe=USE_STRIPE)
                self.object.meta_data = results["meta"]
                self.object.outputs = results["outputs"]
                self.object.aggr_outputs = results["aggr_outputs"]
                self.object.save()
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
                    # if exp_num_minutes > 0:
                    return JsonResponse(
                        {"eta": exp_num_minutes, "origEta": orig_eta}, status=202
                    )
                    # else:
                    # return JsonResponse({"eta": exp_num_minutes, "origEta": orig_eta}, status=200)

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
        self.object = self.get_object(kwargs["pk"], kwargs["username"], kwargs["title"])

        if (
            not (self.object.outputs or self.object.aggr_outputs)
            or self.object.error_text
        ):
            return redirect(self.object)

        # option to download the raw JSON for testing purposes.
        if request.GET.get("raw_json", False):
            raw_json = json.dumps(
                {
                    "meta": self.object.meta_data,
                    "outputs": self.object.outputs,
                    "aggr_outputs": self.object.aggr_outputs,
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
