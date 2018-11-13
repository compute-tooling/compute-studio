import os

import sys

from urllib.parse import urlparse, parse_qs

from django.shortcuts import render, redirect, get_object_or_404

from .forms import TaxcalcForm
from .helpers import json_int_key_encode
from .param_displayers import nested_form_parameters
from ..core.compute import Compute
from .models import TaxcalcRun
from ..core.views import CoreRunDetailView, CoreRunDownloadView
from ..core.models import Tag, TagOption

from .constants import (DISTRIBUTION_TOOLTIP, DIFFERENCE_TOOLTIP,
                         PAYROLL_TOOLTIP, INCOME_TOOLTIP, BASE_TOOLTIP,
                         REFORM_TOOLTIP, INCOME_BINS_TOOLTIP,
                         INCOME_DECILES_TOOLTIP, START_YEAR, START_YEARS,
                         DATA_SOURCES, DEFAULT_SOURCE, OUT_OF_RANGE_ERROR_MSG,
                         WEBAPP_VERSION, TAXCALC_VERSION, NUM_BUDGET_YEARS)

from .param_formatters import append_errors_warnings
from .submit_data import PostMeta, BadPost, process_reform, save_model

ENABLE_QUICK_CALC = bool(os.environ.get('ENABLE_QUICK_CALC', ''))

compute = Compute()


def get_version(url_obj, attr_name, current_version):
    """
    get formatted python version of library for diplay on web page
    """
    # need to chop off the commit reference on older runs
    vers_disp = (getattr(url_obj, attr_name)
                 if getattr(url_obj, attr_name) is not None
                 else current_version)
    # only recently start storing webapp version. for older runs display
    # the current version. an alternative is to display the first stable
    # version if url.webapp_version is None
    if len(vers_disp.split('.')) > 3:
        vers_disp = '.'.join(vers_disp.split('.')[:-1])

    return vers_disp


class TaxcalcRunDetailView(CoreRunDetailView):
    model = TaxcalcRun

    result_header = "Static Results"

    tags = [
        Tag(key="table_type",
            values=[
                TagOption(
                    value="dist",
                    title="Distribution Table",
                    tooltip=DISTRIBUTION_TOOLTIP,
                    children=[
                        Tag(key="law",
                            values=[
                                TagOption(
                                    value="current",
                                    title="Current Law",
                                    active=True,
                                    tooltip=BASE_TOOLTIP),
                                TagOption(
                                    value="reform",
                                    title="Reform",
                                    tooltip=REFORM_TOOLTIP)])]),
                TagOption(
                    value="diff",
                    title="Difference Table",
                    tooltip=DIFFERENCE_TOOLTIP,
                    active=True,
                    children=[
                        Tag(key="tax_type",
                            values=[
                                TagOption(
                                    value="payroll",
                                    title="Payroll Tax",
                                    tooltip=PAYROLL_TOOLTIP),
                                TagOption(
                                    value="ind_income",
                                    title="Income Tax",
                                    tooltip=INCOME_TOOLTIP),
                                TagOption(
                                    value="combined",
                                    title="Combined",
                                    active=True,
                                    tooltip="")  # TODO
                            ])])]),
        Tag(key="grouping",
            values=[
                TagOption(
                    value="bins",
                    title="Income Bins",
                    active=True,
                    tooltip=INCOME_BINS_TOOLTIP),
                TagOption(
                    value="deciles",
                    title="Income Deciles",
                    tooltip=INCOME_DECILES_TOOLTIP)
            ])]
    aggr_tags = [
        Tag(key="law",
            values=[
                TagOption(
                    value="current",
                    title="Current Law"),
                TagOption(
                    value="reform",
                    title="Reform"),
                TagOption(
                    value="change",
                    title="Change",
                    active=True)
            ])]

    def has_link_to_dyn(self):
        assumptions = self.object.inputs.upstream_parameters.get('assumption', None)
        if assumptions is None:
            return True
        else:
            return all(len(assumptions[d]) == 0 for d in assumptions)


class TaxcalcRunDownloadView(CoreRunDownloadView):
    model = TaxcalcRun


def taxcalc_inputs(request):
    """
    Receive data from GUI interface and returns parsed data or default data if
    get request
    """
    start_year = START_YEAR
    has_errors = False
    data_source = DEFAULT_SOURCE
    if request.method == 'POST':
        print('method=POST get', request.GET)
        print('method=POST post', request.POST)
        obj, post_meta = process_reform(request, compute)
        # case where validation failed in forms.TaxcalcForm
        # TODO: assert HttpResponse status is 404
        if isinstance(post_meta, BadPost):
            return post_meta.http_response_404

        # No errors--submit to model
        if not post_meta.stop_submission:
            print('redirecting...', obj, obj.get_absolute_url())
            return redirect(obj)
        # Errors from taxcalc.tbi.reform_warnings_errors
        else:
            personal_inputs = post_meta.personal_inputs
            start_year = post_meta.start_year
            data_source = post_meta.data_source
            use_puf_not_cps = (data_source == 'PUF')
            has_errors = post_meta.has_errors

    else:
        # Probably a GET request, load a default form
        print('method=GET get', request.GET)
        print('method=GET post', request.POST)
        params = parse_qs(urlparse(request.build_absolute_uri()).query)
        if 'start_year' in params and params['start_year'][0] in START_YEARS:
            start_year = params['start_year'][0]

        # use puf by default
        use_puf_not_cps = True
        if ('data_source' in params and
                params['data_source'][0] in DATA_SOURCES):
            data_source = params['data_source'][0]
            if data_source != 'PUF':
                use_puf_not_cps = False

        personal_inputs = TaxcalcForm(first_year=start_year,
                                       use_puf_not_cps=use_puf_not_cps)

    init_context = {
        'form': personal_inputs,
        'params': nested_form_parameters(int(start_year), use_puf_not_cps),
        'upstream_version': TAXCALC_VERSION,
        'webapp_version': WEBAPP_VERSION,
        'start_years': START_YEARS,
        'start_year': start_year,
        'has_errors': has_errors,
        'data_sources': DATA_SOURCES,
        'data_source': data_source,
        'enable_quick_calc': ENABLE_QUICK_CALC
    }

    return render(request, 'taxcalc/input_form.html', init_context)
