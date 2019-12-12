"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import { Nav, Tab, Col, Card } from "react-bootstrap";
import axios from "axios";
import * as Sentry from "@sentry/browser";
import * as yup from "yup";

import InputsForm, { tbLabelSchema } from "./InputsForm";
import OutputsComponent from "./Outputs";
import { AccessStatus, Inputs, InitialValues, Schema, Simulation, RemoteOutputs, Outputs, Sects, InputsDetail } from "./types";
import DescriptionComponent from "./Description";
import API from "./API";
import ErrorBoundary from "./ErrorBoundary";
import { convertToFormik, formikToJSON } from "./ParamTools";
import { Formik, Form, FormikProps } from "formik";
import { hasServerErrors } from "./utils";

Sentry.init({
  dsn: "https://fde6bcb39fda4af38471b16e2c1711af@sentry.io/1530834"
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

interface SimAppProps extends URLProps { }

interface SimAppState {
  // keep track of which tab is open
  key: "inputs" | "outputs";
  hasShownDirtyWarning: boolean;

  // necessary for user id and write access
  accessStatus?: AccessStatus;

  // all meta data for the inputs of a sim.
  inputs?: Inputs;

  timer?: NodeJS.Timer;

  // necessary for form state
  initialValues?: InitialValues;
  schema?: { adjustment: yup.Schema<any>, meta_parameters: yup.Schema<any> }
  sects?: Sects;
  unknownParams?: Array<string>;
  extend?: boolean;
  resetting?: boolean;
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
    }

    this.handleTabChange = this.handleTabChange.bind(this);
    this.resetInitialValues = this.resetInitialValues.bind(this);
    this.poll = this.poll.bind(this);
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
    // if (!this.api.modelpk) {
    //   this.api.getRemoteOutputs().then(data => {
    //     this.setState({
    //       remoteSim: data
    //     })
    //   })
    // }

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
        this.setState({
          inputs: {
            ...this.state.inputs,
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
        });
      })
  }

  handleSubmit(values, actions) {
    const [meta_parameters, adjustment] = formikToJSON(
      values,
      yup.object().shape(this.state.schema),
      tbLabelSchema,
      this.state.extend
    );
    console.log("submitting");
    console.log(adjustment);
    console.log(meta_parameters);

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
        console.log("success", data.gui_url);
        if (data.sim.owner !== sim?.owner) {
          window.location.href = data.gui_url;
        } else {
          history.pushState(null, null, data.gui_url);
          actions.setStatus({
            status: "PENDING",
            api_url: data.api_url,
            editInputsUrl: data.gui_url,
            inputsDetail: data // TODO: necessary
          });
          // set submitting as false in poll func.
          if (data.status === "PENDING") {
            this.poll(
              data,
              (data: InputsDetail) => {
                actions.setStatus({
                  status: data.status,
                  simUrl: data.sim.gui_url,
                  key: "outputs",
                });
                actions.setSubmitting(false);
              },
              (data: InputsDetail) => {
                actions.setSubmitting(false);
                actions.setStatus({
                  status: data.status,
                  serverErrors: data.errors_warnings,
                  editInputsUrl: data.gui_url,
                  key: "inputs",
                });
              }
            );
          }
        }
      })
      .catch(error => {
        console.log("error", error);
        actions.setSubmitting(false);
        if (error.response.status == 403) {
          actions.setStatus({
            auth: "You must be logged in to publish a model."
          });
        }
      });
  }

  poll(
    respData: InputsDetail,
    onSuccess: (data: InputsDetail) => void,
    onInvalid: (data: InputsDetail) => void
  ) {
    let timer = setInterval(() => {
      axios
        .get(respData.api_url)
        .then(response => {
          // be careful with race condidition where status is SUCCESS but
          // sim has not yet been submitted and saved!
          let data: InputsDetail = response.data;
          if (data.status === "SUCCESS" && data.sim !== null) {
            this.killTimer();
            onSuccess(data);
            history.pushState(null, null, data.sim.gui_url);
          } else if (response.data.status === "INVALID") {
            this.killTimer();
            onInvalid(data);
            window.scroll(0, 0);
          }
        })
        .catch(error => {
          console.log("polling error:");
          console.log(error);
          this.killTimer();
          // actions.setSubmitting(false); TODO
          // request likely cancelled because timer was killed.
          // if (error.message && error.message != "Request aborted") {
          //   this.setState({ error: error });
          // }
        });
    }, 1000);
    // @ts-ignore
    this.setState({ timer: timer });
  }

  killTimer() {
    if (!!this.state.timer) {
      clearInterval(this.state.timer);
      this.setState({ timer: null });
    }
  }

  handleTabChange(key: "inputs" | "outputs", formikProps: FormikProps<InitialValues>) {
    // TODO: only includes draft `alert` action to demonstrate new
    // approach
    if (formikProps.dirty && key === "outputs" && !this.state.hasShownDirtyWarning) {
      this.setState({ hasShownDirtyWarning: true });
      alert("you have unsaved inputs in the form.");
    } else {
      this.setState({ key })
    }
  }

  render() {
    if (!(this.state.accessStatus && this.state.inputs)) {
      return <Card className="card-outer">Loading....</Card>
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

      schema,
      initialValues,
      unknownParams,
      extend,
      sects,
    } = this.state;
    let initialServerErrors = hasServerErrors(inputs.detail?.errors_warnings) ?
      inputs.detail.errors_warnings : null;
    let initialStatus;
    if (initialServerErrors) {
      initialStatus = {
        serverErrors: initialServerErrors,
        status: "INVALID",
        editInputsUrl: inputs.detail.api_url
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
              <ErrorBoundary>
                <DescriptionComponent
                  api={this.api}
                  accessStatus={accessStatus}
                />
              </ErrorBoundary>
              <Tab.Container
                id="sim-tabs"
                defaultActiveKey={this.state.key}
                activeKey={formikProps.status?.key ? formikProps.status.key : this.state.key}
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
                          inputs={inputs}
                          defaultURL={`/${this.api.owner}/${this.api.title}/api/v1/`}

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
