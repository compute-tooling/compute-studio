"use strict";

import ReactDOM from "react-dom";
import React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import axios from "axios";
import { Formik, Field, Form, ErrorMessage } from "formik";
import * as Yup from "yup";
import {
  TextField,
  DescriptionField,
  CodeSnippetField,
  ServerSizeField,
  Message
} from "./fields";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const domContainer = document.querySelector("#publish-container");
const requiredMessage = "This field is required.";

function isJsonString(str) {
  try {
    JSON.parse(str);
  } catch (e) {
    return false;
  }
  return true;
}

var Schema = Yup.object().shape({
  title: Yup.string().required(),
  description: Yup.string()
    .max(1000, "The description must be less than ${max} characters.")
    .required(),
  inputs_style: Yup.string().oneOf(
    ["paramtools", "taxcalc"],
    "Inputs type must be either paramtools or taxcalc."
  ),
  meta_parameters: Yup.string()
    .required(requiredMessage)
    .test("valid-json", "Meta parameters is not valid JSON.", value =>
      isJsonString(value)
    ),
  package_defaults: Yup.string().required(requiredMessage),
  parse_user_adjustments: Yup.string().required(requiredMessage),
  run_simulation: Yup.string().required(requiredMessage),
  installation: Yup.string().required(requiredMessage),
  // server_size: Yup.mixed().oneOf([[4, 2], [8, 4], [16, 8], [32, 16], [64, 32]]),
  exp_task_time: Yup.number().min(
    0,
    "Expected task time must be greater than ${min}."
  )
});

const initialValues = {
  title: "",
  description: "",
  inputs_style: "paramtools",
  meta_parameters: "",
  package_defaults: "",
  parse_user_adjustments: "",
  run_simulation: "",
  installation: "",
  server_size: [4, 2],
  exp_task_time: 0
};

class PublishForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      preview: this.props.preview,
      initialValues: this.props.initialValues
    };
    this.togglePreview = this.togglePreview.bind(this);
  }

  togglePreview() {
    event.preventDefault();
    this.setState({ preview: !this.state.preview });
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
            this.props.doSubmit(formdata).then(
              response => {
                actions.setSubmitting(false);
              },
              error => {
                actions.setSubmitting(false);
                actions.setStatus({ msg: "Set some arbitrary status or data" });
              }
            );
          }}
          validationSchema={Schema}
          render={({ onChange }) => (
            <Form>
              <h3>About</h3>
              <hr className="my-4" />
              <div>
                <Field
                  type="text"
                  name="title"
                  component={TextField}
                  placeholder="What's the name of this app?"
                  label="App Name"
                  preview={this.state.preview}
                  onChange={onChange}
                />
                <ErrorMessage
                  name="title"
                  render={msg => <Message msg={msg} />}
                />
              </div>
              <div>
                <Field
                  type="text"
                  name="description"
                  component={DescriptionField}
                  placeholder="What does this app do? Must be less than 1000 characters."
                  preview={this.state.preview}
                />
                <ErrorMessage
                  name="description"
                  render={msg => <Message msg={msg} />}
                />
              </div>
              <h3>Model Parameters</h3>
              <hr className="my-4" />
              <p>
                <em>
                  Insert code snippets satisfying the requirements detailed in
                  the{" "}
                  <a href="https://github.com/comp-org/comp/blob/master/docs/IOSCHEMA.md">
                    inputs documentation.
                  </a>
                </em>
              </p>
              <div>
                <label>
                  <b>Inputs style:</b> Select the style of inputs that your app
                  will use
                </label>
                <p>
                  <Field component="select" name="inputs_style">
                    <option value="paramtools">ParamTools style</option>
                    <option value="taxcalc">Tax-Calculator style</option>
                  </Field>
                </p>
                <ErrorMessage
                  name="inputs_style"
                  render={msg => <Message msg={msg} />}
                />
              </div>
              <div>
                <Field
                  type="text"
                  name="meta_parameters"
                  component={CodeSnippetField}
                  label="Meta parameters"
                  description="Controls the default Model Parameters"
                  language="json"
                  placeholder="# json snippet here"
                  preview={this.state.preview}
                />
                <ErrorMessage
                  name="meta_parameters"
                  render={msg => <Message msg={msg} />}
                />
              </div>
              <h3>Python Functions</h3>
              <hr className="my-4" />
              <p>
                <em>
                  Insert code snippets satisfying the requirements detailed in
                  the{" "}
                  <a href="https://github.com/comp-org/comp/blob/master/docs/ENDPOINTS.md">
                    functions documentation.
                  </a>
                </em>
              </p>
              <div>
                <Field
                  type="text"
                  name="package_defaults"
                  component={CodeSnippetField}
                  label="Get package defaults"
                  description="Get the default Model Parameters and their meta data"
                  language="python"
                  placeholder="# code snippet here"
                  preview={this.state.preview}
                />
                <ErrorMessage
                  name="package_defaults"
                  render={msg => <Message msg={msg} />}
                />
              </div>
              <div>
                <Field
                  type="text"
                  name="parse_user_adjustments"
                  component={CodeSnippetField}
                  label="Parse user adjustments"
                  description="Do model-specific formatting and validation on the user adjustments"
                  language="python"
                  placeholder="# code snippet here"
                  preview={this.state.preview}
                />
                <ErrorMessage
                  name="parse_user_inputs"
                  render={msg => <Message msg={msg} />}
                />
              </div>
              <div>
                <Field
                  type="text"
                  name="run_simulation"
                  component={CodeSnippetField}
                  label="Run simulation"
                  description="Submit the user adjustments (or none) to the model to run the simulations"
                  language="python"
                  placeholder="# code snippet here"
                  preview={this.state.preview}
                />
                <ErrorMessage
                  name="run_simulation"
                  render={msg => <Message msg={msg} />}
                />
              </div>
              <h3>Environment</h3>
              <hr className="my-4" />
              <p>
                <em>
                  Describe how to install this project and its resource
                  requirements as detailed in{" "}
                  <a href="https://github.com/comp-org/comp/blob/master/docs/ENVIRONMENT.md">
                    the environment documentation.
                  </a>
                </em>
              </p>
              <div>
                <Field
                  type="text"
                  name="installation"
                  component={CodeSnippetField}
                  label="Installation"
                  description="Bash commands for installing this project"
                  language="bash"
                  placeholder="# code snippet here"
                  preview={this.state.preview}
                />
                <ErrorMessage
                  name="installation"
                  render={msg => <Message msg={msg} />}
                />
              </div>
              <div>
                <label>
                  <b>Expected job time:</b> Time in seconds for simulation to
                  complete
                </label>
                <p>
                  <Field
                    className="form-control"
                    type="number"
                    name="exp_task_time"
                  />
                  <ErrorMessage
                    name="exp_task_time"
                    render={msg => <Message msg={msg} />}
                  />
                </p>
              </div>
              <div>
                <Field name="server_size" component={ServerSizeField} />
                <ErrorMessage
                  name="server_size"
                  render={msg => <Message msg={msg} />}
                />
              </div>
              <button
                className="btn inline-block"
                onClick={this.togglePreview}
                value
              >
                {this.state.preview ? "Edit" : "Preview"}
              </button>
              <div className="divider" />
              <button className="btn inline-block go-btn" type="submit">
                {this.props.submitType}
              </button>
            </Form>
          )}
        />
      </div>
    );
  }
}

class CreateApp extends React.Component {
  constructor(props) {
    super(props);
    this.doSubmit = this.doSubmit.bind(this);
  }
  doSubmit(data) {
    axios
      .post("/publish/api/", data)
      .then(function(response) {
        console.log("post", response);
        // need to handle errors from the server here!
        window.location.replace("/");
      })
      .catch(function(error) {
        console.log(error);
        if (error.response.status == 401) {
          alert("You must be logged in to publish a model.");
        } else {
          alert("An error has occurred.");
        }
      });
  }
  render() {
    return (
      <div>
        <h1 style={{ marginBottom: "2rem" }}>Publish a new app</h1>
        <PublishForm
          fetchInitialValues={null}
          initialValues={initialValues}
          preview={false}
          submitType="Publish"
          doSubmit={this.doSubmit}
        />
      </div>
    );
  }
}

class AppDetail extends React.Component {
  constructor(props) {
    super(props);
    this.doSubmit = this.doSubmit.bind(this);
    this.fetchInitialValues = this.fetchInitialValues.bind(this);
  }

  fetchInitialValues() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    return axios
      .get(`/publish/api/${username}/${app_name}/detail/`)
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
    axios
      .put(`/publish/api/${username}/${app_name}/detail/`, data)
      .then(function(response) {
        console.log(response);
        window.location.replace(`/${username}/`);
      })
      .catch(function(error) {
        console.log(error);
        if (error.response.status == 401) {
          alert(
            `You must be logged in and the author in order to update ${app_name}.`
          );
        } else {
          alert("An error has occurred.");
        }
      });
  }

  render() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const id = `${username}/${app_name}`;
    return (
      <div>
        <h2 style={{ marginBottom: "2rem" }}>
          <a className="primary-text" href={`/${id}/`}>
            {id}
          </a>
        </h2>
        <PublishForm
          fetchInitialValues={this.fetchInitialValues}
          initialValues={null}
          preview={true}
          submitType="Update"
          doSubmit={this.doSubmit}
        />
      </div>
    );
  }
}

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route exact path="/publish/" component={CreateApp} />
      <Route path="/:username/:app_name/detail/" component={AppDetail} />
    </Switch>
  </BrowserRouter>,
  domContainer
);
