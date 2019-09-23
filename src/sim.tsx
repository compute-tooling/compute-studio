"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import axios from "axios";
import * as Sentry from "@sentry/browser";

import InputsForm from "./InputsForm";
// import ErrorBoundary from "./ErrorBoundary";
import { APIDetail, APIData } from "./types";

Sentry.init({
  dsn: "https://fde6bcb39fda4af38471b16e2c1711af@sentry.io/1530834"
});

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const domContainer = document.querySelector("#inputs-container");

interface InputsAppProps {
  match: {
    params: {
      username: string,
      app_name: string,
      inputs_hashid: string,
      model_pk: string,
    }
  },
  type: "inputs" | "edit_sim" | "edit_inputs";
}

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
                data = inputsResp.data,
                data["detail"] = detailResp.data;
                data["accessStatus"] = statusResp.data;
                return data;
              });
          })
        );
    } else {
      console.log(`type: ${this.props.type} is not allowed.`);
    }
  }

  resetInitialValues(metaParameters: {[metaParam: string]: any}) {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    return axios
      .post(`/${username}/${app_name}/api/v1/inputs/`, metaParameters)
      .then(function(response) {
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
      .then(function(response) {
        console.log(response);
        return response;
      });
  }

  render() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const id = `${username}/${app_name}`;
    console.log("let's render!")
    return (
      // <ErrorBoundary>
        <InputsForm
          fetchInitialValues={this.fetchInitialValues}
          resetInitialValues={this.resetInitialValues}
          doSubmit={this.doSubmit}
        />
      // </ErrorBoundary>
    );
  }
}

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route
        exact
        path="/:username/:app_name/"
        render={routeProps => <InputsApp type="inputs" {...routeProps} />}
      />
      <Route
        exact
        path="/:username/:app_name/:model_pk/edit/"
        render={routeProps => <InputsApp type="edit_sim" {...routeProps} />}
      />
      <Route
        exact
        path="/:username/:app_name/inputs/:inputs_hashid/"
        render={routeProps => <InputsApp type="edit_inputs" {...routeProps} />}
      />
    </Switch>
  </BrowserRouter>,
  domContainer
);
