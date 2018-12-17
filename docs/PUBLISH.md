# Publishing on COMP

This document describes how to publish a model on COMP. The COMP framework was built such that if a project meets all of the COMP criteria, then it can be plugged in with minimal custom work.

The documentation is split into three parts. The [first part](IOSCHEMA.md) documents the inputs and outputs schemas that are at the core of COMP's ability to display input forms, validate user input, and display outputs. The [second part](ENDPOINTS.md) documents the API endpoints that will be used by COMP to get data from and submit data to the project. The [third part](ENVIRONMENT.md) is where the project's installation process is defined.

Once you've completed this guide, send me an email at henrymdoupe@gmail.com containing the following pieces of information:

- How many tasks will the average model run require? About how long will each of the tasks take to complete? What are the memory requirements of this project? This will be used to choose the server size and provide price estimates to the user before they run the model.
- Code snippets showing how each of the four endpoints in the [endpoints documentation](ENDPOINTS.md) are to be called.
- Installation instructions as described in [the installation documentation](ENVIRONMENT.md).

I will then review your work and work with you to get the project up and running. COMP is an open-source website. Thus, you will be able to verify that the code was plugged in correctly. Further, you can download the results and compare them yourself.

If you have any questions about this guide, feel free to email me at henrymdoupe@gmail.com. I'm happy to help.

For those who are interested in a more detailed explanation of how a model is published on COMP, feel free to checkout the [Technical Publishing Guide](TECHNICALPUBLISHING.md).