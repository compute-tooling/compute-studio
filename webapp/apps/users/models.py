from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):

    def __str__(self):
        return self.email


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                null=True,
                                on_delete=models.CASCADE)

    public_access = models.BooleanField(default=False)

    @staticmethod
    def create_from_user(user, public_access):
        profile = Profile.objects.create(user=user,
                                         public_access=public_access)

        return profile

    class Meta:
        permissions = (
            ('access_public', 'Has access to public projects'),
        )


class Project(models.Model):
    SECS_IN_HOUR = 3600.0
    name = models.CharField(max_length=255)
    server_cost = models.DecimalField(max_digits=6, decimal_places=3,
                                      null=True)
    exp_task_time = models.IntegerField(null=True)
    is_public = models.BooleanField(default=True)

    @staticmethod
    def get_or_none(**kwargs):
        try:
            res = Project.objects.get(**kwargs)
        except Project.DoesNotExist:
            res = None
        return res

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
