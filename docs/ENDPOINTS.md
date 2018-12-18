# API endpoints

The modeling project must provide an API endpoint for each of the following tasks:
- Get the baseline inputs and their meta data
- Do model-specific formatting and validation on the user inputs
- Define the tasks for a given user submission
- Submit each task to the modeling project
- Combine the results after all of the tasks have run

The four API endpoints and a corresponding code snippet are discussed below:

Package defaults
----------------------

Accepts meta-parameters, if they are being utilized. Returns data in the form specified in the "Inputs Schema" section of [`IOSCHEMA.md`](IOSCHEMA.md).

- **Python**:
    ```python
    from compbaseball import baseball

    def get_inputs(use_2018): # use_2018 is a metaparameter
        return baseball.get_inputs(use_2018=use_2018)
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

    def parse_inputs(parsed_inputs, jsonstr, errors_warnings):
        (parsed_inputs,
            jsonstr,
            errors_warnings) = baseball.parse_inputs(parsed_inputs, jsonstr,
                                                      errors_warnings)
        return parsed_inputs, jsonstr, errors_warnings
    ```


Define the inputs for each task
-----------------------------------

Accepts data that has been parsed, formatted, and validated. Returns list of tasks to be submitted to the modeling project. COMP allows the model to run tasks in parallel but only when the parallel tasks can be defined prior to submiting them to the modeling project. For example, in the baseball data example, one can view historical data on how a pitcher has pitched to several batters. So, the relationship between the pitcher and each hitter can be evaluated in parallel. Each task will be submitted to the endpoint defined in the "Run tasks" section below.

Parsed data:

```json
[{
    "use_2018": false,
    "matchup": {
        "pitcher": "Clayton Kershaw",
        "batter": ["Freddie Freeman", "Bryce Harper", "Aaron Judge"]
    }
}]
```

Extended data:
```json
[{
    "use_2018": false,
    "matchup": {
        "pitcher": "Clayton Kershaw",
        "batter": "Freddie Freeman"
    }
},
{
    "use_2018": false,
    "matchup": {
        "pitcher": "Clayton Kershaw",
        "batter": "Brye Harper"
    }
}
{
    "use_2018": false,
    "matchup": {
        "pitcher": "Clayton Kershaw",
        "batter": "Aaron Judge"
    }
}]
```

- **Python**
    ```python
    def extend_data(inputs): # meta-parameters are included
        tasks = []
        for batter in inputs[0]["matchups"]["batter"]:
            tasks.append({
                "use_2018": inputs[0]["use_2018"]
                "matchup": {
                    "pitcher": inputs[0]["pitcher"],
                    "batter": batter
                }
            })

        return tasks
    ```


Run tasks
----------------

Accepts meta-parameter values and parsed and formatted user inputs. Returns the result of each task as an object that can be serialized to JSON.

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

- **Python**:
    ```python
    from compbaseball import baseball

    def submit_inputs(use_2018, user_mods):
        result = baseball.get_matchup(use_2018, user_mods)
        return result
    ```


Combine task results
-------------------------

 Accepts list consisting of the results from each of the tasks. Returns combnined results of the format specified in the "Outputs schema" section of [`IOSCHEMA.md`](IOSCHEMA.md).

 - **Python**:
    ```python
    from compbaseball import baseball

    def aggregate_outputs(outputs):
        result = baseball.combine_outputs(outputs)
        return result
    ```


[1]: https://en.wikipedia.org/wiki/Embarrassingly_parallel