"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import { Nav, Tab, Col, ThemeProvider } from "react-bootstrap";
import axios, { AxiosError } from "axios";
import * as Sentry from "@sentry/browser";
import * as yup from "yup";
import ReactLoading from "react-loading";

import InputsForm, { tbLabelSchema } from "./InputsForm";
import OutputsComponent from "./Outputs";
import {
  AccessStatus,
  Inputs,
  InitialValues,
  Simulation,
  RemoteOutputs,
  Outputs,
  Sects,
  InputsDetail,
} from "../types";
import DescriptionComponent from "./Description";
import API from "./API";
import ErrorBoundary from "../ErrorBoundary";
import { convertToFormik, formikToJSON, Persist } from "../ParamTools";
import { Formik, Form, FormikProps, FormikHelpers } from "formik";
import { hasServerErrors } from "../utils";
import { UnsavedChangesModal } from "./modal";
import { AuthPortal, AuthButtons } from "../auth";
import { RolePerms } from "../roles";
import { Utils as SimUtils } from "./sim";

Sentry.init({
  dsn: "https://fde6bcb39fda4af38471b16e2c1711af@sentry.io/1530834",
});

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const domContainer = document.querySelector("#inputs-container");

interface URLProps {
  match: {
    params: {
      owner: string;
      title: string;
      modelpk: string;
    };
  };
}

interface SimAppProps extends URLProps {}

interface SimAppState {
  // keep track of which tab is open
  key: "inputs" | "outputs";
  hasShownDirtyWarning: boolean;
  showDirtyWarning: boolean;

  // show run modal on page load.
  showRunModal: boolean;

  // show collaborator modal on page load.
  showCollabModal: boolean;

  // necessary for user id and write access
  accessStatus?: AccessStatus;

  // all meta data for the inputs of a sim.
  inputs?: Inputs;

  // Keep track of whether the user wants a
  // notification on sim completion.
  notifyOnCompletion: boolean;

  // Keep track of whether the sim is public.
  // This is only used for the run modal.
  isPublic: boolean;

  // all meta data for the outputs of a sim.
  remoteSim?: Simulation<RemoteOutputs>;
  sim?: Simulation<Outputs>;

  // necessary for form state
  initialValues?: InitialValues;
  schema?: { adjustment: yup.Schema<any>; meta_parameters: yup.Schema<any> };
  sects?: Sects;
  unknownParams?: Array<string>;
  extend?: boolean;
  resetting?: boolean;

  error?: Error;
}

class SimTabs extends React.Component<
  SimAppProps & { tabName: "inputs" | "outputs" },
  SimAppState
> {
  api: API;
  constructor(props) {
    super(props);
    const { owner, title, modelpk } = this.props.match.params;
    this.api = new API(owner, title, modelpk);
    const search = props.location.search;
    const showRunModal = new URLSearchParams(search).get("showRunModal") === "true";
    const showCollabModal = new URLSearchParams(search).get("showCollabModal") !== null;
    this.state = {
      key: props.tabName,
      hasShownDirtyWarning: false,
      showDirtyWarning: false,
      notifyOnCompletion: false,
      isPublic: true,
      showRunModal: showRunModal,
      showCollabModal: showCollabModal,
    };

    this.handleTabChange = this.handleTabChange.bind(this);
    this.resetInitialValues = this.resetInitialValues.bind(this);
    this.resetAccessStatus = this.resetAccessStatus.bind(this);
    this.authenticateAndCreateSimulation = this.authenticateAndCreateSimulation.bind(this);
    this.setNotifyOnCompletion = this.setNotifyOnCompletion.bind(this);
    this.setIsPublic = this.setIsPublic.bind(this);
    this.submitWillCreateNewSim = this.submitWillCreateNewSim.bind(this);
    this.pollInputs = this.pollInputs.bind(this);
    this.setOutputs = this.setOutputs.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
  }

  async componentDidMount() {
    this.api.getAccessStatus().then(data => {
      this.setState({
        accessStatus: data,
      });
    });
    if (this.api.modelpk) {
      this.setOutputs();
    }
    let data: Inputs;
    if (this.api.modelpk) {
      const detail = await this.api.getInputsDetail();
      data = await this.api.getInputs(detail.meta_parameters);
      data.detail = detail;
    } else {
      data = await this.api.getInputs();
    }

    const [serverValues, sects, inputs, schema, unknownParams] = convertToFormik(data);
    let isEmpty = true;
    for (const msectvals of Object.values(data.detail?.adjustment || {})) {
      if (Object.keys(msectvals).length > 0) {
        isEmpty = false;
      }
    }
    let initialValues;
    if (isEmpty) {
      const storage = Persist.pop(
        `${this.props.match.params.owner}/${this.props.match.params.title}/inputs`
      );
      // Use values from local storage if available. Default to empty dict from server.
      initialValues = storage || serverValues;
    } else {
      initialValues = serverValues;
    }

    this.setState({
      inputs: inputs,
      initialValues: initialValues,
      sects: sects,
      schema: schema,
      unknownParams: unknownParams,
      extend: "extend" in inputs ? inputs.extend : false,
    });
  }

  async resetInitialValues(metaParameters: InputsDetail["meta_parameters"]) {
    this.setState({ resetting: true });
    const data = await this.api.resetInitialValues({
      meta_parameters: tbLabelSchema.cast(metaParameters),
    });
    const [
      initialValues,
      sects,
      { meta_parameters, model_parameters },
      schema,
      unknownParams,
    ] = convertToFormik(data);
    this.setState(prevState => ({
      inputs: {
        ...prevState.inputs,
        ...{
          meta_parameters: meta_parameters,
          model_parameters: model_parameters,
        },
      },
      initialValues: initialValues,
      sects: sects,
      schema: schema,
      unknownParams: unknownParams,
      resetting: false,
    }));
  }

  resetAccessStatus() {
    // Update authentication status, then the output
    // and inputs access statuses.
    this.api.getAccessStatus().then(accessStatus => {
      this.setState({ accessStatus });
      this.setOutputs();
      this.api.getInputsDetail().then(inputsDetail => {
        this.setState(prevState => ({
          inputs: {
            ...prevState.inputs,
            ...{ detail: inputsDetail },
          },
        }));
      });
    });
  }

  authenticateAndCreateSimulation() {
    // Update authentication status, create a new
    // and blank simulation, update the inputs and
    // outputs data.

    this.api.getAccessStatus().then(accessStatus => {
      if (accessStatus.username !== "anon") {
        this.api.createNewSimulation().then(newSim => {
          this.api.modelpk = newSim.sim.model_pk.toString();
          history.pushState(null, null, newSim.inputs.gui_url);
          this.setState(prevState => ({
            accessStatus: accessStatus,
            inputs: {
              ...prevState.inputs,
              ...{ detail: newSim.inputs },
            },
            remoteSim: newSim.sim,
          }));
        });
      }
    });
  }

  setNotifyOnCompletion(notify: boolean, fromPage: "outputs" | "inputs") {
    if (fromPage === "outputs") {
      let data = new FormData();
      data.append("notify_on_completion", notify.toString());
      this.api.putDescription(data).then(() => {
        this.setState(prevState => ({
          notifyOnCompletion: notify,
          remoteSim: {
            ...prevState.remoteSim,
            ...{ notify_on_completion: notify },
          },
        }));
      });
    } else {
      this.setState({ notifyOnCompletion: notify });
    }
  }

  async setIsPublic(is_public: boolean) {
    const { remoteSim } = this.state;
    if (remoteSim && !this.submitWillCreateNewSim()) {
      let data = new FormData();
      data.append("is_public", is_public.toString());
      await this.api.putDescription(data);
      const accessStatus = await this.api.getAccessStatus();
      this.setState(prevState => ({
        isPublic: is_public,
        remoteSim: {
          ...prevState.remoteSim,
          ...{ is_public: is_public },
        },
        accessStatus: accessStatus,
      }));
    } else {
      this.setState({ isPublic: is_public });
    }
  }

  submitWillCreateNewSim() {
    // returns true if a sim exists, the user has write access,
    // and the sim has not been kicked off yet.
    let { sim } = this.state.inputs.detail;
    return SimUtils.submitWillCreateNewSim(sim);
  }

  handleSubmit(values, actions) {
    const [meta_parameters, adjustment] = formikToJSON(
      values,
      yup.object().shape(this.state.schema),
      tbLabelSchema,
      this.state.extend,
      "year", // hard code until paramtools schema enforced.
      this.state.inputs.model_parameters
    );

    let formdata = new FormData();
    formdata.append("adjustment", JSON.stringify(adjustment));
    formdata.append("meta_parameters", JSON.stringify(meta_parameters));
    formdata.append("client", "web-beta");
    formdata.append("notify_on_completion", this.state.notifyOnCompletion.toString());
    formdata.append("is_public", this.state.isPublic.toString());
    let url = `/${this.api.owner}/${this.api.title}/api/v1/`;
    let sim = this.state.inputs.detail?.sim;
    const { accessStatus } = this.state;

    // Determine if user can create private sim. If not, set is_public to true.
    // User will be shown errors/limits to creating private sims elsewhere.
    const remainingPrivateSims =
      accessStatus.remaining_private_sims[accessStatus.project.toLowerCase()];
    const canCreatePrivateSim = accessStatus.plan.name === "free" && remainingPrivateSims <= 0;
    if (this.submitWillCreateNewSim() && canCreatePrivateSim) {
      formdata.set("is_public", "true");
    }

    // clicked new simulation button
    if (!this.submitWillCreateNewSim()) {
      url = sim.api_url;
    } else if (sim) {
      // sim is completed or user does not have write access
      formdata.append("parent_model_pk", sim.model_pk.toString());
    }
    this.api
      .postAdjustment(url, formdata)
      .then(data => {
        history.pushState(null, null, data.gui_url);
        this.api.modelpk = data.sim.model_pk.toString();
        this.setOutputs();
        this.api.getAccessStatus().then(accessStatus => {
          this.setState(prevState => ({
            inputs: { ...prevState.inputs, ...{ detail: data } },
            key: "inputs",
            accessStatus: accessStatus,
            hasShownDirtyWarning: false,
          }));
        });
        actions.setStatus({
          status: "PENDING",
        });
        // set submitting as false in poll func.
        if (data.status === "PENDING") {
          this.pollInputs(data, actions, values);
        }
      })
      .catch(error => {
        console.log("error", error);
        actions.setSubmitting(false);
        if (error.response.status == 403) {
          actions.setStatus({
            auth: "You must be logged in to create a simulation.",
          });
        }
      });
  }

  pollInputs(respData: InputsDetail, actions: FormikHelpers<InitialValues>, values) {
    setTimeout(() => {
      axios
        .get(respData.api_url)
        .then(response => {
          // be careful with race condidition where status is SUCCESS but
          // sim has not yet been submitted and saved!
          let data: InputsDetail = response.data;
          if (data.status === "SUCCESS" && data.sim !== null) {
            this.api.modelpk = data.sim.model_pk.toString();
            // 250ms buffer time for the backend to update the outputs object.
            this.pollOutputs(250);
            this.api.getAccessStatus().then(accessStatus => {
              this.setState(prevState => ({
                initialValues: values, // reset form with updated init vals.
                inputs: { ...prevState.inputs, ...{ detail: data } },
                key: "outputs",
                accessStatus: accessStatus,
              }));
            });
            actions.setStatus({
              status: data.status,
            });
            actions.setSubmitting(false);

            history.pushState(null, null, data.sim.gui_url);
          } else if (data.status === "INVALID" || data.status === "FAIL") {
            this.api.getAccessStatus().then(accessStatus => {
              this.setState(prevState => ({
                inputs: { ...prevState.inputs, ...{ detail: data } },
                key: "inputs",
                accessStatus: accessStatus,
              }));
            });
            let serverErrors;
            if (data.status === "INVALID") {
              serverErrors = data.errors_warnings;
            }
            actions.setStatus({
              status: data.status,
              serverErrors: serverErrors,
            });

            actions.setSubmitting(false);
            window.scroll(0, 0);
          } else {
            this.pollInputs(respData, actions, values);
          }
        })
        .catch(error => {
          console.log("polling error:");
          console.log(error);
        });
    }, 1000);
  }

  pollOutputs(timeout: number = 5000) {
    let api = this.api;
    if (!api.modelpk) {
      return;
    }
    setTimeout(() => {
      api.getRemoteOutputs().then(initRem => {
        this.setState({ remoteSim: initRem });
        if (initRem.status === "PENDING") {
          return this.pollOutputs(3000);
        } else {
          api.getOutputs().then(initSim => {
            this.setState({ sim: initSim, notifyOnCompletion: false });
          });
        }
      });
    }, timeout);
  }

  setOutputs() {
    let api = this.api;
    if (!api.modelpk) {
      return;
    }
    api
      .getRemoteOutputs()
      .then(remoteSim => {
        this.setState(prevState => ({
          remoteSim,
          isPublic: remoteSim.status === "SUCCESS" ? false : prevState.isPublic,
        }));
        if (remoteSim.status !== "STARTED" && remoteSim.status !== "PENDING") {
          api.getOutputs().then(sim => {
            this.setState({ sim, notifyOnCompletion: false });
          });
        }
        if (remoteSim.status === "PENDING") {
          return this.pollOutputs();
        }
      })
      // This may happen when a users access status changes after
      // removing their read access permission or removing themselves
      // from the author list. We just do a reload here.
      .catch((err: AxiosError) => {
        if (err.response.status == 403) {
          window.location.reload();
        }
      });
  }

  handleTabChange(key: "inputs" | "outputs", formikProps: FormikProps<InitialValues>) {
    // TODO: only includes draft `alert` action to demonstrate new
    // approach
    if (formikProps.dirty && key === "outputs" && !this.state.hasShownDirtyWarning) {
      // this.setState({ hasShownDirtyWarning: true });
      this.setState({ showDirtyWarning: true });
    } else {
      this.setState({ key });
    }
  }

  render() {
    if (this.state.error) throw this.state.error;
    // TODO be able to drop inputs from this if statement
    // currently causes error with formik.
    if (!this.state.accessStatus || (!this.state.remoteSim && this.api.modelpk)) {
      return <div></div>;
    } else if (
      this.state.accessStatus &&
      (this.state.remoteSim || !this.api.modelpk) &&
      !this.state.inputs
    ) {
      return (
        <ErrorBoundary>
          <DescriptionComponent
            api={this.api}
            accessStatus={this.state.accessStatus}
            remoteSim={this.state.remoteSim}
            resetOutputs={this.setOutputs}
            resetAccessStatus={async () => {
              const accessStatus = await this.api.getAccessStatus();
              this.setState({ accessStatus });
              return accessStatus;
            }}
            showCollabModal={this.state.showCollabModal}
          />
          <div className="d-flex justify-content-center">
            <ReactLoading type="spokes" color="#2b2c2d" />
          </div>
        </ErrorBoundary>
      );
    }
    let {
      accessStatus,
      inputs,

      remoteSim,

      schema,
      initialValues,
      unknownParams,
      extend,
      sects,
      showRunModal,
    } = this.state;

    let initialServerErrors = hasServerErrors(inputs?.detail?.errors_warnings)
      ? inputs.detail.errors_warnings
      : null;
    let initialStatus;
    if (initialServerErrors) {
      initialStatus = {
        serverErrors: initialServerErrors,
        status: "INVALID",
      };
    }
    return (
      <>
        <Formik
          initialValues={initialValues}
          validationSchema={yup.object().shape(schema)}
          validateOnChange={true}
          validateOnBlur={true}
          enableReinitialize={true}
          initialStatus={initialStatus}
          onSubmit={this.handleSubmit}
        >
          {(formikProps: FormikProps<InitialValues>) => (
            <>
              <AuthPortal>
                <AuthButtons
                  accessStatus={accessStatus}
                  resetAccessStatus={
                    this.api.modelpk ? this.resetAccessStatus : this.authenticateAndCreateSimulation
                  }
                  message="You must be logged in to run simulations."
                />
              </AuthPortal>
              {this.state.showDirtyWarning ? (
                <UnsavedChangesModal
                  handleClose={() =>
                    this.setState({ hasShownDirtyWarning: true, showDirtyWarning: false })
                  }
                />
              ) : null}
              <ErrorBoundary>
                <DescriptionComponent
                  api={this.api}
                  accessStatus={accessStatus}
                  remoteSim={remoteSim}
                  resetOutputs={this.setOutputs}
                  resetAccessStatus={async () => {
                    const accessStatus = await this.api.getAccessStatus();
                    this.setState({ accessStatus });
                    return accessStatus;
                  }}
                  showCollabModal={this.state.showCollabModal}
                />
              </ErrorBoundary>
              <Tab.Container
                id="sim-tabs"
                transition={false}
                defaultActiveKey={this.state.key}
                activeKey={this.state.key}
                onSelect={(k: "inputs" | "outputs") => this.handleTabChange(k, formikProps)}
              >
                <Nav variant="pills" className="mb-4">
                  <Col className="p-0">
                    <Nav.Item className="sim-nav-item left-nav-item">
                      <Nav.Link eventKey="inputs">Inputs</Nav.Link>
                    </Nav.Item>
                  </Col>
                  <Col className="p-0">
                    <Nav.Item className="sim-nav-item right-nav-item">
                      <Nav.Link eventKey="outputs">Outputs</Nav.Link>
                    </Nav.Item>
                  </Col>
                </Nav>
                <Tab.Content>
                  <Tab.Pane eventKey="inputs">
                    <ErrorBoundary>
                      <Form>
                        <InputsForm
                          api={this.api}
                          readOnly={false}
                          accessStatus={accessStatus}
                          sim={this.state.remoteSim}
                          resetAccessStatus={
                            this.api.modelpk
                              ? this.resetAccessStatus
                              : this.authenticateAndCreateSimulation
                          }
                          setNotifyOnCompletion={(notify: boolean) =>
                            this.setNotifyOnCompletion(notify, "inputs")
                          }
                          showRunModal={showRunModal}
                          notifyOnCompletion={this.state.notifyOnCompletion}
                          setIsPublic={this.setIsPublic}
                          isPublic={this.state.isPublic}
                          inputs={inputs}
                          defaultURL={`/${this.api.owner}/${this.api.title}/api/v1/`}
                          simStatus={remoteSim?.status || "STARTED"}
                          resetInitialValues={this.resetInitialValues}
                          resetting={this.state.resetting}
                          schema={schema}
                          unknownParams={unknownParams}
                          sects={sects}
                          extend={extend}
                          formikProps={formikProps}
                          persist={() =>
                            Persist.persist(
                              `${this.props.match.params.owner}/${this.props.match.params.title}/inputs`,
                              formikProps.values
                            )
                          }
                        />
                      </Form>
                    </ErrorBoundary>
                  </Tab.Pane>
                  <Tab.Pane eventKey="outputs">
                    <ErrorBoundary>
                      <OutputsComponent
                        api={this.api}
                        remoteSim={this.state.remoteSim}
                        sim={this.state.sim}
                        setNotifyOnCompletion={(notify: boolean) =>
                          this.setNotifyOnCompletion(notify, "outputs")
                        }
                      />
                    </ErrorBoundary>
                  </Tab.Pane>
                </Tab.Content>
              </Tab.Container>
            </>
          )}
        </Formik>
      </>
    );
  }
}

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route
        exact
        path="/:owner/:title/new/"
        render={routeProps => (
          <ErrorBoundary>
            <SimTabs tabName="inputs" {...routeProps} />
          </ErrorBoundary>
        )}
      />
      <Route
        exact
        path="/:owner/:title/:modelpk/edit/"
        render={routeProps => (
          <ErrorBoundary>
            <SimTabs tabName="inputs" {...routeProps} />
          </ErrorBoundary>
        )}
      />
      <Route
        exact
        path="/:owner/:title/:modelpk/"
        render={routeProps => (
          <ErrorBoundary>
            <SimTabs tabName="outputs" {...routeProps} />
          </ErrorBoundary>
        )}
      />
    </Switch>
  </BrowserRouter>,
  domContainer
);
