from webapp.apps.core.compute import Compute
from webapp.apps.core.views import (
    UnrestrictedInputsView,
    EditInputsView,
    OutputsView,
    OutputsDownloadView,
)
from webapp.apps.core.abstract_models import Tag, TagOption

from .models import MatchupsRun
from .displayer import MatchupsDisplayer
from .submit import MatchupsSubmit, MatchupsSave
from .forms import MatchupsInputsForm
from .meta_parameters import matchups_meta_parameters
from .constants import MATCHUPS_VERSION, APP_NAME, APP_DESCRIPTION, PROVIDED_FREE


compute = Compute()


class MatchupsInputsMixin:
    form_class = MatchupsInputsForm
    displayer_class = MatchupsDisplayer
    submit_class = MatchupsSubmit
    save_class = MatchupsSave
    project_name = "Matchups"
    app_name = APP_NAME
    app_description = APP_DESCRIPTION
    meta_parameters = matchups_meta_parameters
    meta_options = []
    has_errors = False
    upstream_version = MATCHUPS_VERSION
    provided_free = PROVIDED_FREE


class MatchupsInputsView(MatchupsInputsMixin, UnrestrictedInputsView):
    """
    A Django view for serving the default input page, validating the inputs,
    and submitting them to the backend worker nodes.
    """


class MatchupsEditInputsView(MatchupsInputsMixin, EditInputsView):
    """
    A Django view for serving serving edited parameters.
    """

    model = MatchupsRun


class MatchupsOutputsView(OutputsView):
    """
    A Django view that polls the backend workers to check whether the result
    is ready yet. Once the result is ready, it is stored in the database and
    served from this view.
    """

    model = MatchupsRun
    result_header = "Matchups Results"
    tags = [
        Tag(
            key="attribute",
            hidden=False,
            values=[
                TagOption(
                    value="pitch-outcome",
                    title="Pitch Outcome Table",
                    tooltip="Pitch outcome tooltip",
                    active=True,
                ),
                TagOption(
                    value="pitch-type",
                    title="Pitch Type Table",
                    tooltip="Pitch type tooltip",
                ),
            ],
        ),
        Tag(
            key="count",
            hidden=False,
            values=[
                TagOption(title="Normalized", value="normalized", tooltip="Normalized"),
                TagOption(
                    title="Count", value="raw-count", active=True, tooltip="Count"
                ),
            ],
        ),
    ]
    aggr_tags = [
        Tag(
            key="attribute",
            hidden=False,
            values=[
                TagOption(title="Pitch Outcome", value="pitch-outcome"),
                TagOption(title="Pitch Type", value="pitch-type", active=True),
            ],
        )
    ]


class MatchupsOutputsDownloadView(OutputsDownloadView):
    """
    A Django view for downloading the result of the project run.
    """

    model = MatchupsRun
