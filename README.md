# Compute Studio

**Compute Studio** is an open-source platform for sharing models and simulations.

To see Compute Studio in action, visit [Compute.Studio](https://Compute.Studio).

Principles:
- Freely share models and simulations with the public.
- Pay for your own resources, like compute, at cost.
- Sponsor resources for others if you'd like.

Features:
- A web-based GUI for decisionmakers makes it easy to interact with models and simulations from the browser.
- The web API enables developers to include CS models in their own applications.
- Personal libraries store simulations for users, including both inputs and results.

Under development:
- Sharing and privacy features for simulations and models.

## Contributing

Compute Studio is an open source project and anyone can contribute code or suggestions.

You can reach Compute Studio developers to discuss how to get started by opening an issue or joining the Compute Studio Community [chat room](https://riot.im/app/#/room/!WQWxPnwidsSToqkeLk:matrix.org).

## Development process

1. Download the code: `git clone git@github.com:compute-tooling/compute-studio.git`
1. Fetch branches: `git fetch origin`
1. Checkout the `dev` branch: `git checkout dev`
1. Checkout the feature branch from this `dev` branch: `git checkout my-new-feature`
1. Make some changes and commit them to `my-new-feature`. When you're ready, open a pull request on the `dev` branch.
1. Merge PR to `dev` branch for testing on https://dev.compute.studio
1. Repeat process until feature / bug fix is ready.
1. Deploy to production by opening a PR from the `dev` to the `master` branch.

## Local Development (the easy way)

This is the easiest way to get up and running with a local compute studio webserver. It requires an existing database (e.g. the test database for dev.compute.studio). With this setup, you can still view the home dashboard and run simulations and apps.

### Get the code, install Docker and friends, and install node.
1. Download the code: `git clone git@github.com:compute-tooling/compute-studio.git`
2. Fetch branches: `git fetch origin`
3. Checkout the `dev` branch: `git checkout dev`
4. Install Docker and Docker Compose:
  - https://docs.docker.com/get-docker/
  - https://docs.docker.com/compose/install/
5. Install node and yarn:
    - https://nodejs.org
    - `npm install yarn`

### Set up credentials for database access and run
6. Copy `.env.example` to `.env` and fill in the variables.
7. Save your google cloud credentials in a file named `google-creds.json`.
8. Start the webserver: `docker-compose up`

### Install JavaScript dependencies and run the JavaScript build server:
9. In another terminal window, install JavaScript dependencies: `yarn install`
10. Then, run the dev server: `yarn start`

### Checkout the devlopment server at http://localhost:8000 !!!

## Local Development (the hard way)

This isn't for the faint of heart, but if you must, here's the [guide](local-deployment.md).

## License

Compute Studio is licensed under the open source [GNU Affero General Public License](/License.txt) to Compute Tooling, Inc.
