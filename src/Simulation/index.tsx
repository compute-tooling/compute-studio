"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import { Nav, Tab, Col } from "react-bootstrap";
import axios from "axios";
import * as Sentry from "@sentry/browser";
import * as yup from "yup";
import ReactLoading from "react-loading";

import InputsForm, { tbLabelSchema } from "./InputsForm";
import OutputsComponent from "./Outputs";
import { AccessStatus, Inputs, InitialValues, Schema, Simulation, RemoteOutputs, Outputs, Sects, InputsDetail } from "../types";
import DescriptionComponent from "./Description";
import API from "./API";
import ErrorBoundary from "../ErrorBoundary";
import { convertToFormik, formikToJSON } from "../ParamTools";
import { Formik, Form, FormikProps, FormikActions } from "formik";
import { hasServerErrors } from "../utils";
import { UnsavedChangesModal } from "./modal";
import { AuthButtons } from "../auth";

Sentry.init({
  dsn: "https://fde6bcb39fda4af38471b16e2c1711af@sentry.io/1530834"
});

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const domContainer = document.querySelector("#inputs-container");
const authContainer = document.querySelector("#auth-group");

interface URLProps {
  match: {
    params: {
      owner: string;
      title: string;
      modelpk: string;
    };
  };
}

interface SimAppProps extends URLProps { }

interface SimAppState {
  // keep track of which tab is open
  key: "inputs" | "outputs";
  hasShownDirtyWarning: boolean;
  showDirtyWarning: boolean;

  // necessary for user id and write access
  accessStatus?: AccessStatus;

  // all meta data for the inputs of a sim.
  inputs?: Inputs;

  // all meta data for the outputs of a sim.
  remoteSim?: Simulation<RemoteOutputs>;
  sim?: Simulation<Outputs>;

  inputsTimer?: NodeJS.Timer | null;
  outputsTimer?: NodeJS.Timer | null;

  // necessary for form state
  initialValues?: InitialValues;
  schema?: { adjustment: yup.Schema<any>, meta_parameters: yup.Schema<any> }
  sects?: Sects;
  unknownParams?: Array<string>;
  extend?: boolean;
  resetting?: boolean;
}


class AuthPortal extends React.Component<{}> {
  el: HTMLDivElement

  constructor(props) {
    super(props);
    this.el = document.createElement("div");
  }

  componentDidMount() {
    while (authContainer.firstChild) {
      authContainer.removeChild(authContainer.firstChild);
    }
    authContainer.appendChild(this.el);
  }

  componentWillUnmount() {
    authContainer.removeChild(this.el);
  }

  render() {
    return ReactDOM.createPortal(
      this.props.children,
      this.el,
    )
  }
}


class SimTabs extends React.Component<
  SimAppProps & { tabName: "inputs" | "outputs" },
  SimAppState> {

  api: API
  constructor(props) {
    super(props);
    const { owner, title, modelpk } = this.props.match.params;
    this.api = new API(owner, title, modelpk)

    this.state = {
      key: props.tabName,
      hasShownDirtyWarning: false,
      showDirtyWarning: false,
    }

    this.handleTabChange = this.handleTabChange.bind(this);
    this.resetInitialValues = this.resetInitialValues.bind(this);
    this.resetAccessStatus = this.resetAccessStatus.bind(this);
    this.authenticateAndCreateSimulation = this.authenticateAndCreateSimulation.bind(this);
    this.pollInputs = this.pollInputs.bind(this);
    this.setOutputs = this.setOutputs.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
  }

  componentDidMount() {
    this.api.getAccessStatus().then(data => {
      this.setState({
        accessStatus: data
      })
    })
    this.api.getInitialValues().then(data => {
      const [
        initialValues,
        sects,
        inputs,
        schema,
        unknownParams
      ] = convertToFormik(data);
      this.setState({
        inputs: inputs,
        initialValues: initialValues,
        sects: sects,
        schema: schema,
        unknownParams: unknownParams,
        extend: "extend" in data ? data.extend : false,
      })
    })
    if (this.api.modelpk) {
      this.setOutputs()
    }
  }

  resetInitialValues(metaParameters: InputsDetail["meta_parameters"]) {
    this.setState({ resetting: true });
    this.api
      .resetInitialValues({
        meta_parameters: tbLabelSchema.cast(metaParameters)
      })
      .then(data => {
        const [
          initialValues,
          sects,
          { meta_parameters, model_parameters },
          schema,
          unknownParams
        ] = convertToFormik(data);
        this.setState((prevState) => ({
          inputs: {
            ...prevState.inputs,
            ...{
              meta_parameters: meta_parameters,
              model_parameters: model_parameters,
            }
          },
          initialValues: initialValues,
          sects: sects,
          schema: schema,
          unknownParams: unknownParams,
          resetting: false
        }));
      })
  }

  resetAccessStatus() {
    // Update authentication status, then the output
    // and inputs access statuses.
    this.api.getAccessStatus().then(accessStatus => {
      this.setState({ accessStatus });
    }).then(
      () => { this.setOutputs() }
    ).then(() => {
      this.api.getInputsDetail().then(inputsDetail => {
        this.setState((prevState) => ({
          inputs: {
            ...prevState.inputs,
            ...{ detail: inputsDetail }
          }
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
          this.setState((prevState) => ({
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

  handleSubmit(values, actions) {
    const [meta_parameters, adjustment] = formikToJSON(
      values,
      yup.object().shape(this.state.schema),
      tbLabelSchema,
      this.state.extend
    );

    let formdata = new FormData();
    formdata.append("adjustment", JSON.stringify(adjustment));
    formdata.append("meta_parameters", JSON.stringify(meta_parameters));
    formdata.append("client", "web-beta");
    let url = `/${this.api.owner}/${this.api.title}/api/v1/`;
    let sim = this.state.inputs.detail?.sim;
    // clicked new simulation button
    if (
      sim &&
      this.state.inputs.detail.has_write_access &&
      sim.status === "STARTED"
    ) {
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
          this.setState((prevState) => ({
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
            auth: "You must be logged in to create a simulation."
          });
        }
      });
  }

  pollInputs(respData: InputsDetail, actions: FormikActions<InitialValues>, values) {
    let timer = setInterval(() => {
      axios
        .get(respData.api_url)
        .then(response => {
          // be careful with race condidition where status is SUCCESS but
          // sim has not yet been submitted and saved!
          let data: InputsDetail = response.data;
          if (data.status === "SUCCESS" && data.sim !== null) {
            this.killTimer("inputsTimer");
            this.api.modelpk = data.sim.model_pk.toString();
            this.setOutputs();
            this.api.getAccessStatus().then(accessStatus => {
              this.setState((prevState) => ({
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
          } else if (response.data.status === "INVALID") {
            this.killTimer("inputsTimer");
            this.api.getAccessStatus().then(accessStatus => {
              this.setState((prevState) => ({
                inputs: { ...prevState.inputs, ...{ detail: data } },
                key: "inputs",
                accessStatus: accessStatus,
              }));
            });
            actions.setStatus({
              status: data.status,
              serverErrors: data.errors_warnings,
            });
            actions.setSubmitting(false);
            window.scroll(0, 0);
          }
        })
        .catch(error => {
          console.log("polling error:");
          console.log(error);
          this.killTimer("inputsTimer");
        });
    }, 1000);
    // @ts-ignore
    this.setState({ inputsTimer: timer });
  }

  setOutputs() {
    let timer;
    let api = this.api;
    if (!api.modelpk) {
      return;
    }
    api.getRemoteOutputs().then(initRem => {
      this.setState({ remoteSim: initRem });
      if (initRem.status !== "PENDING") {
        api.getOutputs().then(initSim => {
          this.setState({ sim: initSim });
        });
      } else {
        timer = setInterval(() => {
          api.getRemoteOutputs().then(detRem => {
            if (detRem.status !== "PENDING") {
              this.setState({ remoteSim: detRem })
              this.killTimer("outputsTimer");
              api.getOutputs().then(detSim => {
                this.setState({ sim: detSim })
              });
            } else {
              this.setState({ remoteSim: detRem })
            }
          })
        }, 5000);
      };
      this.setState({ outputsTimer: timer });
    });
  }

  killTimer(timerName: "inputsTimer" | "outputsTimer") {
    console.log("killTimer", timerName, this.state[timerName])
    if (this.state[timerName]) {
      clearInterval(this.state[timerName]);
      // @ts-ignore
      this.setState({ [timerName]: null });
    }
  }

  handleTabChange(key: "inputs" | "outputs", formikProps: FormikProps<InitialValues>) {
    // TODO: only includes draft `alert` action to demonstrate new
    // approach
    if (formikProps.dirty && key === "outputs" && !this.state.hasShownDirtyWarning) {
      // this.setState({ hasShownDirtyWarning: true });
      this.setState({ showDirtyWarning: true })
    } else {
      this.setState({ key })
    }
  }

  render() {
    // TODO be able to drop inputs from this if statement
    // currently causes error with formik.
    if (!this.state.accessStatus || (!this.state.remoteSim && this.api.modelpk)) {
      return <div></div>;
    } else if (this.state.accessStatus && (this.state.remoteSim || !this.api.modelpk) && !this.state.inputs) {
      return (<ErrorBoundary>
        <DescriptionComponent
          api={this.api}
          accessStatus={this.state.accessStatus}
          remoteSim={this.state.remoteSim}
        />
        <div className="d-flex justify-content-center">
          <ReactLoading type="spokes" color="#2b2c2d" />
        </div>
      </ErrorBoundary>);
    }
    const style = { padding: 0 };
    const buttonGroupStyle = {
      left: {
        borderTopRightRadius: 0,
        borderBottomRightRadius: 0
      },
      right: {
        borderTopLeftRadius: 0,
        borderBottomLeftRadius: 0
      }
    };
    let {
      accessStatus,
      inputs,

      remoteSim,

      schema,
      initialValues,
      unknownParams,
      extend,
      sects,
    } = this.state;
    let initialServerErrors = hasServerErrors(inputs?.detail?.errors_warnings) ?
      inputs.detail.errors_warnings : null;
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
          validateOnChange={false}
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
                />
              </AuthPortal>
              {this.state.showDirtyWarning ?
                <UnsavedChangesModal handleClose={() => this.setState({ hasShownDirtyWarning: true, showDirtyWarning: false })} />
                : null
              }
              <ErrorBoundary>
                <DescriptionComponent
                  api={this.api}
                  accessStatus={accessStatus}
                  remoteSim={remoteSim}
                />
              </ErrorBoundary>
              <Tab.Container
                id="sim-tabs"
                defaultActiveKey={this.state.key}
                activeKey={this.state.key}
                onSelect={(k: "inputs" | "outputs") => this.handleTabChange(k, formikProps)}
              >
                <Nav variant="pills" className="mb-4">
                  <Col style={style}>
                    <Nav.Item className="sim-nav-item">
                      <Nav.Link style={buttonGroupStyle.left} eventKey="inputs">
                        Inputs
                      </Nav.Link>
                    </Nav.Item>
                  </Col>
                  <Col style={style}>
                    <Nav.Item className="sim-nav-item">
                      <Nav.Link style={buttonGroupStyle.right} eventKey="outputs">
                        Outputs
                    </Nav.Link>
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
                          resetAccessStatus={
                            this.api.modelpk ? this.resetAccessStatus : this.authenticateAndCreateSimulation
                          }
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
  };
};

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route
        exact
        path="/:owner/:title/new/"
        render={routeProps => <SimTabs tabName="inputs" {...routeProps} />}
      />
      <Route
        exact
        path="/:owner/:title/:modelpk/edit/"
        render={routeProps => <SimTabs tabName="inputs" {...routeProps} />}
      />
      <Route
        exact
        path="/:owner/:title/:modelpk/"
        render={routeProps => <SimTabs tabName="outputs" {...routeProps} />}
      />
    </Switch>
  </BrowserRouter>,
  domContainer
);
