# Publishing on Compute Studio

This guide describes how to publish a model on Compute Studio. The Compute Studio framework depends on model interfaces meeting several Compute Studio criteria, and we walk you through how to meet those criteria, either by modifying your model's interface or building a new wrapper interface around your model. The great part is that you don't have to deal with any web technology to build your Compute Studio app.

If you have any questions as you proceed through this guide, send Hank an email at hank@compute.studio.

The documentation is split into three parts.

- The first part documents the [inputs](/publish/inputs) and [outputs](/publish/outputs/) JSON schemas that your model will need to adopt for Compute Studio to be able to generate input forms representing your model's default specification, validate user adjustments, and display model outputs.
- The [second part](/publish/functions/) documents the python functions that will be used by Compute Studio to get data from and submit data to your model.
- The third part is a [publish form](https://compute.studio/publish) that asks you to provide a title and overview for your new Compute Studio app, code snippets for the three python functions, and information describing your app's resource requirements and installation directions. If you would like to see a publishing template that has already been completed, you can view the Matchups template [here](https://compute.studio/hdoupe/Matchups/detail).

Once you've submitted the publishing form, Hank will review it and get back to you within 24 hours to inform you whether the model is ready to be published or if there are criteria that have not been satisfied. Your model will be deployed to Compute Studio once it has met all of the critera. You will have the opportunity to test it out after it has been deployed.
