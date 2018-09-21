from django.db import models
from django.urls import reverse
from ..core.models import CoreInputs, CoreRun


class FileInput(CoreInputs):
    pass


class FileOutput(CoreRun):
    inputs = models.OneToOneField(FileInput, on_delete=models.PROTECT,
                                  related_name='outputs')

    def get_absolute_url(self):
        kwargs = {
            'pk': self.pk
        }
        return reverse('file_results', kwargs=kwargs)

    def get_absolute_download_url(self):
        kwargs = {
            'pk': self.pk
        }
        return reverse('fileinput_download', kwargs=kwargs)

    def zip_filename(self):
        return 'upload.zip'
