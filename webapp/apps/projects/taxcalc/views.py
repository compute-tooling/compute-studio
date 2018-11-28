import os

import sys

from urllib.parse import urlparse, parse_qs

from django.shortcuts import render, redirect
from webapp.apps.core.compute import Compute
from webapp.apps.core.views import CoreRunDetailView, CoreRunDownloadView
from webapp.apps.core.models import Tag, TagOption
from webapp.apps.core.constants import WEBAPP_VERSION
from webapp.apps.core.submit import BadPost, handle_submission

from .constants import (DISTRIBUTION_TOOLTIP, DIFFERENCE_TOOLTIP,
                         PAYROLL_TOOLTIP, INCOME_TOOLTIP, BASE_TOOLTIP,
                         REFORM_TOOLTIP, INCOME_BINS_TOOLTIP,
                         INCOME_DECILES_TOOLTIP, START_YEAR, START_YEARS,
                         DATA_SOURCES, DEFAULT_SOURCE,
                         TAXCALC_VERSION)
from .models import TaxcalcRun
from .submit import Submit, Save
from .forms import TaxcalcInputsForm
from .param_displayer import ParamDisplayer


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
    meta_parameters = {
        "start_year": int(START_YEAR),
        "data_source": DEFAULT_SOURCE,
        "use_puf_not_cps": DEFAULT_SOURCE == "PUF",
    }
    meta_options = {
        "start_years": START_YEARS,
        "data_sources": DATA_SOURCES,
    }
    has_errors = False
    if request.method == 'POST':
        print('method=POST get', request.GET)
        print('method=POST post', request.POST)
        result = handle_submission(request, compute, Submit, Save)
        # case where validation failed
        # TODO: assert HttpResponse status is 404
        if isinstance(result, BadPost):
            return submission.http_response_404

        # No errors--submit to model
        if result.save is not None:
            print('redirecting...', result.save, result.save.runmodel.get_absolute_url())
            return redirect(result.save.runmodel)
        # Errors from taxcalc.tbi.reform_warnings_errors
        else:
            personal_inputs = result.submit.form
            print(personal_inputs.errors)
            meta_parameters = result.submit.meta_parameters
            has_errors = result.submit.has_errors

    else:
        # Probably a GET request, load a default form
        print('method=GET get', request.GET)
        print('method=GET post', request.POST)
        params = parse_qs(urlparse(request.build_absolute_uri()).query)
        if 'start_year' in params and params['start_year'][0] in START_YEARS:
            start_year = params['start_year'][0]
            meta_parameters.update({
                "start_year": int(start_year)
            })

        # use puf by default
        use_puf_not_cps = True
        if ('data_source' in params and
                params['data_source'][0] in DATA_SOURCES):
            data_source = params['data_source'][0]
            if data_source != 'PUF':
                use_puf_not_cps = False
            meta_parameters.update({
                "data_source": data_source,
                "use_puf_not_cps": use_puf_not_cps,
            })

        personal_inputs = TaxcalcInputsForm()#**meta_parameters)

    pd = ParamDisplayer(**meta_parameters)
    metadict = dict(meta_parameters, **meta_options)
    context = dict(
        form=personal_inputs,
        default_form=pd.default_form(),
        upstream_version=TAXCALC_VERSION,
        webapp_version=WEBAPP_VERSION,
        has_errors=has_errors,
        enable_quick_calc=ENABLE_QUICK_CALC,
        **metadict
    )
    return render(request, 'taxcalc/input_form.html', context)
