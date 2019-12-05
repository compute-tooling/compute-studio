"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import { Nav, Tab, Col, Card } from "react-bootstrap";
import axios from "axios";
import * as Sentry from "@sentry/browser";

import InputsForm from "./InputsForm";
import OutputsComponent from "./Outputs";
import { AccessStatus } from "./types";
import DescriptionComponent from "./Description";
import API from "./API";
import ErrorBoundary from "./ErrorBoundary";

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


class SimTabs extends React.Component<
  SimAppProps & { tabName: "inputs" | "outputs" },
  { key: "inputs" | "outputs", accessStatus: AccessStatus }> {

  api: API
  constructor(props) {
    super(props);
    const { owner, title, modelpk } = this.props.match.params;
    this.api = new API(owner, title, modelpk)

    this.state = {
      key: props.tabName,
      accessStatus: null,
    }
  }

  componentDidMount() {
    const { owner, title } = this.api;
    return axios.get(`/users/status/${owner}/${title}/`).then(resp => {
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
        <ErrorBoundary>
          <DescriptionComponent
            api={this.api}
            accessStatus={this.state.accessStatus}
          />
        </ErrorBoundary>
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
              <ErrorBoundary>
                <InputsForm
                  api={this.api}
                  readOnly={false}
                  accessStatus={this.state.accessStatus}
                  defaultURL={`/${this.api.owner}/${this.api.title}/api/v1/`}
                />
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
