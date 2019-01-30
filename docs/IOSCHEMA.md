# Input-Output Schema

COMP relies on three primary JSON schemas: Meta Parameters, Model Parameters, and Outputs. COMP uses them to derive the COMP input form representing your model's default specification and your model's output page. One of the required Python functions in the next step of this guide will also rely on these schemas to validate user adjustments on the COMP input form. The [ParamTools][3] project is compatible with the inputs schemas below and can be used for the parameter processing and validation that is described in the Python functions documentation.

Meta Parameters
--------------------------------

These are the parameters upon which Model Parameters depend. For example, if your model's default Model Parameters depend on the dataset being used, a meta parameter named `data_set` could be helfpul. This should be of the form:

- "variable_name": The name of the meta parameter as it is used in the modeling project.
- "title": A human readable name for the parameter.
- "default": A default value for the meta parameter.
- "type": The parameter's data type. Supported types are:
  - "int": Integer.
  - "float": Floating point.
  - "bool": Boolean. Either `True` or `False`.
  - "str"`: String.
  - "date": Date. Needs to be of the format `"YYYY-MM-DD"`.
- "validators": A mapping of [Validator Objects](#validator-object).

Example:

```json
{
    "time_of_day": {
        "title": "Time of the Day",
        "default": 12,
        "type": "int",
        "validators": {
            "range": {"min": 0, "max": 23}
        }
    }
}
```

Model Parameters
----------------

COMP uses the JSON schema below for documenting Model Parameters and their values under the default sepcification:

- "major_section": Broad categories of model parameters. A baseball model may break up its model parameters into Hitting, Pitching, and Fielding major sections.
- "param_name": The name of the parameter as it is used in the modeling project.
- "title": A human readable name for the parameter.
- "description": Describes this parameter.
- "notes": Any additional information that should be displayed to the user.
- "section_1": Section of parameters that are like this one
- "section_2": Subsection of section 1.
- "type": The parameter's data type. Supported types are:
  - `"int"` - Integer.
  - `"float"`- Floating point.
  - `"bool"`- Boolean. Either `True` or `False`.
  - `"str"` - String.
  - `"date"`- Date. Needs to be of the format `"YYYY-MM-DD"`.
- "value": A list of [Value Objects](#value-object). Describes the default values of the parameter.
- "validators": A mapping of [Validator Objects](#validator-object).

Example:

```json
{
    "weather": {
        "temperature": {
            "title": "Temperature",
            "description": "Temperature at a given hour in the day",
            "section_1": "Hourly Weather",
            "section_2": "Standard Measurements",
            "notes": "This is in Fahrenheit.",
            "type": "int",
            "value": [
                {"time_of_day": 0, "value": 40},
                {"time_of_day": 8, "value": 38},
                {"time_of_day": 16, "value": 50}
            ],
            "validators": {
                "range": {"min": -130, "max": 135}
            }
        }
    }
}
```



Outputs
------------

Currently, tables are the only supported media that can be served. In the future, COMP will serve media such as pictures and charts.

Upstream projects can specify downloadable content such as CSVs in addition to the rendered content.

A tag system is used to organize the outputs. For example, a baseball model might produce outputs for each of baseball's two leagues and have tags: `{"league": "american"}` and `{"league": "national"}`. There can be multiple levels of tags. Continuing the previous example, there could be a muti-level tag `{"league": "american", "team": "yankees"}` or `{"league": national", "team": "braves"}`.

There are two types of outputs. One type is "Aggregate Outputs." These will be displayed at the top of the outputs page. The other type is "Outputs." A `dimension` attribute can be specified for each set of outputs. If it is specified, the `dimension` attribute will be used to toggle between different sets of outputs. For example, a baseball model that runs on each season over a ten year period will have a dimension attribute named `"Season"` and a set of outputs that corresponds to each of those seasons.

The Outputs Schema:

```json
{
    "aggr_outputs": [
        {
            "tags": {"category": "a category"},
            "title": "Title to be displayed",
            "downloadable": [
                {
                    "filename": "filename.csv",
                    "text": "data here"
                },
            ],
            "renderable": "HTML table to render"
        }
    ],
    "outputs": [
        {
            "tags": {"category": "a category", "subcategory": "a subcategory"},
            "dimension": "Dimension corresponding to the task producing this output",
            "title": "Title to be displayed (may want to include dimension)",
            "downloadable": [
                {
                    "filename": "filename.csv",
                    "text": "data here"
                },
            ],
            "renderable": "HTML table to render"
        },
    ],
    "meta": {
        "task_times": ["list of task times in seconds"],
        "version": "model version, e.g. 1.1.0"
    }
}
```

JSON Objects
---------------

### Validator Object
- Used for validating user input.
- Available validators:
  - "range": Define a minimum and maximum value for a given parameter.
    - Arguments:
      - "min": Minimum allowed value.
      - "max": Maximum allowed value.
    - Example:
        ```json
        {
            "range": {"min": 0, "max": 10}
        }
        ```
  - "choice": Define a set of values that this parameter can take.
    - Arguments:
      - "choice": List of allowed values.
    - Example:
        ```json
        {
            "choice": {"choices": ["allowed choice", "another allowed choice"]}
        }
        ```

### Value Object
- Used for defining the value of a parameter. The Value Object consists of a "value" attribute indicating the parameter's value and zero or more key-value pairs that describe the dimensions of the parameter space that the value should be applied to.
- Example:
    ```json
    {"time_of_day": 0, "value": 40},
    ```

[1]: https://github.com/PSLmodels/Tax-Calculator
[2]: https://github.com/hdoupe/ParamProject
[3]: https://github.com/PSLmodels/ParamTools