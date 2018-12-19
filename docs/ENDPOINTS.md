# Python functions

The modeling project must provide a Python function for each of the following tasks:
- **Package Defaults**: Get the baseline inputs and their meta data
- **Parse user inputs**: Do model-specific formatting and validation on the user inputs
- **Run simulation**: Submit the user inputs to the model to run the simulations

Package defaults
----------------------

Accepts meta-parameters, if they are being utilized. Returns data in the form specified in the "Inputs Schema" section of [`IOSCHEMA.md`](IOSCHEMA.md).

- **Python**:
    ```python
    from compbaseball import baseball

    def package_defaults(**meta_parameters):
        return baseball.get_inputs(use_2018=meta_parameters["use_2018"])
    ```

Parse user inputs
----------------------
Accepts parsed data, separated by each major section. Returns parsed inputs, JSON representation of the inputs, and warnings/errors (if any).

COMP will submit parsed data of the form:

```json
{
    "matchup": {
        "start_date": "2012-08-01",
        "end_date": "2012-09-01",
        "pitcher": "Not a Real Pitcher",
    }
}
```

The function should return:

Reformatted data (no reformatting necessary for this project):

```json
{
    "matchup": {
        "start_date": "2012-08-01",
        "end_date": "2012-09-01",
        "pitcher": "Not a Real Pitcher",
    }
}
```

JSON representation of each major section of parameters:

```python
    {
        "matchup":  '{"start_date": "2012-08-01", "end_date": "2012-09-01", "pitcher": "Not a Real Pitcher"}'
    }
```

Warnings/Errors:

```json
    {
        "matchup": {
            "errors": {
                "pitcher": "Pitcher \"Not a Real Pitcher\" not allowed"
            },
            "warnings": {}
        }
    }
```

- **Python**:
    ```python
    from compbaseball import baseball

    def parse_user_inputs(params, jsonparams, errors_warnings, **meta_parameters):
        # parse the params, jsonparams, and errors_warnings further
        use_2018 = meta_parameters["use_2018"]
        params, jsonparams, errors_warnings = baseball.parse_inputs(
            params, jsonparams, errors_warnings, use_2018=use_2018)
        # done parsing
        return params, jsonparams, errors_warnings
    ```

Run simulation
----------------

Accepts meta-parameter values and parsed and formatted user inputs. Returns outputs as specified by the [Outputs schema](IOSCHEMA.md)

COMP submits the model's meta parameters and the parsed and formatted inputs:
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
    from compbaseball import baseball

    def run_simulation(use_2018, user_mods):
        result = baseball.get_matchup(use_2018, user_mods)
        return result
    ```
