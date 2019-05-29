"use strict";

import ReactDOM from "react-dom";
import React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import axios from "axios";
import { Formik, Field, Form, ErrorMessage } from "formik";
import * as Yup from "yup";
import {
  TextField,
  TextAreaField,
  CodeSnippetField,
  ServerSizeField,
  Message
} from "./fields";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const domContainer = document.querySelector("#inputs-container");
const requiredMessage = "This field is required.";

var Schema = Yup.object().shape({
});

const initialValues = {
};


class InputsForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      initialValues: this.props.initialValues
    };
  }

  componentDidMount() {
    if (this.props.fetchInitialValues) {
      this.props.fetchInitialValues().then(data => {
        this.setState({ initialValues: data });
      });
    }
  }

  render() {
    if (!this.state.initialValues) {
      return <p> loading.... </p>;
    }
    return (
      <div>
        <Formik
          initialValues={this.state.initialValues}
          onSubmit={(values, actions) => {
            console.log(values, actions);
            var formdata = new FormData();
            for (var field in values) {
              formdata.append([field], values[field]);
            }
            this.props
              .doSubmit(formdata)
              .then(response => {
                actions.setSubmitting(false);
              })
              .catch(error => {
                console.log("error", error);
                console.log(error.response.data);
                actions.setSubmitting(false);
                if (error.response.status == 400) {
                  actions.setStatus(error.response.data);
                } else if (error.response.status == 401) {
                  actions.setStatus({
                    auth: "You must be logged in to publish a model."
                  });
                }
              });
          }}
          validationSchema={Schema}
          render={({ onChange, status, errors }) => (
            <Form>
              <div class="row">
                <div class="col-4">
                  <ul class="list-unstyled components sticky-top scroll-y">
                    <li>
                      <div class="card card-body card-outer">
                        <p>Hello world!</p>
                        <button type="submit" name="reset" value="true" class="btn btn-block btn-outline-dark">Reset</button>
                      </div>
                    </li>
                    <li>
                      <div class="card card-body card-outer">
                        <button type="submit" class="btn btn-block btn-success">
                          <b>Run</b>
                        </button>
                      </div>
                    </li>
                  </ul>
                </div>
                <div class="col-8">
                  <div class="card card-body card-outer">
                    <p>hello</p>
                    <pre>
                      <code>
                        {JSON.stringify(this.state.initialValues, null, 4)}
                      </code>
                    </pre>
                  </div>
                </div>
              </div>
            </Form>
          )}
        />
      </div>
    );
  }
}


class InputsApp extends React.Component {
  constructor(props) {
    super(props);
    this.doSubmit = this.doSubmit.bind(this);
    this.fetchInitialValues = this.fetchInitialValues.bind(this);
  }

  fetchInitialValues() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    return axios
      .get(`/${username}/${app_name}/api/v1/inputs/`)
      .then(function(response) {
        console.log(response);
        return response.data;
      })
      .catch(function(error) {
        console.log(error);
      });
  }

  doSubmit(data) {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    return axios
      .put(`/${username}/${app_name}/api/v1/`, data)
      .then(function(response) {
        console.log(response);
        window.location.replace("/");
      });
  }

  render() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const id = `${username}/${app_name}`;
    return (
        <InputsForm
          fetchInitialValues={this.fetchInitialValues}
          initialValues={null}
          submitType="Create"
          doSubmit={this.doSubmit}
        />
    );
  }
}

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route exact path="/:username/:app_name/" component={InputsApp} />
    </Switch>
  </BrowserRouter>,
  domContainer
);
