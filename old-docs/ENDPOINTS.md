# Python functions

The modeling project must provide a Python function for each of the following tasks:
- **Package Defaults**: Get the default Model Parameters and their meta data.
- **Parse user adjustments**: Do model-specific formatting and validation on user adjustments.
- **Run simulation**: Submit the user adjustments (or none) to the model to run the simulation.

Package defaults
----------------------

Accepts Meta Parameters, if they are being utilized. Returns data in the form specified in the "Model Parameters" section of [`IOSCHEMA.md`](IOSCHEMA.md).

- **Python**:
    ```python
    import matchups

    def package_defaults(**meta_parameters):
        return matchups.get_inputs(use_full_data=meta_parameters["use_full_data"])
    ```

    Here's what you get after filling in this function:
    ![alt text](https://user-images.githubusercontent.com/9206065/51710288-a3152a80-1ff6-11e9-8dcb-16f39f7e9e66.png)

Parse user adjustemnts
----------------------
Accepts parsed user adjustments, separated by each major section. Returns parsed user adjustments, JSON representation of the user adjustments, and warnings/errors (if any).

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

Potentially, reformatted data (no reformatting necessary for this project):

```json
{
    "matchup": {
        "start_date": [{"value": "2012-08-01"}],
        "end_date": [{"value": "2012-09-01"}],
        "pitcher": [{"value": "Not a Real Pitcher"}],
    }
}
```

JSON representation of each major section of parameters:

```python
    {
        "matchup": '{"start_date": [{"value": "2012-08-01"}], "end_date": [{"value": "2012-09-01"}], "pitcher": [{"value": "Not a Real Pitcher"}]}'
    }
```

Warnings/Errors:

```json
    {
        "matchup": {
            "errors": {
                "pitcher": ["Pitcher \"Not a Real Pitcher\" not allowed"]
            },
            "warnings": {}
        }
    }
```

- **Python**:
    ```python
    import matchups

    def parse_user_inputs(params, jsonparams, errors_warnings,
                            **meta_parameters):
        # parse the params, jsonparams, and errors_warnings further
        use_full_data = meta_parameters["use_full_data"]
        params, jsonparams, errors_warnings = matchups.parse_inputs(
            params, jsonparams, errors_warnings, use_full_data==use_full_data)
        return params, jsonparams, errors_warnings
    ```

    Here's what you get after filling in this function:
    ![alt text](https://user-images.githubusercontent.com/9206065/51710289-a3152a80-1ff6-11e9-975d-ba3dfc2b35e9.png)

    The `jsonparams` data is displayed on the outputs page:

    ![alt text](https://user-images.githubusercontent.com/9206065/51710291-a3152a80-1ff6-11e9-8c0d-7a41f8966350.png)

Run simulation
----------------

Accepts Meta Parameters values and parsed and formatted user adjustments. Returns outputs as specified by the [Outputs schema](IOSCHEMA.md)

Compute Studio submits the model's meta parameters and the parsed and formatted user adjustments:
```
    {
        "meta_parameter1": value,
        "meta_parameter2": value,
        ...
        "user_mods": {
            "major_section1": {
            ...
            },
            "major_section2": {
            ...
            },
            ...
        }
    }
```

The function returns the results of the simulation:

[Outputs schema](IOSCHEMA.md)

- **Python**:
    ```python
    import matchups

    def run(**kwargs):
        result = matchups.get_matchup(kwargs["use_full_data"], kwargs["user_mods"])
        return result
    ```

    Here's what you get after filling in this function:

    Aggregate outputs:
    ![alt text](https://user-images.githubusercontent.com/9206065/51710292-a3152a80-1ff6-11e9-9640-661aabd5d76f.png)

    Outputs:
    ![alt text](https://user-images.githubusercontent.com/9206065/51710347-dbb50400-1ff6-11e9-8f28-1c4e5b802fbf.png)

    Toggle along dimension:
    ![alt text](https://user-images.githubusercontent.com/9206065/51710310-baecae80-1ff6-11e9-933a-6308a8baf293.png)