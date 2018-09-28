import datetime

from django.utils import timezone
from django.shortcuts import render, redirect
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test

from webapp.apps.core.models import Tag, TagOption
from webapp.apps.core.views import CoreRunDetailView, CoreRunDownloadView
from webapp.apps.core.compute import Compute, WorkersUnreachableError

from webapp.apps.users.models import Project, is_profile_active

from .models import FileInput, FileOutput


Compute = Compute


class FileInputView(View):
    model = FileInput
    result_header = 'Describe'
    template_name = 'upload/input.html'
    name = 'Descriptive Statistics'
    app_name = 'upload'

    def get(self, request, *args, **kwargs):
        project = Project.objects.get(name=self.name)
        user = request.user
        can_run = user.is_authenticated and is_profile_active(user)
        rate = round(project.server_cost, 2)
        avg_job_cost = self.avg_job_cost(project)

        return render(request, self.template_name,
                      context={'rate': f'${rate}/hr',
                               'name': self.name,
                               'redirect_back': 'fileinput',
                               'can_run': can_run,
                               'avg_job_cost': f'${avg_job_cost}'})

    @method_decorator(login_required)
    @method_decorator( #TODO: redirect to update pmt info or re-subscribe
        user_passes_test(is_profile_active, login_url='/users/login/'))
    def post(self, request, *args, **kwargs):
        project = Project.objects.get(name=self.name)
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
        fo.project = project
        fo.profile = request.user.profile
        fo.save()
        return redirect(fo)

    def avg_job_cost(self, project, n_tasks=1):
        rate_per_sec = project.server_cost / 3600
        return round(
            rate_per_sec * project.exp_task_time * n_tasks,
            4)


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
