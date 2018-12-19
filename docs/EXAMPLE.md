# COMP Publishing Information

App Name
-----------------
*What's the name of the app?*

CompBaseball

App Overview
----------------------------------------
*What does this app do? Must be less than 1000 characters.*

[CompBaseball](https://github.com/hdoupe/compbaseball) is an entertaining way to document COMP and demonstrate its abilities. Select a date range using the format YYYY-MM-DD. Keep in mind that CompBaseball only provides data on matchups going back to 2008. Two datasets are offered to run this model: one that only has the most recent season, 2018, and one that contains data on every single pitch going back to 2008. Next, select your favorite pitcher and some batters who he's faced in the past. Click submit to start analyzing the selected matchups!


Python Functions
-------------------------
*Insert code snippets satisfying the requirements detailed in the [functions documentation.](ENDPOINTS.md)*


**Package Defaults:** Get the default Model Parameters and their meta data

```python
# code snippet here
from compbaseball import baseball


def package_defaults(**meta_parameters):
    return baseball.get_inputs(use_2018=meta_parameters["use_2018"])
```


**Parse user adjustments:** Do model-specific formatting and validation on the user adjustments

```python
# code snippet here
from compbaseball import baseball


def parse_user_inputs(params, jsonparams, errors_warnings,
                        **meta_parameters):
    # parse the params, jsonparams, and errors_warnings further
    use_2018 = meta_parameters["use_2018"]
    params, jsonparams, errors_warnings = baseball.parse_inputs(
        params, jsonparams, errors_warnings, use_2018=use_2018)
    return params, jsonparams, errors_warnings
```


**Run simulation:** Submit the user adjustments (or none) to the model to run the simulations

```python
# code snippet here
from compbaseball import baseball


def run_simulation(use_2018, user_mods):
    result = baseball.get_matchup(use_2018, user_mods)
    return result
```

Environment
---------------
*Describe how to install this project and its resource requirements as detailed in [the environment documentation](ENVIRONMENT.md).*


**Installation:** How is this project installed?

```
conda install pandas pyarrow bokeh
pip install pybaseball compbaseball
```

**Memory:** How much memory in GB will this project require to run?

2 GB

**Run time:** About how long will it take to run this project?

20 seconds