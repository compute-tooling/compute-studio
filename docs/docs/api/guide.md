# API Guide

Compute Studio offers a REST API for creating simulations, viewing existing simulations, and viewing the input parameters for a given model. This is intended for users who would like to build applications on top of the Compute Studio interface or create simulations programmatically. An API token is required for requests that modify data. Find out how to get your token [here](/api/auth/).

More information about the data formats that are shown below can be found in the Compute Studio publishing documentation on [inputs](/publish/inputs/) and [outputs](/publish/outputs/).

This guide details the Compute Studio API endpoints and schema. A more practical [Python example](/api/python/) is also provided.

## /[owner]/[title]/api/v1/

Used for creating simulations.

Supports POST HTTP actions.

### Create simulation

```bash
POST hdoupe/Matchups/api/v1/
```

**Example:**

```json
{
  "meta_parameters": {
    "use_full_data": true
  },
  "adjustment": {
    "matchup": {
      "pitcher": "Max Scherzer"
    }
  }
}
```

**Response:**

```bash
HTTP/1.1 201 Created
Allow: GET, POST, HEAD, OPTIONS

{
    "api_url": "/hdoupe/Matchups/api/v1/22",
    "creation_date": "2019-05-31T10:43:03.105760-05:00",
    "eta": 0.33,
    "gui_url": "/hdoupe/Matchups/22/",
    "inputs": {
        "adjustment": {
            "matchup": {
                "pitcher": "Max Scherzer"
            }
        },
        "errors_warnings": {
            "API": {
                "errors": {},
                "warnings": {}
            },
            "GUI": {
                "errors": {},
                "warnings": {}
            },
            "matchup": {
                "errors": {},
                "warnings": {}
            }
        },
        "custom_adjustment": null,
        "meta_parameters": {
            "use_full_data": true
        }
    },
    "model_pk": 22,
    "outputs": null,
    "traceback": null
}

```

## /[owner]/[title]/api/v1/[model_pk]

Used for getting simulations.

Supports GET HTTP actions.

### Get simulation

```bash
GET /hdoupe/Matchups/api/v1/22
```

**Response:**

```bash
HTTP 200 OK
Allow: GET, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "inputs": {
        "meta_parameters": {
            "use_full_data": true
        },
        "adjustment": {
            "matchup": {
                "pitcher": "Max Scherzer"
            }
        },
        "custom_adjustment": null,
        "errors_warnings": {
            "API": {
                "errors": {},
                "warnings": {}
            },
            "GUI": {
                "errors": {},
                "warnings": {}
            },
            "matchup": {
                "errors": {},
                "warnings": {}
            }
        }
    },
    "outputs": {
        "renderable": [
            {
                "title": "Max Scherzer v. All batters",
                "media_type": "bokeh",
                "data": {
                    "html": "html here",
                    "javascript": "javascript here"
                }
            },
            {
                "title": "Max Scherzer v. Chipper Jones",
                "media_type": "bokeh",
                "data": {
                    "html": "html here",
                    "javascript": "javascript here"
                }
            }
        ],
        "downloadable": [
            {
                "title": "Max Scherzer v. All batters",
                "media_type": "CSV",
                "data": "csv here"
            },
            {
                "title": "Max Scherzer v. Chipper Jones",
                "media_type": "CSV",
                "data": "csv here"
            }
        ]
    },
    "traceback": null,
    "creation_date": "2019-05-31T11:41:22.211492-05:00",
    "api_url": "/hdoupe/Matchups/api/v1/23",
    "gui_url": "/hdoupe/Matchups/23/",
    "eta": 0.0,
    "model_pk": 23
}

```

## /[owner]/[title]/api/v1/inputs/

Used for viewing the inputs for a given model.

Supports GET and POST HTTP actions.

### View inputs:

```bash
GET hdoupe/Matchups/api/v1/inputs/
```

**Response:**

```
HTTP 200 OK
Allow: GET, POST, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "meta_parameters": {
        "use_full_data": {
            "type": "bool",
            "title": "Use Full Data",
            "value": [
                {
                    "value": true
                }
            ],
            "validators": {
                "choice": {
                    "choices": [
                        true,
                        false
                    ]
                }
            },
            "description": "Flag that determines whether Matchups uses the 10 year data set or the 2018 data set.",
            "number_dims": 0
        }
    },
    "model_parameters": {
        "matchup": {
            "start_date": {
                "type": "date",
                "section_1": "Date",
                "title": "Start Date",
                "value": [
                    {
                        "value": "2008-01-01",
                        "use_full_data": true
                    }
                ],
                "validators": {
                    "date_range": {
                        "max": "end_date",
                        "min": "2008-01-01"
                    }
                },
                "description": "Date to start pulling statcast information",
                "section_2": "",
                "notes": "If using the 2018 dataset, only use dates in 2018.",
                "number_dims": 0
            },
            "pitcher": {
                "type": "str",
                "section_1": "Parameters",
                "title": "Pitcher Name",
                "value": [
                    {
                        "value": "Clayton Kershaw",
                        "use_full_data": true
                    }
                ],
                "validators": {
                    "choice": {
                        "choices": [
                            "A. J. Achter",
                            "A. J. Burnett",
                            "A. J. Cole",
                            "A. J. Ellis",
                            "A. J. Griffin",
                            "A. J. Jimenez",
                            "A. J. Minter",
                            "A. J. Morris",
                            "A. J. Murray",
                            "A. J. Pierzynski",
                            "A. J. Pollock",
                            "A. J. Reed",
                            "A. J. Schugel",
                            "AJ Ramos",
                            "Aaron Altherr",
                            "Aaron Barrett",

    ...
```

### Update with meta parameters

```bash
POST /hdoupe/Matchups/api/v1/inputs/
```

**Example:**

```json
{
  "meta_parameters": { "use_full_data": true }
}
```

**Response:**

```
HTTP 200 OK
Allow: GET, POST, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "meta_parameters": {
        "use_full_data": {
            "type": "bool",
            "title": "Use Full Data",
            "value": [
                {
                    "value": false
                }
            ],
            "validators": {
                "choice": {
                    "choices": [
                        true,
                        false
                    ]
                }
            },
            "description": "Flag that determines whether Matchups uses the 10 year data set or the 2018 data set.",
            "number_dims": 0
        }
    },
    "model_parameters": {
        "matchup": {
            "start_date": {
                "type": "date",
                "section_1": "Date",
                "title": "Start Date",
                "value": [
                    {
                        "value": "2018-01-01",
                        "use_full_data": false
                    }
                ],
                "validators": {
                    "date_range": {
                        "max": "end_date",
                        "min": "2008-01-01"
                    }
                },
                "description": "Date to start pulling statcast information",
                "section_2": "",
                "notes": "If using the 2018 dataset, only use dates in 2018.",
                "number_dims": 0
            },
            "pitcher": {
                "type": "str",
                "section_1": "Parameters",
                "title": "Pitcher Name",
                "value": [
                    {
                        "value": "Jacob deGrom",
                        "use_full_data": false
                    }
                ],
                "validators": {
                    "choice": {
                        "choices": [
                            "A. J. Achter",
                            "A. J. Burnett",
                            "A. J. Cole",
                            "A. J. Ellis",
                            "A. J. Griffin",
                            "A. J. Jimenez",
                            "A. J. Minter",
                            "A. J. Morris",
                            "A. J. Murray",
                            "A. J. Pierzynski",
    ...
```

[1]: https://github.com/compute-tooling/compute-studio-kit#comp-studio-toolkit
[2]: https://httpie.org/
