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
    from compbaseball import baseball

    def package_defaults(**meta_parameters):
        return baseball.get_inputs(use_2018=meta_parameters["use_2018"])
    ```

    Here's what you get after filling in this function:
    ![alt text](https://user-images.githubusercontent.com/9206065/50243845-480b6a80-039c-11e9-8452-029fefd866b0.png)

Parse user adjustemnts
----------------------
Accepts parsed user adjustments, separated by each major section. Returns parsed user adjustments, JSON representation of the user adjustments, and warnings/errors (if any).

COMP will provide parsed user adjustments of the form:

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

    def parse_user_inputs(params, jsonparams, errors_warnings,
                            **meta_parameters):
        # parse the params, jsonparams, and errors_warnings further
        use_2018 = meta_parameters["use_2018"]
        params, jsonparams, errors_warnings = baseball.parse_inputs(
            params, jsonparams, errors_warnings, use_2018=use_2018)
        return params, jsonparams, errors_warnings
    ```

    Here's what you get after filling in this function:
    ![alt text](https://user-images.githubusercontent.com/9206065/50243758-0a0e4680-039c-11e9-9a98-56e2cbdd2f8f.png)

    The `jsonparams` data is displayed on the outputs page:

    ![alt text](https://user-images.githubusercontent.com/9206065/50363819-60fe5200-053b-11e9-8b5c-e2eafe7f2668.png)

Run simulation
----------------

Accepts Meta Parameters values and parsed and formatted user adjustments. Returns outputs as specified by the [Outputs schema](IOSCHEMA.md)

COMP submits the model's meta parameters and the parsed and formatted user adjustments:
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

    Here's what you get after filling in this function:

    Aggregate outputs:
    ![alt text](https://user-images.githubusercontent.com/9206065/50352415-21bc0b00-0513-11e9-9fc2-b84cedb3cafe.png)

    Outputs:
    ![alt text](https://user-images.githubusercontent.com/9206065/50352416-21bc0b00-0513-11e9-8ec8-260a80b6c114.png)

    Toggle along dimension:
    ![alt text](https://user-images.githubusercontent.com/9206065/50352417-21bc0b00-0513-11e9-8e4e-d0bb329e842e.png)