"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import { Nav, Tabs, Tab, Row, Col } from "react-bootstrap";
import axios from "axios";
import * as Sentry from "@sentry/browser";

import InputsForm from "./InputsForm";
import OutputsComponent from "./Outputs";
import ErrorBoundary from "./ErrorBoundary";
import { APIData, RemoteOutputs, Outputs, SimAPIData } from "./types";

Sentry.init({
  dsn: "https://fde6bcb39fda4af38471b16e2c1711af@sentry.io/1530834"
});

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const domContainer = document.querySelector("#inputs-container");

interface URLProps {
  match: {
    params: {
      username: string;
      app_name: string;
      inputs_hashid: string;
      model_pk: string;
    };
  };
}

interface InputsAppProps extends URLProps {
  type: "inputs" | "edit_sim" | "edit_inputs";
  readOnly: boolean;
}

interface SimAppProps extends URLProps { }

class InputsApp extends React.Component<InputsAppProps, {}> {
  constructor(props) {
    super(props);
    this.doSubmit = this.doSubmit.bind(this);
    this.fetchInitialValues = this.fetchInitialValues.bind(this);
    this.resetInitialValues = this.resetInitialValues.bind(this);
  }

  fetchInitialValues() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    let data: APIData;
    console.log("router", username, app_name, this.props.type);
    if (this.props.type === "inputs") {
      console.log("fresh page");
      return axios
        .all([
          axios.get(`/${username}/${app_name}/api/v1/inputs/`),
          axios.get(`/users/status/${username}/${app_name}/`)
        ])
        .then(
          axios.spread((inputsResp, statusResp) => {
            console.log("inputsResp", inputsResp);
            console.log("statusResp", statusResp);
            data = inputsResp.data;
            data["accessStatus"] = statusResp.data;
            return data;
          })
        );
    } else if (this.props.type === "edit_sim") {
      let model_pk = this.props.match.params.model_pk;
      console.log("edit sim");
      return axios
        .all([
          axios.get(`/${username}/${app_name}/api/v1/${model_pk}/edit/`),
          axios.get(`/users/status/${username}/${app_name}/`)
        ])
        .then(
          axios.spread((detailResp, statusResp) => {
            console.log("detailResp", detailResp);
            console.log("statusResp", statusResp);
            return axios
              .post(`/${username}/${app_name}/api/v1/inputs/`, {
                meta_parameters: detailResp.data.meta_parameters
              })
              .then(inputsResp => {
                console.log("inputsResp", inputsResp);
                data = inputsResp.data;
                data["detail"] = detailResp.data;
                data["accessStatus"] = statusResp.data;
                return data;
              });
          })
        );
    } else if (this.props.type === "edit_inputs") {
      let inputs_hashid = this.props.match.params.inputs_hashid;
      console.log("edit inputs");
      return axios
        .all([
          axios.get(`/${username}/${app_name}/api/v1/inputs/${inputs_hashid}/`),
          axios.get(`/users/status/${username}/${app_name}/`)
        ])
        .then(
          axios.spread((detailResp, statusResp) => {
            console.log("detailResp", detailResp);
            console.log("statusResp", statusResp);
            return axios
              .post(`/${username}/${app_name}/api/v1/inputs/`, {
                meta_parameters: detailResp.data.meta_parameters
              })
              .then(inputsResp => {
                console.log("inputsResp", inputsResp);
                (data = inputsResp.data), (data["detail"] = detailResp.data);
                data["accessStatus"] = statusResp.data;
                return data;
              });
          })
        );
    } else {
      console.log(`type: ${this.props.type} is not allowed.`);
    }
  }

  resetInitialValues(metaParameters: { [metaParam: string]: any }) {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    return axios
      .post(`/${username}/${app_name}/api/v1/inputs/`, metaParameters)
      .then(function (response) {
        console.log(response);
        let data: APIData = response.data;
        return data;
      });
  }

  doSubmit(data: FormData) {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    console.log("posting...");
    console.log(data);
    return axios
      .post(`/${username}/${app_name}/api/v1/`, data)
      .then(function (response) {
        console.log(response);
        return response;
      });
  }

  render() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const id = `${username}/${app_name}`;
    console.log("let's render!");
    return (
      <ErrorBoundary>
        <InputsForm
          fetchInitialValues={this.fetchInitialValues}
          resetInitialValues={this.resetInitialValues}
          doSubmit={this.doSubmit}
          readOnly={this.props.readOnly}
        />
      </ErrorBoundary>
    );
  }
}

class OutputsApp extends React.Component<SimAppProps, {}> {
  constructor(props) {
    super(props);
    this.fetchRemoteOutputs = this.fetchRemoteOutputs.bind(this);
    this.fetchOutputs = this.fetchOutputs.bind(this);
  }

  fetchRemoteOutputs(): Promise<SimAPIData<RemoteOutputs>> {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const model_pk = this.props.match.params.model_pk;
    return axios
      .get(`/${username}/${app_name}/api/v1/${model_pk}/remote/`)
      .then(resp => {
        let data: SimAPIData<RemoteOutputs> = resp.data;
        return data;
      });
  }

  fetchOutputs(): Promise<SimAPIData<Outputs>> {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    let model_pk = this.props.match.params.model_pk;
    return axios
      .get(`/${username}/${app_name}/api/v1/${model_pk}/`)
      .then(resp => {
        let data: SimAPIData<Outputs> = resp.data;
        return data;
      });
  }

  render() {
    return (
      <OutputsComponent
        fetchRemoteOutputs={this.fetchRemoteOutputs}
        fetchOutputs={this.fetchOutputs}
      />
    );
  }
}

const SimTabs: React.FC<
  SimAppProps & { type: "inputs" | "outputs" }
> = props => {
  const [key, setKey] = React.useState(props.type);

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
  return (
    <Tab.Container
      id="sim-tabs"
      defaultActiveKey={key}
      onSelect={(k: "inputs" | "outputs") => setKey(k)}
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
          <InputsApp readOnly={true} match={props.match} type="edit_sim" />
        </Tab.Pane>
        <Tab.Pane eventKey="outputs">
          <OutputsApp match={props.match} />
        </Tab.Pane>
      </Tab.Content>
    </Tab.Container>
  );
};

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route
        exact
        path="/:username/:app_name/"
        render={routeProps => <InputsApp readOnly={false} type="inputs" {...routeProps} />}
      />
      <Route
        exact
        path="/:username/:app_name/inputs/:inputs_hashid/"
        render={routeProps => <InputsApp readOnly={false} type="edit_inputs" {...routeProps} />}
      />
      <Route
        exact
        path="/:username/:app_name/:model_pk/edit/"
        render={routeProps => <InputsApp readOnly={false} type="edit_sim" {...routeProps} />}
      />
      <Route
        exact
        path="/:username/:app_name/:model_pk/"
        render={routeProps => <SimTabs type="outputs" {...routeProps} />}
      />
      <Route
        exact
        path="/:username/:app_name/:model_pk/inputs/"
        render={routeProps => <SimTabs type="inputs" {...routeProps} />}
      />
    </Switch>
  </BrowserRouter>,
  domContainer
);
