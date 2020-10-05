# Publishing on Compute Studio

This guide describes how to publish a model on Compute Studio. The Compute Studio framework depends on model interfaces meeting several Compute Studio criteria, and we walk you through how to meet those criteria, either by modifying your model's interface or building a new wrapper interface around your model. The great part is that you don't have to deal with any web technology to build your Compute Studio app.

If you have any questions as you proceed through this guide, send Hank an email at <a href="mailto:hank@compute.studio">hank@compute.studio</a>.

## Data formats

Compute Studio relies on two data formats, one for the [inputs](/publish/inputs) and one for the [outputs](/publish/outputs/). These are JSON schemas that your model will need to adopt for Compute Studio to be able to generate input forms representing your model's default specification, validate user adjustments, and display model outputs.

## Functions

Compute Studio interacts with your model using [4 Python functions](/publish/functions/): one for getting the model's version, one for getting the default inputs, one for validating user inputs, and one for running the model.

## Publish

Now it's time to publish your model. The first step is to install [Compute Studio Kit](https://github.com/compute-tooling/compute-studio-kit/#compute-studio-kit) via `pip install cs-kit`. Next, create a directory named `cs-config` in your model's source code repository with the command `csk-init`. This creates a light-weight python package that includes an installation script, a `functions.py` file with stubs for each of the four Python functions, and a [py.test](https://docs.pytest.org/en/latest/) ready test suite located at `cs-config/cs_config/tests/test_functions.py`. Once you've filled in your functions, you can test whether they are compliant with the C/S criteria by running `py.test cs-config/`.

Once your functions are passing the `cs-kit` tests, fill out the [publish form](https://compute.studio/publish) that asks you to provide a title and overview for your new Compute Studio app and a link to your model's source code repository. If you would like to see a publishing template that has already been completed, you can view the Matchups template [here](https://compute.studio/hdoupe/Matchups/detail).

Once you've submitted the publishing form, Hank will review it and get back to you within 24 hours to inform you whether the model is ready to be published or if there are criteria that have not been satisfied. Your model will be deployed to Compute Studio once it has met all of the critera. You will have the opportunity to test it out after it has been deployed.
