"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import axios from "axios";
import { Formik, Field, Form, ErrorMessage, FormikActions } from "formik";
import * as yup from "yup";
import { TextField, TextAreaField, ServerSizeField, Message, CheckboxField } from "../fields";
import { Card } from "react-bootstrap";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const inputStyle = {
  width: "100%"
};

const domContainer = document.querySelector("#publish-container");
const requiredMessage = "This field is required.";

var Schema = yup.object().shape({
  title: yup.string().required(requiredMessage),
  oneliner: yup.string().required(requiredMessage),
  description: yup.string().required(requiredMessage),
  repo_url: yup.string().url(),
  // server_size: yup.mixed().oneOf([[4, 2], [8, 4], [16, 8], [32, 16], [64, 32]]),
  exp_task_time: yup.number().min(0, "Expected task time must be greater than ${min}."),
  listed: yup.boolean().required(requiredMessage)
});

const specialRequests = (
  <div>
    <p>
      You may contact the Compute Studio admin at
      <a href="mailto:hank@compute.studio"> hank@compute.studio</a> to discuss:
    </p>
    <ul>
      <li>giving collaborators write-access to this app's publish details.</li>
      <li>special accomodations that need to be made for this model.</li>
      <li>any questions or feedback about the publish process.</li>
    </ul>
  </div>
);

interface PublishValues {
  title: string;
  description: string;
  oneliner: string;
  repo_url: string;
  server_size: [number, number];
  exp_task_time: number;
  listed: boolean;
}

const initialValues: PublishValues = {
  title: "",
  description: "",
  oneliner: "",
  repo_url: "",
  server_size: [4, 2],
  exp_task_time: 0,
  listed: true
};

interface PublishProps {
  preview: boolean;
  initialValues: PublishValues;
  submitType: "Publish" | "Update";
  fetchInitialValues: () => Promise<any>;
  doSubmit: (data: FormData) => Promise<void>;
}

type PublishState = Readonly<{
  preview: boolean;
  initialValues: PublishValues;
}>;

class PublishForm extends React.Component<PublishProps, PublishState> {
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
          onSubmit={(values: PublishValues, actions: FormikActions<PublishValues>) => {
            var formdata = new FormData();
            for (const field in values) {
              formdata.append(field, values[field]);
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
                window.scroll(0, 0);
              });
          }}
          validationSchema={Schema}
          render={({ status }) => (
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
                  <label>
                    <b>Title</b>
                  </label>
                  <Field
                    type="text"
                    name="title"
                    component={TextField}
                    placeholder="Name of the app"
                    label="App Name"
                    preview={this.state.preview}
                    exitPreview={() => this.setState({ preview: false })}
                    allowSpecialChars={false}
                    style={inputStyle}
                  />
                  <ErrorMessage name="title" render={msg => <Message msg={msg} />} />
                </div>
                <div className="mt-1 mb-1">
                  <label>
                    <b>Oneliner</b>
                  </label>
                  <Field
                    type="text"
                    name="oneliner"
                    component={TextField}
                    placeholder="Short description of this app"
                    label="One-Liner"
                    preview={this.state.preview}
                    exitPreview={() => this.setState({ preview: false })}
                    style={inputStyle}
                  />
                  <ErrorMessage name="oneliner" render={msg => <Message msg={msg} />} />
                </div>
                <div className="mt-1 mb-1">
                  <label>
                    <b>README</b>
                  </label>
                  <Field
                    type="text"
                    name="description"
                    component={TextAreaField}
                    placeholder="Description of this app"
                    label="README"
                    preview={this.state.preview}
                    exitPreview={() => this.setState({ preview: false })}
                    style={inputStyle}
                  />
                  <ErrorMessage name="description" render={msg => <Message msg={msg} />} />
                </div>
                <div className="mt-1 mb-1">
                  <label>
                    <b>Repo URL</b>
                  </label>
                  <p className="mt-1 mb-1">
                    <Field
                      className="form-control w-50rem"
                      type="url"
                      name="repo_url"
                      placeholder="Link to the model's code repository"
                      style={inputStyle}
                    />
                    <ErrorMessage name="repo_url" render={msg => <Message msg={msg} />} />
                  </p>
                </div>
                <div className="mt-3 mb-1">
                  <label>
                    <b>Listed:</b>Include this app in the public list of apps
                  </label>

                  <Field
                    component={CheckboxField}
                    label="Listed: "
                    description="Include this app in the public list of apps"
                    name="listed"
                  />
                  <ErrorMessage name="listed" render={msg => <Message msg={msg} />} />
                </div>
              </div>
              <div className="mt-5">
                <h3>Environment</h3>
                <hr className="my-3" />
                <div className="mt-1 mb-1">
                  <label>
                    <b>Expected job time:</b> Time in seconds for simulation to complete
                  </label>
                  <p className="mt-1 mb-1">
                    <Field
                      className="form-control w-50rem"
                      type="number"
                      name="exp_task_time"
                      style={inputStyle}
                    />
                    <ErrorMessage name="exp_task_time" render={msg => <Message msg={msg} />} />
                  </p>
                </div>
                <div className="mt-1 mb-1">
                  <Field name="server_size" component={ServerSizeField} />
                  <ErrorMessage name="server_size" render={msg => <Message msg={msg} />} />
                </div>
              </div>
              {specialRequests}
              <button className="btn inline-block" onClick={this.togglePreview}>
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

class CreateApp extends React.Component<{ doSubmit: PublishProps["doSubmit"] }, {}> {
  constructor(props) {
    super(props);
    this.doSubmit = this.doSubmit.bind(this);
  }
  doSubmit(data) {
    return axios.post("/publish/api/", data).then(function(response) {
      console.log("post", response);
      let data: { title: string; owner: string };
      data = response.data;
      window.location.href = `/${data.owner}/${data.title}/detail/`;
    });
  }
  render() {
    return (
      <Card className="card-outer">
        <Card.Body>
          <h1 style={{ marginBottom: "2rem" }}>Publish</h1>

          <p className="lead">
            Publish your model on Compute Studio. Check out the
            <a href="https://docs.compute.studio/publish/guide/"> developer documentation</a> to
            learn more about the publishing criteria.
          </p>
          <PublishForm
            fetchInitialValues={null}
            initialValues={initialValues}
            preview={false}
            submitType="Publish"
            doSubmit={this.doSubmit}
          />
        </Card.Body>
      </Card>
    );
  }
}

interface Match {
  params: { username: string; app_name: string };
}
class AppDetail extends React.Component<{ match: Match }, {}> {
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
        let data: PublishValues = response.data;
        return data;
      })
      .catch(function(error) {
        console.log(error);
      });
  }

  doSubmit(data: FormData) {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    console.log(data);
    return axios.put(`/publish/api/${username}/${app_name}/detail/`, data).then(function(response) {
      console.log(response);
      window.location.href = `/${username}/${app_name}/detail/`;
    });
  }

  render() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const id = `${username}/${app_name}`;
    return (
      <Card className="card-outer">
        <Card.Body>
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
        </Card.Body>
      </Card>
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
