import itertools
from io import BytesIO
from zipfile import ZipFile
import json

from django.utils import timezone
from django.db import models
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin, DetailView
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404, JsonResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test

from webapp.apps.billing.models import SubscriptionItem, UsageRecord
from webapp.apps.billing.utils import USE_STRIPE
from webapp.apps.users.models import Project, is_profile_active
from .constants import WEBAPP_VERSION

from .models import CoreRun
from .compute import Compute, JobFailError
from .displayer import Displayer
from .meta_parameters import meta_parameters
from .submit import handle_submission, BadPost


class InputsMixin:
    """
    Define class attributes and common methods for inputs form views.
    """
    form_class = None
    displayer_class = Displayer
    submit_class = None
    save_class = None
    template_name = "core/inputs_form.html"
    project_name = "Inputs"
    app_name = "core"
    app_description = "Placeholder description"
    meta_parameters = meta_parameters
    meta_options = {}
    has_errors = False
    upstream_version = None
    webapp_version = WEBAPP_VERSION

    def project_context(self, request):
        project = Project.objects.get(name=self.project_name)
        user = request.user
        can_run = user.is_authenticated and is_profile_active(user)
        rate = round(project.server_cost, 2)
        exp_cost, exp_time = project.exp_job_info(adjust=True)

        context = {
            'rate': f'${rate}/hour',
            'project_name': self.project_name,
            'app_name': self.app_name,
            'app_description': self.app_description,
            'redirect_back': self.app_name,
            'can_run': can_run,
            'exp_cost': f'${exp_cost}',
            'exp_time': f'{exp_time} seconds'}
        return context


class InputsView(InputsMixin, View):

    def get(self, request, *args, **kwargs):
        print("method=GET", request.GET)
        inputs_form = self.form_class()
        # set cleaned_data with is_valid call
        inputs_form.is_valid()
        inputs_form.clean()
        context = self.project_context(request)
        return self._render_inputs_form(request, inputs_form, context)

    @method_decorator(login_required)
    @method_decorator(
        user_passes_test(is_profile_active, login_url='/users/login/'))
    def post(self, request, *args, **kwargs):
        print("method=POST", request.POST)
        compute = Compute()
        if request.POST.get("reset", ''):
            inputs_form = self.form_class(request.POST.dict())
            if inputs_form.is_valid():
                inputs_form.clean()
            else:
                inputs_form = self.form_class()
                inputs_form.is_valid()
                inputs_form.clean()
            context = self.project_context(request)
            return self._render_inputs_form(request, inputs_form, context)

        result = handle_submission(
            request, compute, self.submit_class, self.save_class
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

        displayer = self.displayer_class(**valid_meta_params)
        context = dict(
            form=inputs_form,
            default_form=displayer.defaults(flat=False),
            upstream_version=self.upstream_version,
            webapp_version=self.webapp_version,
            has_errors=self.has_errors,
            **self.project_context(request)
        )
        return render(request, self.template_name, context)

    def _render_inputs_form(self, request, inputs_form, context):
        valid_meta_params = {}
        for mp in self.meta_parameters.parameters:
            valid_meta_params[mp.name] = inputs_form.cleaned_data[mp.name]
        displayer = self.displayer_class(**valid_meta_params)
        context = dict(
            form=inputs_form,
            default_form=displayer.defaults(flat=False),
            upstream_version=self.upstream_version,
            webapp_version=self.webapp_version,
            has_errors=self.has_errors,
            **context
        )
        return render(request, self.template_name, context)


class EditInputsView(InputsMixin, DetailView):
    model = CoreRun

    def get(self, request, *args, **kwargs):
        print("edit method=GET", request.GET)
        model = self.get_object()
        initial = {}
        for k, v in model.inputs.raw_gui_inputs.items():
            if v not in ("", None):
                initial[k] = v
        for mp in self.meta_parameters.parameters:
            mp_val = getattr(model.inputs, mp.name, None)
            if mp_val is not None:
                initial[mp.name] = mp_val
        inputs_form = self.form_class(initial=initial)
        # clean data with is_valid call.
        inputs_form.is_valid()
        # is_bound is turned off so that the `initial` data is displayed.
        # Note that form is validated and cleaned with is_bound call.
        inputs_form.is_bound = False
        context = self.project_context(request)
        return self._render_inputs_form(request, inputs_form, context)

    def post(self, request, *args, **kwargs):
        return HttpResponseNotFound('<h1>Post not allowed to edit page</h1>')

    def _render_inputs_form(self, request, inputs_form, context):
        valid_meta_params = {}
        for mp in self.meta_parameters.parameters:
            valid_meta_params[mp.name] = (
                inputs_form.initial.get(mp.name, None) or inputs_form[mp.name]
            )
        displayer = self.displayer_class(**valid_meta_params)
        context = dict(
            form=inputs_form,
            default_form=displayer.defaults(flat=False),
            upstream_version=self.upstream_version,
            webapp_version=self.webapp_version,
            has_errors=self.has_errors,
            **context
        )
        return render(request, self.template_name, context)


class SuperclassTemplateNameMixin(object):
    """A mixin that adds the templates corresponding to the core as candidates
    if customized ones aren't found in subclasses."""

    def get_template_names(self):
        names = super().get_template_names()

        # Look for classes that the view inherits from, and that are directly
        # inheriting this mixin
        subclasses = SuperclassTemplateNameMixin.__subclasses__()
        superclasses = self.__class__.__bases__
        classes_to_check = set(subclasses).intersection(set(superclasses))

        for c in classes_to_check:
            # Adapted from
            # https://github.com/django/django/blob/2e06ff8/django/views/generic/detail.py#L142
            if (getattr(c, 'model', None) is not None and
                    issubclass(c.model, models.Model)):
                names.append("%s/%s%s.html" % (
                    c.model._meta.app_label,
                    c.model._meta.model_name,
                    self.template_name_suffix))
        return names


class OutputsView(SuperclassTemplateNameMixin, DetailView):
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

    model = CoreRun
    is_editable = True
    result_header = "Results"

    def fail(self):
        return render(self.request, 'core/failed.html',
                      {"error_msg": self.object.error_text})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["result_header"] = self.result_header
        return context

    def dispatch(self, request, *args, **kwargs):
        compute = Compute()
        self.object = self.get_object()
        if self.object.outputs or self.object.aggr_outputs:
            return super().get(self, request, *args, **kwargs)
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
            if job_ready == 'FAIL':
                error_msg = compute.get_results(job_id, job_failure=True)
                if not error_msg:
                    error_msg = ("Error: stack trace for this error is "
                                 "unavailable")
                val_err_idx = error_msg.rfind("Error")
                error_contents = error_msg[val_err_idx:].replace(" ", "&nbsp;")
                self.object.error_text = error_contents
                self.object.save()
                return self.fail()

            if job_ready == 'YES':
                try:
                    results = compute.get_results(job_id)
                except Exception as e:
                    self.object.error_text = str(e)
                    self.object.save()
                    return self.fail()
                self.object.run_time = sum(results['meta']['task_times'])
                self.object.run_cost = self.object.project.run_cost(
                    self.object.run_time)
                quantity = self.object.project.run_cost(
                    self.object.run_time, adjust=True)
                if USE_STRIPE:
                    plan = self.object.project.product.plans.get(
                        usage_type='metered')
                    si = SubscriptionItem.objects.get(
                        subscription__customer=self.object.profile.user.customer,
                        plan=plan)
                    stripe_ur = UsageRecord.create_stripe_object(
                        quantity=Project.dollar_to_penny(quantity),
                        timestamp=None,
                        subscription_item=si,
                    )
                    UsageRecord.construct(stripe_ur, si)
                self.object.meta_data = results["meta"]
                self.object.outputs = results['outputs']
                self.object.aggr_outputs = results['aggr_outputs']
                self.object.creation_date = timezone.now()
                self.object.save()
                return super().get(self, request, *args, **kwargs)
            else:
                if request.method == 'POST':
                    # if not ready yet, insert number of minutes remaining
                    exp_comp_dt = self.object.exp_comp_datetime
                    utc_now = timezone.now()
                    dt = exp_comp_dt - utc_now
                    exp_num_minutes = dt.total_seconds() / 60.
                    exp_num_minutes = round(exp_num_minutes, 2)
                    exp_num_minutes = (exp_num_minutes if exp_num_minutes > 0
                                       else 0)
                    if exp_num_minutes > 0:
                        return JsonResponse({'eta': exp_num_minutes},
                                            status=202)
                    else:
                        return JsonResponse({'eta': exp_num_minutes},
                                            status=200)

                else:
                    context = {'eta': '100'}
                    return render(
                        request,
                        'core/not_ready.html',
                        context
                    )

    def is_from_file(self):
        if hasattr(self.object.inputs, 'raw_gui_field_inputs'):
            return not self.object.inputs.raw_gui_field_inputs
        else:
            return False

    def inputs_to_display(self):
        if hasattr(self.object.inputs, 'inputs_file'):
            return json.dumps(self.object.inputs.inputs_file, indent=2)
        else:
            return ''


class OutputsDownloadView(SingleObjectMixin, View):
    model = CoreRun

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if (not (self.object.outputs or self.object.aggr_outputs) or
           self.object.error_text):
            return redirect(self.object)

        # option to download the raw JSON for testing purposes.
        if request.GET.get("raw_json", False):
            raw_json = json.dumps({
                "meta": self.object.meta_data,
                "outputs": self.object.outputs,
                "aggr_outputs": self.object.aggr_outputs},
                indent=4)
            resp = HttpResponse(raw_json, content_type="text/plain")
            resp['Content-Disposition'] = "attachment; filename=outputs.json"
            return resp

        try:
            downloadables = list(itertools.chain.from_iterable(
                output['downloadable'] for output in self.object.outputs))
            downloadables += list(itertools.chain.from_iterable(
                output['downloadable'] for output in self.object.aggr_outputs))
        except KeyError:
            raise Http404
        if not downloadables:
            raise Http404

        s = BytesIO()
        z = ZipFile(s, mode='w')
        for i in downloadables:
            z.writestr(i['filename'], i['text'])
        z.close()
        resp = HttpResponse(s.getvalue(), content_type="application/zip")
        resp['Content-Disposition'] = 'attachment; filename={}'.format(
            self.object.zip_filename())
        s.close()
        return resp