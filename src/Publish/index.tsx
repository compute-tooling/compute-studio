"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import axios from "axios";
import { Formik, Field, Form, ErrorMessage, FormikHelpers } from "formik";
import * as yup from "yup";
import { Visualization, Project } from "../types";
import { TextField, TextAreaField, ServerSizeField, Message, CheckboxField } from "../fields";
import { Card } from "react-bootstrap";
import { captureException } from "@sentry/browser";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

interface Match {
  params: { username: string; app_name: string; vizTitle?: string };
}

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
  cpu: yup
    .number()
    .min(1, "CPU must be greater than ${min}.")
    .max(7, "CPU must be less than ${max}."),
  memory: yup
    .number()
    .min(2, "Memory must be greater than ${min}.")
    .max(24, "Memory must be less than ${max}."),
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
  repo_tag: string;
  cpu: number;
  memory: number;
  exp_task_time: number;
  listed: boolean;
  visualizations: Array<Visualization>;
}

const initialValues: PublishValues = {
  title: "",
  description: "",
  oneliner: "",
  repo_url: "",
  repo_tag: "master",
  cpu: 2,
  memory: 6,
  exp_task_time: 0,
  listed: true,
  visualizations: []
};

interface PublishProps<T> {
  preview: boolean;
  initialValues: T;
  project?: Project;
  submitType: "Publish" | "Update";
  doSubmit: (data: FormData) => Promise<void>;
}

type PublishState<T> = Readonly<{
  preview: boolean;
  initialValues: T;
  project?: Project;
}>;

class VisualizationApp extends React.Component<
  { preview: boolean; togglePreview: () => void; project: Project; viz?: Visualization },
  { initialValues: Visualization }
> {
  constructor(props) {
    super(props);
    this.state = {
      initialValues: this.props.viz || {
        title: "",
        oneliner: "",
        description: "",
        software: "",
        requires_server: true,
        function_name: ""
      }
    };
  }

  render() {
    const project = this.props.project;
    return (
      <div>
        <Formik
          initialValues={this.state.initialValues}
          onSubmit={async (values: Visualization, actions: FormikHelpers<Visualization>) => {
            var formdata = new FormData();
            for (const field in values) {
              formdata.append(field, values[field]);
            }
            try {
              const resp = await axios.post(
                `/publish/api/${project.owner}/${project.title}/viz/`,
                formdata
              );
              window.location.reload();
            } catch (e) {
              console.log(e);
            }
          }}
          // validateOnChange={true}
          // validationSchema={}
          render={({ status, handleSubmit }) => (
            <div>
              {status && status.project_exists ? (
                <div className="alert alert-danger" role="alert">
                  {status.project_exists}
                </div>
              ) : null}
              {status && status.auth ? (
                <div className="alert alert-danger" role="alert">
                  {status.auth}
                </div>
              ) : null}
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
                    preview={false}
                    exitPreview={() => this.props.togglePreview}
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
                    preview={false}
                    exitPreview={() => this.props.togglePreview}
                    style={inputStyle}
                  />
                  <ErrorMessage name="oneliner" render={msg => <Message msg={msg} />} />
                </div>
                <div className="mt-1 mb-1">
                  <label>
                    <b>README</b>
                  </label>
                  <Field
                    as="text"
                    name="description"
                    component={TextAreaField}
                    placeholder="Description of this app"
                    label="README"
                    preview={false}
                    exitPreview={() => this.props.togglePreview}
                    style={inputStyle}
                  />
                  <ErrorMessage name="description" render={msg => <Message msg={msg} />} />
                </div>
                <div className="mt-1 mb-1">
                  <label>
                    <b>Viz Software</b>
                  </label>
                  <Field className="form-control" as="select" name="software" style={inputStyle}>
                    <option value="bokeh">Bokeh</option>
                    <option value="dash">Dash</option>
                  </Field>
                  <ErrorMessage name="software" render={msg => <Message msg={msg} />} />
                </div>
                <div className="mt-1 mb-1">
                  <label>
                    <b>Function Name</b>
                  </label>
                  <Field name="function_name">
                    {({ field, form: { touched, errors }, meta }) => (
                      <div>
                        <input
                          type="text"
                          className="form-control"
                          {...field}
                          onChange={e => {
                            let val = e.target.value.replace(/[^a-zA-Z0-9]+/g, "-");
                            e.target.value = val;
                            field.onChange(e);
                          }}
                        />
                        {meta.touched && meta.error && <Message msg={meta.error} />}
                      </div>
                    )}
                  </Field>
                  <ErrorMessage name="software" render={msg => <Message msg={msg} />} />
                </div>
              </div>
              <button
                className="btn inline-block btn-success"
                onClick={e => {
                  e.preventDefault();
                  handleSubmit();
                }}
              >
                Publish
              </button>
            </div>
          )}
        />
      </div>
    );
  }
}

class PublishForm extends React.Component<
  PublishProps<PublishValues>,
  PublishState<PublishValues>
> {
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

  render() {
    const visualizations = this.props.project?.visualizations;
    return (
      <div>
        <Formik
          initialValues={this.state.initialValues}
          onSubmit={(values: PublishValues, actions: FormikHelpers<PublishValues>) => {
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
          validateOnChange={true}
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
                  <div className="mt-1 mb-1">
                    <label>
                      <b>Repo Tag:</b> Your project will be deployed from here
                    </label>
                    <p className="mt-1 mb-1">
                      <Field
                        className="form-control w-50rem"
                        type="text"
                        name="repo_tag"
                        placeholder="Link to the model's code repository"
                        style={inputStyle}
                      />
                      <ErrorMessage name="repo_tag" render={msg => <Message msg={msg} />} />
                    </p>
                  </div>
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
              </div>
              <div className="mt-5">
                <h4>Resource Requirements</h4>
                <div className="my-3" />
                <div className="mt-1 mb-1">
                  <label>CPUs required:</label>
                  <p className="mt-1 mb-1">
                    <Field
                      className="form-control w-50rem"
                      type="number"
                      step="0.1"
                      name="cpu"
                      style={inputStyle}
                    />
                    <ErrorMessage name="cpu" render={msg => <Message msg={msg} />} />
                  </p>
                </div>
                <div className="mt-1 mb-1">
                  <label>Memory (GB) required:</label>
                  <p className="mt-1 mb-1">
                    <Field
                      className="form-control w-50rem"
                      type="number"
                      step="0.1"
                      name="memory"
                      style={inputStyle}
                    />
                    <ErrorMessage name="memory" render={msg => <Message msg={msg} />} />
                  </p>
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
              {visualizations && visualizations.length && (
                <div className="mt-5">
                  <h3>My Interactive Visualizations</h3>
                  {visualizations.map(viz => (
                    <VisualizationApp
                      preview={this.state.preview}
                      togglePreview={() => {
                        this.setState({ preview: false });
                      }}
                      project={this.props.project}
                      viz={viz}
                    />
                  ))}
                </div>
              )}
              <div className="mt-5">
                <h3>Create New Interactive Visualization</h3>
                <VisualizationApp
                  preview={this.state.preview}
                  togglePreview={() => {
                    this.setState({ preview: false });
                  }}
                  project={this.props.project}
                />
              </div>
            </Form>
          )}
        />
      </div>
    );
  }
}

class VisualizationDetailApp extends React.Component<
  { match: Match },
  { project?: Project; viz?: Visualization; preview: boolean }
> {
  constructor(props) {
    super(props);
    this.state = { preview: true };
  }

  async fetchInitialValues() {
    const { username, app_name, vizTitle } = this.props.match.params;
    const vizResp = await axios.get(`/publish/api/${username}/${app_name}/viz/${vizTitle}/`);
    const projectResp = await axios.get(`/publish/api/${username}/${app_name}/detail/`);
    let vizData: Visualization = vizResp.data;
    let projectData: Project = projectResp.data;
    this.setState({
      project: projectData,
      viz: vizData
    });
  }

  render() {
    if (!this.state.project || !this.state.viz) {
      return <p>loading ....</p>;
    }
    const { username, app_name, vizTitle } = this.props.match.params;
    return (
      <Card className="card-outer">
        <Card.Body>
          <h2 style={{ marginBottom: "2rem" }}>
            <a className="primary-text" href={`/${username}/${app_name}/viz/${vizTitle}/`}>
              {`/${username}/${app_name}/viz/${vizTitle}/`}
            </a>
          </h2>
          <VisualizationApp
            viz={this.state.viz}
            project={this.state.project}
            preview={true}
            togglePreview={() => this.setState({ preview: !this.state.project })}
          />
        </Card.Body>
      </Card>
    );
  }
}

class CreateApp extends React.Component<{ doSubmit: PublishProps<PublishValues>["doSubmit"] }, {}> {
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

class AppDetail extends React.Component<{ match: Match }, { project?: Project }> {
  constructor(props) {
    super(props);
    this.state = {};
    this.doSubmit = this.doSubmit.bind(this);
  }

  async componentDidMount() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const resp = await axios.get(`/publish/api/${username}/${app_name}/detail/`);
    let data: Project = resp.data;
    this.setState({ project: data });
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
    if (!this.state.project) {
      return <p>getting project...</p>;
    }
    return (
      <Card className="card-outer">
        <Card.Body>
          <h2 style={{ marginBottom: "2rem" }}>
            <a className="primary-text" href={`/${id}/`}>
              {id}
            </a>
          </h2>
          <PublishForm
            project={this.state.project}
            initialValues={(this.state.project as unknown) as PublishValues}
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
      <Route path="/:username/:app_name/viz/:vizTitle/detail/" component={VisualizationDetailApp} />
    </Switch>
  </BrowserRouter>,
  domContainer
);
