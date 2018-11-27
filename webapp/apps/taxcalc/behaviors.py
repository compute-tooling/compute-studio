"""
This module provides a set of mix-ins to be used throughout webapp models.
To read more about Django model mix-ins, check out the following links:
https://docs.djangoproject.com/en/2.0/topics/db/models/#abstract-base-classes
http://blog.kevinastone.com/django-model-behaviors.html
"""

from django.db import models
from . import param_parser


class Fieldable(models.Model):
    """
    Mix-in for providing logic around formatting raw GUI input fields
    """

    class Meta:
        abstract = True

    def set_fields(self, default_data, nonparam_fields=None):
        """
        Parse raw fields
            1. Only keep fields that user specifies
            2. Map TB names to TC names
            3. Do more specific type checking--in particular, check if
               field is the type that Tax-Calculator expects from this param
        """

        gui_field_inputs, failed_lookups = param_parser.parse_fields(
            self.raw_gui_field_inputs,
            default_data
        )

        if failed_lookups:
            # distinct elements
            potential_failed_lookups = set(failed_lookups)
            # only keep parameters that used to be in the upstream package
            set_failed_lookups = potential_failed_lookups - nonparam_fields
            if self.deprecated_fields is None:
                self.deprecated_fields = []
            # drop parameters that we already know are deprecated
            set_failed_lookups.difference_update(self.deprecated_fields)
            self.deprecated_fields += list(set_failed_lookups)

        self.gui_field_inputs = gui_field_inputs

    def pop_extra_errors(self, errors_warnings):
        """
        Removes errors on extra parameters
        """
        for project in errors_warnings:
            for action in ['warnings', 'errors']:
                params = list(errors_warnings[project][action].keys())
                for param in params:
                    if param not in self.raw_gui_field_inputs:
                        errors_warnings[project][action].pop(param)

    def get_model_specs(self):
        """
        Stub to remind that this part of the API is needed
        """
        raise NotImplementedError()


class DataSourceable(models.Model):
    """
    Mix-in for providing data_source field and methods that access it
    """

    class Meta:
        abstract = True

    @property
    def use_puf_not_cps(self):
        # which file to use, front-end not yet implemented
        if self.meta_parameters["data_source"] == 'PUF':
            return True
        else:
            return False
