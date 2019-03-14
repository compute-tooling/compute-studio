from django.db import models
from django.urls import reverse
from webapp.apps.core.abstract_models import CoreInputs, CoreRun


class TestappInputs(CoreInputs):
    """
    Set inputs fields that are specific to this project's application. Most other
    parameters will be covered in the abstract model class, CoreInputs, but
    some parameters may be specific to this project, such as the
    meta_parameters defined in this project's meta_parameters module.
    """


class TestappRun(CoreRun):
    """
    Set run or outputs fields that are specific to this project's application.
    Additionally, set the name of the table "dimension." This will be used
    for organizing the outputs. For example, if your project displays data
    on baseball pitchers, this would allow you to toggle a set of tables by
    the pitcher who is being analyzed.
    """

    dimension_name = "testing"

    inputs = models.OneToOneField(
        TestappInputs, on_delete=models.CASCADE, related_name="outputs"
    )

    def get_absolute_url(self):
        return "/url/"

    def get_absolute_edit_url(self):
        return "/url/"

    def get_absolute_download_url(self):
        return "/url/"

    def zip_filename(self):
        return "testing.zip"
