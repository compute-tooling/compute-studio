from django.utils.safestring import mark_safe

"""
This file is used to specify constant variables such as meta_parameter
defaults and the project version
"""
APP_NAME = "compbaseball"
COMPBASEBALL_VERSION = "0.1.0"

APP_DESCRIPTION = mark_safe("""
<div>
    <p>
        <a href="https://github.com/hdoupe/compbaseball">CompBaseball</a>
        is an entertaining way to document COMP and demonstrate its abilities. Select a date
        range using the format YYYY-MM-DD. Keep in mind that CompBaseball only provides data
        on matchups going back to 2008. Two datasets are offered to run this model: one that
        only has the most recent season, 2018, and one that contains data on every single
        pitch going back to 2008. Next, select your favorite pitcher and some batters who he's
        faced in the past. Click submit to start analyzing the selected matchups!
    </p>
    <h4> Core Maintainers: </h4>
    <ul>
        <li>Hank Doupe</li>
    </ul>
</div>
""")