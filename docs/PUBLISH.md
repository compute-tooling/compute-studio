# Publishing on COMP

This document describes how to publish a model on COMP. The COMP framework was built such that if a project meets all of the COMP criteria, then it can be plugged in with minimal custom work.

The documentation is split into three parts. The [first part](IOSCHEMA.md) documents the inputs and outputs schemas that are at the core of COMP's ability to display input forms, validate user input, and display outputs. The [second part](ENDPOINTS.md) documents the python functions that will be used by COMP to get data from and submit data to the project. The [third part](ENVIRONMENT.md) is where the project's installation process is defined.

Once you've completed this guide, send me an email at henrymdoupe@gmail.com containing the following pieces of information:

- How long will each model simulation take? What are the memory requirements of the model? This information will be used to choose the server size and provide price estimates to the user before they run the model.
- Code snippets showing how each of the three python functions in the [functions documentation](ENDPOINTS.md) are to be called.
- Installation instructions as described in [the installation documentation](ENVIRONMENT.md).

I will then review your work. If all of the criteria has been met, it will be deployed to COMP. If there are any issues, then I will work with you to resolve them. Once the model has been deployed, you will have the opportunity to test it out. Since COMP is an open-source website, you can check my work to verify that the code was plugged in correctly.

If you have any questions about this guide, feel free to email me at henrymdoupe@gmail.com. I'm happy to help.

For those who are interested in a more detailed explanation of how a model is published on COMP, feel free to checkout the [Technical Publishing Guide](TECHNICALPUBLISHING.md).