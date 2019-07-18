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
  ServerSizeField,
  Message,
  CheckboxField
} from "./fields";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const domContainer = document.querySelector("#publish-container");
const requiredMessage = "This field is required.";

var Schema = Yup.object().shape({
  title: Yup.string().required(requiredMessage),
  oneliner: Yup.string().required(requiredMessage),
  description: Yup.string().required(requiredMessage),
  repo_url: Yup.string().url(),
  // server_size: Yup.mixed().oneOf([[4, 2], [8, 4], [16, 8], [32, 16], [64, 32]]),
  exp_task_time: Yup.number().min(
    0,
    "Expected task time must be greater than ${min}."
  ),
  listed: Yup.boolean().required(requiredMessage)
});

const initialValues = {
  title: "",
  description: "",
  oneliner: "",
  repo_url: "",
  server_size: [4, 2],
  exp_task_time: 0,
  listed: true
};

const specialRequests = (
  <div>
    <p>
      You may contact the COMP admin at
      <a href="mailto:henrymdoupe@gmail.com"> henrymdoupe@gmail.com</a> to
      discuss:
    </p>
    <ul>
      <li>giving collaborators write-access to this app's publish details.</li>
      <li>special accomodations that need to be made for this model.</li>
      <li>any questions or feedback about the publish process.</li>
    </ul>
  </div>
);

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
              {status && status.project_exists ? (
                <div className="alert alert-danger" role="alert">
                  {status.project_exists}
                </div>
              ) : (
                  <div />
                )}
              {status && status.auth ? (
                <div className="alert alert-danger" role="alert">
                  {status.auth}
                </div>
              ) : (
                  <div />
                )}
              <div className="mt-5">
                <h3>About</h3>
                <hr className="my-3" />
                <div className="mt-1 mb-1">
                  <Field
                    type="text"
                    name="title"
                    component={TextField}
                    placeholder="Name of the app"
                    label="App Name"
                    preview={this.state.preview}
                    onChange={onChange}
                  />
                  <ErrorMessage
                    name="title"
                    render={msg => <Message msg={msg} />}
                  />
                </div>
                <div className="mt-1 mb-1">
                  <Field
                    type="text"
                    name="oneliner"
                    component={TextField}
                    placeholder="Short description of this app"
                    label="One-Liner"
                    preview={this.state.preview}
                    onChange={onChange}
                  />
                  <ErrorMessage
                    name="oneliner"
                    render={msg => <Message msg={msg} />}
                  />
                </div>
                <div className="mt-1 mb-1">
                  <Field
                    type="text"
                    name="description"
                    component={TextAreaField}
                    placeholder="Description of this app"
                    label="README"
                    preview={this.state.preview}
                    onChange={onChange}
                  />
                  <ErrorMessage
                    name="description"
                    render={msg => <Message msg={msg} />}
                  />
                </div>
                <div className="mt-1 mb-1">
                  <label>
                    <b>Repo URL:</b>
                  </label>
                  <p className="mt-1 mb-1">
                    <Field
                      className="form-control w-50rem"
                      type="url"
                      name="repo_url"
                      placeholder="Link to the model's code repository"
                    />
                    <ErrorMessage
                      name="repo_url"
                      render={msg => <Message msg={msg} />}
                    />
                  </p>
                </div>
                <div className="mt-3 mb-1">
                  <Field
                    component={CheckboxField}
                    label="Listed: "
                    description="Include this app in the public list of apps"
                    name="listed"
                    onChange={onChange}
                  />
                  <ErrorMessage
                    name="listed"
                    render={msg => <Message msg={msg} />}
                  />
                </div>
              </div>
              <div className="mt-5">
                <h3>Environment</h3>
                <hr className="my-3" />
                <div className="mt-1 mb-1">
                  <label>
                    <b>Expected job time:</b> Time in seconds for simulation to
                    complete
                  </label>
                  <p className="mt-1 mb-1">
                    <Field
                      className="form-control w-50rem"
                      type="number"
                      name="exp_task_time"
                    />
                    <ErrorMessage
                      name="exp_task_time"
                      render={msg => <Message msg={msg} />}
                    />
                  </p>
                </div>
                <div className="mt-1 mb-1">
                  <Field name="server_size" component={ServerSizeField} />
                  <ErrorMessage
                    name="server_size"
                    render={msg => <Message msg={msg} />}
                  />
                </div>
              </div>
              {specialRequests}
              <button
                className="btn inline-block"
                onClick={this.togglePreview}
                value
              >
                {this.state.preview ? "Edit" : "Preview"}
              </button>
              <div className="divider" />
              <button className="btn inline-block btn-success" type="submit">
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
    return axios.post("/publish/api/", data).then(function (response) {
      console.log("post", response);
      window.location.replace("/");
    });
  }
  render() {
    return (
      <div>
        <h1 style={{ marginBottom: "2rem" }}>Publish</h1>

        <p className="lead">
          Publish your model on COMP. Check out the
          <a href="https://docs.compmodels.org/publish/guide/">
            {" "}
            developer documentation
          </a>{" "}
          to learn more about the publishing criteria.
        </p>
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
      .then(function (response) {
        console.log(response);
        return response.data;
      })
      .catch(function (error) {
        console.log(error);
      });
  }

  doSubmit(data) {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    console.log(data);
    return axios
      .put(`/publish/api/${username}/${app_name}/detail/`, data)
      .then(function (response) {
        console.log(response);
        window.location.replace("/");
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
