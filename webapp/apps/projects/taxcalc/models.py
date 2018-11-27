from django.db import models
from django.urls import reverse
from django.contrib.postgres.fields import ArrayField
from webapp.apps.core.models import CoreInputs, CoreRun

from webapp.apps.projects.taxcalc.helpers import json_int_key_encode


class TaxcalcInputs(CoreInputs):
    start_year = models.IntegerField()
    data_source = models.CharField(max_length=10)

    # deprecated fields list
    deprecated_fields = ArrayField(
        models.CharField(max_length=100, blank=True),
        blank=True,
        null=True
    )

    NONPARAM_FIELDS = set(["id", "quick_calc", "data_source"])

    @property
    def deserialized_inputs(self):
        """
        Convert integer keys to int type after they were converted to strings
        during serialization
        """
        return json_int_key_encode(self.upstream_parameters)

    @property
    def years(self):
        return list(i + self.start_year for i in range(0, 10))

    class Meta:
        permissions = (
            ("view_inputs", "Allowed to view Taxcalc."),
        )


class TaxcalcRun(CoreRun):
    inputs = models.OneToOneField(TaxcalcInputs, on_delete=models.PROTECT,
                                  related_name='outputs')

    def get_absolute_url(self):
        kwargs = {
            'pk': self.pk
        }
        return reverse('taxcalc_detail', kwargs=kwargs)

    # def get_absolute_edit_url(self):
    #     kwargs = {
    #         'pk': self.pk
    #     }
    #     return reverse('edit_personal_results', kwargs=kwargs)

    def get_absolute_download_url(self):
        kwargs = {
            'pk': self.pk
        }
        return reverse('taxcalc_download', kwargs=kwargs)

    def zip_filename(self):
        return 'taxcalc.zip'
