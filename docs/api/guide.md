# API Guide

Compute Studio offers a REST API to do things like:

- Create new simulations
- View data for existing simulations
- View a model's inputs documentation

The REST API is intended for users who would like to build applications on top of the Compute Studio interface or create simulations programmatically.

The Compute Studio [Python client](/api/python-api/) takes care of low-level details like like managing API Tokens and using the correct HTTP verbs. Checkout the more practical example [here](/api/python-client-example/).

```{note}
An API token is required for requests that modify data. Find out how to get your token [here](/api/auth/).
```

More information about the data formats used by the API can be found in the Compute Studio publishing documentation on [inputs](/publish/model/inputs/) and [outputs](/publish/model/outputs/).
