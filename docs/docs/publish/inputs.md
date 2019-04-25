# Inputs

COMP uses the ParamTools inputs format for building its GUI. ParamTools also offers functionality for updating parameter values and validating the new values. Check out the [ParamTools documentation](https://paramtools.org) for more information on how to create your configuration files. COMP requires two typs of inputs: meta parameters and model parameters.

**First, what are *meta parameters*?**

Meta parameters *control* the default parameters. If the value of a parameter depends on the current year, then the user will need to set the current year via a meta parameter before they can view the parameter's default value and update it.

### Meta Parameters

For example, the meta parameters for [PSLmodels/Tax-Brain](https://www.compmodels.org/PSLmodels/Tax-Brain/) are defined like this:

```json
{
    "schema": {
        "labels": {},
        "additional_members": {}
    },
    "start_year": {
        "title": "Start Year",
        "description": "Year for parameters.",
        "type": "int",
        "value": 2019,
        "validators": {"range": {"min": 2019, "max": 2027}}
    },
    "data_source": {
        "title": "Data Source",
        "description": "Data source can be PUF or CPS",
        "type": "str",
        "value": "PUF",
        "validators": {"choice": {"choices": ["PUF", "CPS"]}}
    },
    "use_full_sample": {
        "title": "Use Full Sample",
        "description": "Use entire data set or a 2% sample.",
        "type": "str",
        "value": true,
        "validators": {}
    }
}
```

COMP uses this information to build a set of controls that dictate which values of the default model parameters are shown:

[![alt text](https://user-images.githubusercontent.com/9206065/56739962-eee28780-673d-11e9-836c-21efdced5f3b.png)](https://www.compmodels.org/PSLmodels/Tax-Brain/)

### Default Parameters

The GUI is built directly from the default parameters. Here's an example using a subset of the inputs from [hdoupe/Matchups](https://www.compmodels.org/hdoupe/Matchups/):



```json
{
    "schema": {
        "labels": {
            "use_full_data": {"type": "bool", "validators": {}}
        },
        "additional_parameters": {
            "section_1": {"type": "str", "number_dims": 0},
            "section_2": {"type": "str", "number_dims": 0}
        }
    },
    "start_date": {
        "title": "Start Date",
        "description": "Date to start pulling statcast information",
        "section_1": "Date",
        "section_2": "",
        "notes": "If using the 2018 dataset, only use dates in 2018.",
        "type": "date",
        "value": [
            {"use_full_data": true, "value": "2008-01-01"},
            {"use_full_data": false, "value": "2018-01-01"}
        ],
        "validators": {"date_range": {"min": "2008-01-01", "max": "end_date"}}
    },
    "pitcher": {
        "title": "Pitcher Name",
        "description": "Name of pitcher to pull data on",
        "section_1": "Parameters",
        "section_2": "Pitcher",
        "type": "str",
        "value": "Clayton Kershaw",
        "validators": {
            "choice": {
                "choices": ["Clayton Kershaw", "Jacob deGrom", "Justin Verlander"]
            }
        }
    }
}


```

COMP builds the model parameter GUI directly from this data:

[![alt text](https://user-images.githubusercontent.com/9206065/56739963-eee28780-673d-11e9-8692-59f58af2b5ff.png)](https://www.compmodels.org/hdoupe/Matchups/)