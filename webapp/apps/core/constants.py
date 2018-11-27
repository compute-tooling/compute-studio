from django.conf import settings
from django.utils.safestring import mark_safe

OUT_OF_RANGE_ERROR_MSG = mark_safe("""
<div align="left">
    Some fields have warnings or errors. Fields with warnings have message(s)
    below them beginning with \'WARNING\', and fields with errors have
    message(s) below them beginning with \'ERROR\'.
    <br /> <br />
    &emsp;- If the field has a warning message , then review the input to make
    sure it is correct and click \'SUBMIT\' to run the model with these inputs.
    <br />
    &emsp;- If the field has an error message, then the parameter value must be
    changed so that it is in a valid range.
</div>""")


WEBAPP_VERSION = settings.WEBAPP_VERSION
