# Python functions

The modeling project must provide a Python function for each of the following tasks:

- **Model Parameters**: Get the default Model Parameters and their meta data.
- **Parse user adjustments**: Do model-specific formatting and validation on user adjustments.
- **Run simulation**: Submit the user adjustments (or none) to the model to run the simulation.

Once you've skimmed the criteria below, you can develop your functions against the [`computestudiokit`](https://github.com/compute-studio/Compute-Studio-Kit/) automated testing suite.

Model Parameters
----------------------

Accepts Meta Parameters, if they are being utilized. Returns data in the form specified in the [inputs page](/publish/inputs/).

- **Python Example**:

```python
import matchups


def get_inputs(meta_params_dict):
    meta_params = MetaParams()
    meta_params.adjust(meta_params_dict)
    params = MatchupsParams()
    spec = params.specification(
        meta_data=True,
        use_full_data=meta_params.use_full_data.tolist()
    )
    return meta_params.specification(meta_data=True), {"matchup": spec}

```

Here's what you get after filling in this function:
[![alt text](https://user-images.githubusercontent.com/9206065/56739963-eee28780-673d-11e9-8692-59f58af2b5ff.png)](https://compute.studio/hdoupe/Matchups/)

Validate user adjustments
--------------------------
Accepts parsed user adjustments, separated by each major section. Returns warnings/errors (if any).

Compute Studio will provide parsed user adjustments of the form:

```json
{
    "matchup": {
        "start_date": [{"value": "2012-08-01"}],
        "end_date": [{"value": "2012-09-01"}],
        "pitcher": [{"value": "Not a Real Pitcher"}],
    }
}
```

The function should return:

Warnings/Errors:

```python
    {
        "matchup": {
            "errors": {
                "pitcher": ['Pitcher "Not a Real Pitcher" not allowed']
            },
            "warnings": {}
        }
    }
```

- **Python**:

```python
import matchups

def validate_inputs(meta_param_dict, adjustment, errors_warnings):
    # matchups doesn't look at meta_param_dict for validating inputs.
    params = MatchupsParams()
    params.adjust(adjustment["matchup"], raise_errors=False)
    errors_warnings["matchup"]["errors"].update(params.errors)
    return errors_warnings
```

Here's what you get after filling in this function:
![alt text](https://user-images.githubusercontent.com/9206065/56741151-48e44c80-6740-11e9-88a8-dcc5887a3187.png)


Run simulation
----------------

Accepts Meta Parameters values and model parameters. Returns outputs as specified in the [outputs page](/publish/outputs/)

Compute Studio submits the model's meta parameters and the parsed and formatted user adjustments:

```
{
    "meta_params": {},
    "model_params": {
        "some_major_section": {},
        "another_major_section": {}
    }
}
```

- **Python Example**:

```python
import matchups

def get_matchup(meta_param_dict, adjustment):
    result = matchups.get_matchup(meta_param_dict, adjustment)
    return result
```

Here's what you get after filling in this function:

[![alt text](https://user-images.githubusercontent.com/9206065/56739964-ef7b1e00-673d-11e9-9d91-2f7227d09897.png)](https://compute.studio/hdoupe/Matchups/16/)