# Input-Output Schema

COMP relies on three primary JSON schemas: Meta Parameters, Model Parameters, and Outputs. COMP uses them to derive the COMP input form representing your model's default specification and your model's output page. One of the required Python functions in the next step of this guide will also rely on these scheme to validate user adjustments on the COMP input form. 

Meta Parameters
--------------------------------

These are the parameters upon which Model Parameters depend. For example, if your model's default Model Parameters depend on the dataset being used, a meta parameter named `data_set` could be helfpul. This should be of the form:

```json
{
    "variable_name": {
        "title": "Variable Name",
        "default": "default value",
        "type": "int, boolean, string, date",
        "validators": {
            "range": {"min": "minvalue", "max": "maxvalue"},
            "choices": {"choices": ["list of choices"]}
        }
    }
}
```

Notes:
- Supported types are `"int"`, `"float"`, `"bool"`, `"str"`, and `"date"`. Parameters of type `"date"` expect the format `"YYYY-MM-DD"`.
- Validators are optional. More validators will be added in the future.

Model Parameters
----------------

COMP uses the JSON schema below for documenting Model Parameters and their values under the default sepcification:

```json
{
    "majorsection1": {
        "param_name1": {
            "long_name": "Human Readable Name of Parameter",
            "description": "Description of this parameter",
            "section_1": "Section of parameters that are like this one",
            "section_2": "Subsection of section 1",
            "notes": "More notes on this parameter.",
            "type": "type here",
            "value": "value here",
            "validators": {
                "range": {"min": "minvalue", "max": "maxvalue"},
                "choice": {"min": "minvalue", "max": "maxvalue"}
            }
        }
    },
    "majorsection2": {
    }
}
```

Notes:
- The major sections can be thought of as broad categories of model parameters. A baseball model may break up its model parameters into Hitting, Pitching, and Fielding major sections.
- Supported types are `"int"`, `"float"`, `"bool"`, `"str"`, and `"date"`. Parameters of type `"date"` expect the format `"YYYY-MM-DD"`.

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

[1]: https://github.com/PSLmodels/Tax-Calculator
[2]: https://github.com/hdoupe/ParamProject
