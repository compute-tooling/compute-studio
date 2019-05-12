from django.conf import settings
from django.utils.safestring import mark_safe

OUT_OF_RANGE_ERROR_MSG = mark_safe(
    """
<div align="left">
    Some fields have errors. These must be fixed before the
    simulation can be submitted.
</div>"""
)


WEBAPP_VERSION = settings.WEBAPP_VERSION
