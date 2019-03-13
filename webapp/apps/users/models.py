from collections import defaultdict

from django.db import models
from django.db.models.functions import TruncMonth
from django.db.models import F, Case, When, Sum
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.urls import reverse
from django.contrib.postgres.fields import ArrayField


def is_profile_active(user):
    if getattr(user, "profile", False):
        return user.profile.is_active
    return False


class User(AbstractUser):
    def __str__(self):
        return self.email


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)

    def costs(self, projects=None):
        if projects is None:
            projects = Project.objects.all()
        agg = defaultdict(float)
        for project in projects:
            relation = f"{project.app_name}_{project.app_name}run_runs"
            if hasattr(self, relation):
                res = (
                    getattr(self, relation)
                    .values(month=TruncMonth("creation_date"))
                    .annotate(
                        effective=Case(
                            When(run_cost=0.0, then=0.01), default=F("run_cost")
                        )
                    )
                    .annotate(Sum("effective"))
                )
                for month in res:
                    agg[month["month"]] += float(month["effective__sum"])
        return {k.strftime("%B %Y"): v for k, v in sorted(agg.items())}

    def runs(self, projects=None):
        if projects is None:
            projects = Project.objects.all()
        runs = {}
        for project in projects:
            relation = f"{project.app_name}_{project.app_name}run_runs"
            queryset = getattr(self, relation, None)
            if queryset is not None:
                runs[project.name] = queryset.all()
            print(f"skipping {relation}")
        return runs

    class Meta:
        # not in use yet...
        permissions = (("access_public", "Has access to public projects"),)


class Project(models.Model):
    SECS_IN_HOUR = 3600.0
    name = models.CharField(max_length=255)
    app_name = models.CharField(max_length=30)
    description = models.CharField(max_length=1000)
    profile = models.ForeignKey(
        Profile, null=True, related_name="projects", on_delete=models.CASCADE
    )
    sponsor = models.ForeignKey(
        Profile, null=True, related_name="sponsored_projects", on_delete=models.SET_NULL
    )
    is_public = models.BooleanField(default=True)
    status = models.CharField(
        choices=(
            ("live", "live"),
            ("pending", "pending"),
            ("requires fixes", "requires fixes"),
        ),
        default="live",
        max_length=32,
    )

    # functions
    package_defaults = models.CharField(max_length=1000)
    parse_user_adjustments = models.CharField(max_length=1000)
    run_simulation = models.CharField(max_length=1000)

    # install
    installation = models.CharField(max_length=1000)

    # server resources
    server_cost = models.DecimalField(max_digits=6, decimal_places=3, null=True)
    # ram, vcpus
    def callabledefault():
        return [4, 2]

    server_size = ArrayField(
        models.CharField(max_length=5), default=callabledefault, size=2
    )
    exp_task_time = models.IntegerField(null=True)
    exp_num_tasks = models.IntegerField(null=True)

    @staticmethod
    def get_or_none(**kwargs):
        try:
            res = Project.objects.get(**kwargs)
        except Project.DoesNotExist:
            res = None
        return res

    def exp_job_info(self, adjust=False):
        rate_per_sec = self.server_cost / 3600
        job_time = self.exp_task_time * self.exp_num_tasks
        cost = round(rate_per_sec * job_time, 4)
        if adjust:
            return max(cost, 0.01), job_time
        else:
            return cost, job_time

    def run_cost(self, run_time, adjust=False):
        """
        Calculate the cost of a project run. The run time is scaled by the time
        required for it to cost one penny. If adjust is true and the cost is
        less than one penny, then it is rounded up to a penny.
        """
        cost = round(run_time / self.n_secs_per_penny) / 100
        if adjust:
            return max(cost, 0.01)
        else:
            return cost

    @property
    def n_secs_per_penny(self):
        """
        Calculate the number of seconds a project sim needs to run such that
        the cost of that run is one penny.
        """
        return 0.01 / self.server_cost_in_secs

    @property
    def server_cost_in_secs(self):
        """
        Convert server cost from $P/hr to $P/sec.
        """
        return float(self.server_cost) / self.SECS_IN_HOUR

    @staticmethod
    def dollar_to_penny(c):
        return int(round(c * 100, 0))

    @property
    def app_url(self):
        return reverse(self.app_name)

    def worker_ext(self, action):
        return f"{self.profile.user.username}/{self.app_name}/{action}"

    @property
    def display_sponsor(self):
        if self.sponsor is not None:
            return self.sponsor.user.username
        else:
            return "Not sponsored"

    @property
    def number_runs(self):
        relation = relation = f"{self.app_name}_{self.app_name}run_runs"
        return getattr(self, relation).count()
