"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import { Nav, Tabs, Tab, Row, Col, Card } from "react-bootstrap";
import axios from "axios";
import * as Sentry from "@sentry/browser";

import InputsForm from "./InputsForm";
import OutputsComponent from "./Outputs";
import ErrorBoundary from "./ErrorBoundary";
import { InputsAPIData, RemoteOutputs, Outputs, SimAPIData, AccessStatus } from "./types";
import DescriptionComponent from "./Description";

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
  type: "new" | "edit_sim" | "edit_inputs";
  readOnly: boolean;
  accessStatus: AccessStatus;
}

interface SimAppProps extends URLProps { }
interface DescriptionProps extends URLProps { accessStatus: AccessStatus }

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
    let data: InputsAPIData;
    console.log("router", username, app_name, this.props.type);
    if (this.props.type === "new") {
      console.log("fresh page");
      return axios.get(`/${username}/${app_name}/api/v1/inputs/`)
        .then(inputsResp => {
          console.log("inputsResp", inputsResp);
          data = inputsResp.data;
          return data;
        });
    } else if (this.props.type === "edit_sim") {
      let model_pk = this.props.match.params.model_pk;
      console.log("edit sim");
      return axios.get(`/${username}/${app_name}/api/v1/${model_pk}/edit/`).then(detailResp => {
        console.log("detailResp", detailResp);
        return axios
          .post(`/${username}/${app_name}/api/v1/inputs/`, {
            meta_parameters: detailResp.data.meta_parameters
          })
          .then(inputsResp => {
            console.log("inputsResp", inputsResp);
            data = inputsResp.data;
            data["detail"] = detailResp.data;
            return data;
          });
      });
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
        let data: InputsAPIData = response.data;
        return data;
      });
  }

  doSubmit(url: string, data: FormData) {
    return axios
      .post(url, data)
      .then(function (response) {
        console.log(response);
        return response;
      });
  }

  render() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const id = `${username}/${app_name}`;
    return (
      <ErrorBoundary>
        <InputsForm
          fetchInitialValues={this.fetchInitialValues}
          resetInitialValues={this.resetInitialValues}
          doSubmit={this.doSubmit}
          readOnly={this.props.readOnly}
          accessStatus={this.props.accessStatus}
          defaultURL={`/${username}/${app_name}/api/v1/`}
        />
      </ErrorBoundary>
    );
  }
}

class OutputsApp extends React.Component<SimAppProps, { isNew: Boolean }> {
  constructor(props) {
    super(props);
    this.fetchRemoteOutputs = this.fetchRemoteOutputs.bind(this);
    this.fetchOutputs = this.fetchOutputs.bind(this);
    this.state = {
      isNew: this.props.match.params.model_pk ? false : true
    }
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
        isNew={this.state.isNew}
        fetchRemoteOutputs={this.fetchRemoteOutputs}
        fetchOutputs={this.fetchOutputs}
      />
    );
  }
}

class DescriptionApp extends React.Component<DescriptionProps, { isNew: Boolean }> {
  constructor(props) {
    super(props);
    this.fetchRemoteOutputs = this.fetchRemoteOutputs.bind(this);
    this.putDescription = this.putDescription.bind(this);
    this.state = {
      isNew: this.props.match.params.model_pk ? false : true
    }
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

  putDescription(data: FormData): Promise<SimAPIData<RemoteOutputs>> {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const model_pk = this.props.match.params.model_pk;
    console.log("put", data);
    return axios.put(
      `/${username}/${app_name}/api/v1/${model_pk}/`,
      data
    ).then(resp => {
      let data: SimAPIData<RemoteOutputs> = resp.data;
      return data;
    })
  }

  render() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const modelPk = this.props.match.params.model_pk;
    return (
      <DescriptionComponent
        isNew={this.state.isNew}
        accessStatus={this.props.accessStatus}
        fetchRemoteOutputs={this.fetchRemoteOutputs}
        putDescription={this.putDescription}
        username={username}
        appname={app_name}
        modelPk={parseInt(modelPk)}
      />
    );
  }
}

class SimTabs extends React.Component<
  SimAppProps & { tabName: "inputs" | "outputs", type: "new" | "edit_inputs" | "edit_sim" },
  { key: "inputs" | "outputs", accessStatus: AccessStatus }> {
  constructor(props) {
    super(props);
    this.state = {
      key: props.tabName,
      accessStatus: null,
    }
  }

  componentDidMount() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;

    return axios.get(`/users/status/${username}/${app_name}/`).then(resp => {
      this.setState({
        accessStatus: resp.data
      })
      return resp.data
    })
  }

  render() {
    if (!this.state.accessStatus) {
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
    return (
      <>
        <DescriptionApp match={this.props.match} accessStatus={this.state.accessStatus} />
        <Tab.Container
          id="sim-tabs"
          defaultActiveKey={this.state.key}
          onSelect={(k: "inputs" | "outputs") => this.setState({ key: k })}
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
              <InputsApp readOnly={false} match={this.props.match} type={this.props.type} accessStatus={this.state.accessStatus} />
            </Tab.Pane>
            <Tab.Pane eventKey="outputs">
              <OutputsApp match={this.props.match} />
            </Tab.Pane>
          </Tab.Content>
        </Tab.Container>
      </>
    );
  };
};

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route
        exact
        path="/:username/:app_name/new/"
        render={routeProps => <SimTabs tabName="inputs" type="new" {...routeProps} />}
      />
      <Route
        exact
        path="/:username/:app_name/inputs/:inputs_hashid/"
        render={routeProps => <SimTabs tabName="outputs" type="edit_inputs" {...routeProps} />}
      />
      <Route
        exact
        path="/:username/:app_name/:model_pk/edit/"
        render={routeProps => <SimTabs tabName="inputs" type="edit_sim" {...routeProps} />}
      />
      <Route
        exact
        path="/:username/:app_name/:model_pk/"
        render={routeProps => <SimTabs tabName="outputs" type="edit_sim" {...routeProps} />}
      />
    </Switch>
  </BrowserRouter>,
  domContainer
);
