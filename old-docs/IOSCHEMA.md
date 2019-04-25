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

COMP uses the JSON schema below for documenting Model Parameters and their values under the default sepcification. This schema is compliant with the ParamTools specification schema. You can find a [more complete guide][4] for the Model Parameters in the ParamTools documentation.

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



[1]: https://github.com/PSLmodels/Tax-Calculator
[2]: https://github.com/hdoupe/ParamProject
[3]: https://github.com/PSLmodels/ParamTools
[4]: https://paramtools.readthedocs.io/en/latest/spec.html