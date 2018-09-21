import datetime

from django.utils import timezone
from django.shortcuts import render, redirect
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test

from webapp.apps.core.models import Tag, TagOption
from webapp.apps.core.views import CoreRunDetailView, CoreRunDownloadView
from webapp.apps.core.compute import Compute, WorkersUnreachableError

from webapp.apps.users.models import Plan

from .models import FileInput, FileOutput

Compute = Compute

def has_public_access(user):
    if hasattr(user, 'profile') and user.profile is not None:
        return user.profile.public_access
    else:
        return False


class FileInputView(View):
    model = FileInput
    result_header = 'Describe'
    template_name = 'upload/input.html'
    name = 'Descriptive Statistics'
    app_name = 'upload'

    def get(self, request, *args, **kwargs):
        user = request.user
        can_run = user.is_authenticated and has_public_access(user)
        if not can_run:
            # plan = Plan.objects.filter(product__name=self.name)
            # met = plan.get(usage_type='metered')
            meter_price = 9/100
        else:
            meter_price = None

        return render(request, self.template_name,
                      context={'metered_price': f'${meter_price}/hr',
                               'name': self.name,
                               'redirect_back': 'fileinput',
                               'can_run': can_run})

    @method_decorator(login_required(login_url='/users/login/'))
    @method_decorator( #TODO: redirect to update pmt info or re-subscribe
        user_passes_test(has_public_access, login_url='/users/login/'))
    def post(self, request, *args, **kwargs):
        compute = Compute()
        tmpfile = request.FILES['datafile']
        tasks = [{'data': tmpfile.read(), 'compression': 'gzip'}]
        try:
            submitted_id, _ = compute.submit_job(tasks, endpoint=self.app_name)
        except WorkersUnreachableError as e:
            print(e)
            return render(request, 'core/failed.html')

        fi = FileInput()
        fi.save()
        fo = FileOutput()
        fo.inputs = fi
        fo.job_id = submitted_id
        delta = datetime.timedelta(seconds=20)
        fo.exp_comp_datetime = timezone.now() + delta
        fo.save()
        return redirect(fo)


class FileRunDetailView(CoreRunDetailView):
    model = FileOutput

    result_header = "Static Results"

    tags = []
    aggr_tags = [
        Tag(key="default",
            values=[
                TagOption(
                    value="default",
                    title="Descriptive"),
            ])]

    def has_link_to_dyn(self):
        return False


class FileRunDownloadView(CoreRunDownloadView):
    model = FileOutput
