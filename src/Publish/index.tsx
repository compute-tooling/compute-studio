"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import * as ReactMarkdown from "react-markdown";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import { Row, Col, Card, Dropdown, Jumbotron } from "react-bootstrap";
import axios from "axios";
import { Formik, Field, Form, ErrorMessage, FormikHelpers, FormikProps } from "formik";
import * as yup from "yup";
import { Project, AccessStatus, Tech } from "../types";
import { CheckboxField } from "../fields";
import API from "./API";
import { Tip } from "../components";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const techLinks = {
  "python-paramtools": "https://paramtools.dev",
  bokeh: "https://bokeh.org",
  dash: "https://dash.plotly.com/"
};

const techDocsLinks = {
  "python-paramtools": "https://docs.compute.studio/publish/guide/",
  bokeh: "https://bokeh.org",
  dash: "https://dash.plotly.com/"
};

const techTitles = {
  dash: "Dash",
  bokeh: "Bokeh",
  "python-paramtools": "ParamTools"
};

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
  listed: yup.boolean().required(requiredMessage),
  tech: yup.string(),
  callable_name: yup.string()
});

export const Message = ({ msg }) => (
  <p className={`form-text font-weight-bold`} style={{ color: "#dc3545", fontSize: "80%" }}>
    {msg}
  </p>
);

const SpecialRequests: React.FC<{}> = () => (
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

interface ProjectValues {
  title: string;
  description: string | null;
  oneliner: string;
  repo_url: string;
  repo_tag: string;
  cpu: number;
  memory: number;
  exp_task_time: number;
  listed: boolean;
  tech: Tech;
  callable_name: string;
}

const initialValues: ProjectValues = {
  title: "",
  description: "",
  oneliner: "",
  repo_url: "",
  repo_tag: "master",
  cpu: 2,
  memory: 6,
  exp_task_time: 0,
  listed: true,
  tech: "python-paramtools",
  callable_name: ""
};

interface PublishProps {
  preview: boolean;
  initialValues: ProjectValues;
  project?: Project;
  accessStatus: AccessStatus;
  api: API;
}

type PublishState = Readonly<{
  preview: boolean;
  initialValues: ProjectValues;
}>;

const TechSelect: React.FC<{
  selectedTech: Tech | null;
  onSelectTech: (tech: Tech) => void;
}> = ({ selectedTech, onSelectTech }) => {
  const techChoices: Array<Tech> = ["python-paramtools", "bokeh", "dash"];
  return (
    <Dropdown>
      <Dropdown.Toggle
        variant="primary"
        id="dropdown-basic"
        className="w-50"
        style={{ backgroundColor: "white", color: "#007bff" }}
      >
        <strong>{selectedTech || "Select"}</strong>
      </Dropdown.Toggle>
      <Dropdown.Menu>
        {techChoices.map((tech, ix) => (
          <Dropdown.Item
            key={ix}
            href="#"
            className={`w-100 ${selectedTech === tech && "bg-primary"}`}
            onClick={() => onSelectTech(tech)}
          >
            <strong>{tech}</strong>
          </Dropdown.Item>
        ))}
      </Dropdown.Menu>
    </Dropdown>
  );
};

const PythonParamTools: React.FC<{}> = ({ }) => {
  return (
    <div className="mt-5">
      <h4>ParamTools Configuration</h4>
      <div className="my-3" />
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
  );
};

const VizWithServer: React.FC<{ tech: Tech }> = ({ tech }) => {
  const title = {
    dash: "Dash",
    bokeh: "Bokeh"
  }[tech];
  return (
    <div className="mt-5">
      <h4>{title} Configuration</h4>
      <div className="my-3" />
      <div className="mt-1 mb-1">
        <label>
          <b>Function Name</b>
        </label>
        <Field name="callable_name">
          {({ field, meta }) => (
            <div>
              {console.log(field)}
              <input
                type="text"
                className="form-control"
                {...field}
                onChange={e => {
                  let val = e.target.value.replace(/[^a-zA-Z0-9]+/g, "_");
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
  );
};

const CommonFields: React.FC<any> = ({ }) => {
  return (
    <div className="mt-5">
      <h4>Environment</h4>
      <div className="my-3" />
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
    </div>
  );
};

const ViewProject: React.FC<{
  project: Project;
  accessStatus: AccessStatus;
  enterEditMode: () => void;
}> = ({ project, accessStatus, enterEditMode }) => {
  const id = `${project.owner}/${project.title}`;
  const goto = project.tech === "python-paramtools" ? `/${id}/new/` : `/${id}/viz/`;
  const image = node => (
    <div className="container-fluid">
      <img className="h-100 w-100" src={node.src} alt={node.alt} style={{ objectFit: "cover" }} />
    </div>
  );
  const isMobile = window.innerWidth < 992;
  let title;
  if (isMobile) {
    title = (
      <>
        <p className="font-weight-light primary-text mb-0">
          <a href={`/${project.owner}/`}>{project.owner}</a> /
        </p>
        <a href={`/${id}/`} className="primary-text">
          <p className="lead font-weight-bold">{project.title}</p>
        </a>
      </>
    );
  } else {
    title = (
      <>
        <h1 className="display-5">
          <a href={`/${project.owner}/`} className="primary-text">
            <span className="font-weight-light">{project.owner}</span>
          </a>
          <span className="font-weight-light mx-1">/</span>
          <a href={`/${id}/`} className="primary-text">
            <span className="font-weight-bold">{project.title}</span>
          </a>
        </h1>
      </>
    );
  }
  return (
    <Jumbotron className="shadow" style={{ backgroundColor: "white" }}>
      <Row className="justify-content-between mb-2">
        <Col className="col-auto align-self-center">{title}</Col>
        {accessStatus.can_write_project && (
          <Col className="col-auto align-self-center">
            <button className="btn btn-outline-primary" onClick={() => enterEditMode()}>
              Edit
            </button>
          </Col>
        )}
      </Row>
      <p className="lead">{project.oneliner}</p>
      <hr className="my-4" />
      <ReactMarkdown source={project.description} escapeHtml={false} renderers={{ image: image }} />
      <Row className="justify-content-between mt-5">
        <Col className="col-auto align-self-center">
          {project.status === "live" && (
            <a className="btn btn-success" href={goto}>
              <strong>Go to App</strong>
            </a>
          )}
        </Col>
        <Col className="col-auto align-self-center">
          <p>
            Built with{" "}
            <a href={techLinks[project.tech]}>
              <strong>{techTitles[project.tech]}</strong>
            </a>
            .
          </p>
        </Col>
      </Row>
    </Jumbotron>
  );
};

class ProjectApp extends React.Component<PublishProps, PublishState & { showTechOpts: boolean }> {
  constructor(props) {
    super(props);
    let initialValues = {};
    for (const [key, value] of Object.entries(this.props.initialValues)) {
      initialValues[key] = value === null ? "" : value;
    }
    this.state = {
      preview: this.props.preview,
      initialValues: initialValues as ProjectValues,
      showTechOpts: false
    };
    this.togglePreview = this.togglePreview.bind(this);
  }

  togglePreview() {
    event.preventDefault();
    this.setState({ preview: !this.state.preview });
  }

  render() {
    const { accessStatus } = this.props;
    return (
      <div>
        <Formik
          initialValues={this.state.initialValues}
          onSubmit={(values: ProjectValues, actions: FormikHelpers<ProjectValues>) => {
            var formdata = new FormData();
            for (const field in values) {
              formdata.append(field, values[field]);
            }
            this.props.api
              .save(formdata)
              .then(project => {
                actions.setSubmitting(false);
                window.location.href = `/${project.owner}/${project.title}/`;
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
        >
          {(props: FormikProps<ProjectValues>) => (
            <Form>
              {props.status && props.status.project_exists ? (
                <div className="alert alert-danger" role="alert">
                  {props.status.project_exists}
                </div>
              ) : (
                  <div />
                )}
              {(props.status && props.status.auth) || !accessStatus.username ? (
                <div className="alert alert-danger" role="alert">
                  You must be logged in to publish a model.
                </div>
              ) : (
                  <div />
                )}
              <div>
                <div className="mt-1 mb-1">
                  <Field name="title">
                    {({ field, meta }) => (
                      <Row className="justify-content-md-center">
                        <Col className="flex-grow-0 align-self-center">
                          <h6 className="lead">{accessStatus.username}</h6>
                        </Col>
                        <Col className="flex-grow-0 align-self-center">
                          <p className="lead pt-2">/</p>
                        </Col>
                        <Col className="flex-grow-0 align-self-center">
                          <input
                            type="text"
                            {...field}
                            onChange={e => {
                              e.target.value = e.target.value.replace(/[^a-zA-Z0-9]+/g, "-");
                              field.onChange(e);
                            }}
                          />
                          {meta.touched && meta.error && (
                            <div className="text-danger">{meta.error}</div>
                          )}
                        </Col>
                      </Row>
                    )}
                  </Field>
                </div>
                <div className="mt-1 mb-1">
                  <label className="strong">Oneliner</label>
                  <Field name="oneliner">
                    {({ field, meta }) => (
                      <Row className="w-100">
                        <Col>
                          <input type="text" className="w-100" {...field} />
                          {meta.touched && meta.error && (
                            <div className="text-danger">{meta.error}</div>
                          )}
                        </Col>
                      </Row>
                    )}
                  </Field>
                </div>
                <div className="mt-1 mb-1">
                  <label className="strong">
                    README{" "}
                    <Tip id="readme-markdown-icon" tip="Supports Markdown." placement="top">
                      <i className="fab fa-markdown mr-3" style={{ opacity: 0.8 }}></i>
                    </Tip>
                  </label>
                  <Field name="description">
                    {({ field, meta }) => (
                      <Row className="w-100">
                        <Col>
                          <textarea type="text" className="w-100" rows="10" {...field} />
                          {meta.touched && meta.error && (
                            <div className="text-danger">{meta.error}</div>
                          )}
                        </Col>
                      </Row>
                    )}
                  </Field>
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
                <div className="mt-5 mb-1">
                  <label>
                    <b>Tech</b>
                  </label>
                  <Field name="tech">
                    {({ field, meta }) => (
                      <TechSelect
                        selectedTech={
                          (props.values.tech && props.touched.tech) || this.props.api.title
                            ? props.values.tech
                            : null
                        }
                        onSelectTech={sel => {
                          props.setFieldValue("tech", sel);
                          props.setFieldTouched("tech", true);
                        }}
                      />
                    )}
                  </Field>
                </div>
                {((props.values.tech && props.touched.tech) || this.props.api.title) && (
                  <>
                    {props.values.tech === "python-paramtools" && <PythonParamTools />}
                    {["bokeh", "dash"].includes(props.values.tech) && (
                      <VizWithServer tech={props.values.tech} />
                    )}
                    <CommonFields />
                  </>
                )}
              </div>
              <SpecialRequests />
              <button className="btn inline-block" onClick={this.togglePreview}>
                {this.state.preview ? "Edit" : "Preview"}
              </button>
              <div className="divider" />
              <button className="btn inline-block btn-success" type="submit">
                {this.props.api?.owner ? "Save" : "Create"}
              </button>
            </Form>
          )}
        </Formik>
      </div>
    );
  }
}

class CreateProject extends React.Component<{}, { accessStatus?: AccessStatus }> {
  api: API;
  constructor(props) {
    super(props);
    this.state = {};

    this.api = new API(null, null);
  }
  async componentDidMount() {
    const accessStatus = await this.api.getAccessStatus();
    this.setState({
      accessStatus
    });
  }
  render() {
    if (!this.state.accessStatus) {
      return <div />;
    }
    return (
      <Card className="card-outer">
        <Card.Body>
          <ProjectApp
            initialValues={initialValues}
            preview={false}
            accessStatus={this.state.accessStatus}
            api={this.api}
          />
        </Card.Body>
      </Card>
    );
  }
}

class ProjectDetail extends React.Component<
  { match: Match },
  { project?: Project; accessStatus?: AccessStatus; edit: boolean }
  > {
  api: API;
  constructor(props) {
    super(props);
    this.state = { edit: false };
    const owner = this.props.match.params.username;
    const title = this.props.match.params.app_name;
    this.api = new API(owner, title);
  }

  async componentDidMount() {
    const project = await this.api.getProject();
    const accessStatus = await this.api.getAccessStatus();
    this.setState({ accessStatus, project });
  }

  render() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const id = `${username}/${app_name}`;
    if (!this.state.project || !this.state.accessStatus) {
      return <div />;
    }
    return this.state.edit ? (
      <Card className="card-outer">
        <Card.Body>
          <h2 style={{ marginBottom: "2rem" }}>
            <a className="primary-text" href={`/${id}/`}>
              {id}
            </a>
          </h2>
          <ProjectApp
            project={this.state.project}
            accessStatus={this.state.accessStatus}
            initialValues={(this.state.project as unknown) as ProjectValues}
            preview={true}
            api={this.api}
          />
        </Card.Body>
      </Card>
    ) : (
        <ViewProject
          project={this.state.project}
          accessStatus={this.state.accessStatus}
          enterEditMode={() => this.setState({ edit: true })}
        />
      );
  }
}

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route exact path="/publish/" component={CreateProject} />
      <Route exact path="/new/" component={CreateProject} />
      <Route path="/:username/:app_name/" component={ProjectDetail} />
    </Switch>
  </BrowserRouter>,
  domContainer
);
