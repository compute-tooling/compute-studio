"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import * as ReactMarkdown from "react-markdown";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import { Row, Col, Card, Dropdown, Jumbotron, Button, ListGroup } from "react-bootstrap";
import axios from "axios";
import { Formik, Field, Form, ErrorMessage, FormikHelpers, FormikProps } from "formik";
import * as yup from "yup";
import { Project, AccessStatus, Tech, ResourceLimitException } from "../types";
import { CheckboxField } from "../fields";
import API from "./API";
import { Tip } from "../components";
import { AuthPortal, AuthButtons, AuthDialog } from "../auth";
axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const newTechEmail =
  "mailto:hank@compute.studio?subject=Requesting%20New%20App%20Technology&body=I%20am%20interested%20in%20publishing%20an%20app%20using:";

const techLinks = {
  "python-paramtools": "https://paramtools.dev",
  bokeh: "https://bokeh.org",
  dash: "https://dash.plotly.com/",
};

const techDocsLinks = {
  "python-paramtools": "https://docs.compute.studio/publish/guide/",
  bokeh: "https://bokeh.org",
  dash: "https://dash.plotly.com/",
};

const techGuideLinks = {
  bokeh: "https://docs.compute.studio/publish/data-viz/guide.html#bokeh",
  dash: "https://docs.compute.studio/publish/data-viz/guide.html#dash",
  "python-paramtools": "https://docs.compute.studio/publish/model/guide.html",
};

const techTitles = {
  dash: "Dash",
  bokeh: "Bokeh",
  "python-paramtools": "ParamTools",
};

interface Match {
  params: { username: string; app_name: string; vizTitle?: string };
}

const inputStyle = {
  width: "100%",
};

const domContainer = document.querySelector("#publish-container");
const requiredMessage = "This field is required.";

var Schema = yup.object().shape({
  title: yup.string().required(requiredMessage),
  oneliner: yup.string(),
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
  tech: yup.string().required(requiredMessage),
  callable_name: yup.string(),
  is_public: yup.boolean(),
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
  tech: Tech | null;
  callable_name: string;
  is_public: boolean;
}

const initialValues: ProjectValues = {
  title: "",
  description: "",
  oneliner: "",
  repo_url: "",
  repo_tag: "master",
  cpu: 1,
  memory: 2,
  exp_task_time: 0,
  listed: true,
  tech: null,
  callable_name: "",
  is_public: true,
};

type ProjectSettingsSection = "about" | "configure" | "environment" | "access";

interface PublishProps {
  initialValues: ProjectValues;
  project?: Project;
  accessStatus: AccessStatus;
  resetAccessStatus: () => void;
  api: API;
  edit?: boolean;
  section?: ProjectSettingsSection;
}

type PublishState = Readonly<{
  initialValues: ProjectValues;
}>;

const PrivateAppException: React.FC<{ upgradeTo: "pro" }> = ({ upgradeTo }) => {
  let plan;
  if (upgradeTo === "pro") {
    plan = "Compute Studio Pro";
  }
  return (
    <div className="alert alert-primary alert-dismissible fade show" role="alert">
      You must upgrade to{" "}
      <a href="/billing/upgrade/">
        <strong>{plan}</strong>
      </a>{" "}
      to make this app private.
      <Row className="w-100 justify-content-center">
        <Col className="col-auto">
          <Button
            variant="primary"
            style={{ fontWeight: 600 }}
            className="w-100 mt-3"
            href="/billing/upgrade/"
          >
            Upgrade to {plan}
          </Button>
        </Col>
      </Row>
      <button type="button" className="close" data-dismiss="alert" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>
  );
};

const TechSelectDropdown: React.FC<{
  selectedTech: Tech | null;
  onSelectTech: (tech: Tech) => void;
}> = ({ selectedTech, onSelectTech }) => {
  const techChoices: Array<Tech> = ["python-paramtools", "bokeh", "dash"];
  return (
    <Dropdown>
      <Dropdown.Toggle variant="outline-primary" id="dropdown-basic" className="w-100">
        {selectedTech ? (
          <span>
            Tech: <strong className="px-3">{selectedTech}</strong>
          </span>
        ) : (
          <strong>Specify technology</strong>
        )}
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
        <Dropdown.Item key="another" href={newTechEmail} className="w-100">
          <strong>Request Another</strong>
        </Dropdown.Item>
      </Dropdown.Menu>
    </Dropdown>
  );
};

const TechSelect: React.FC<{ project: Project; props: FormikProps<ProjectValues> }> = ({
  project,
  props,
}) => (
  <Row className="w-100 justify-content-left">
    <Col className="col-auto">
      <Field name="tech">
        {({ field, meta }) => (
          <TechSelectDropdown
            selectedTech={props.values.tech || !!project ? props.values.tech : null}
            onSelectTech={sel => {
              TechSelect;
              props.setFieldValue("tech", sel);
            }}
          />
        )}
      </Field>
      <ErrorMessage name="tech" render={msg => <Message msg={msg} />} />
    </Col>
  </Row>
);

const PythonParamTools: React.FC<{}> = ({}) => {
  return (
    <div>
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
    bokeh: "Bokeh",
  }[tech];
  return (
    <div>
      <div className="my-3" />
      {tech === "dash" && (
        <div className="mt-1 mb-1">
          <label>
            <b>Function Name</b>
          </label>
          <Field name="callable_name">
            {({ field, meta }) => (
              <div>
                <input
                  type="text"
                  className="form-control w-50"
                  {...field}
                  placeholder={`Name of the ${title} server.`}
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
          <ErrorMessage name="callable_name" render={msg => <Message msg={msg} />} />
        </div>
      )}
      <div className="mt-1 mb-1">
        <label>
          <b>App Location</b>
        </label>
        <div>
          <Field
            required={tech === "bokeh"}
            name="app_location"
            placeholder="Directory or file containing app."
            className="w-50"
          />
          <ErrorMessage name="app_location" render={msg => <Message msg={msg} />} />
        </div>
      </div>
    </div>
  );
};

const SourceCodeFields: React.FC<{}> = ({}) => (
  <div>
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
);

const AdvancedFields: React.FC<{}> = ({}) => {
  return (
    <div>
      <details className="my-2">
        <summary>
          <span className="h6">Advanced Configuration</span>
        </summary>
        <div className="mt-1">
          <p className="lead">Resource Requirements</p>
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
        <SpecialRequests />
      </details>
    </div>
  );
};

const PublicPrivateRadio: React.FC<{ props: FormikProps<ProjectValues>; project?: Project }> = ({
  props,
  project,
}) => (
  <>
    <p>
      <label>
        <input
          id="make-public"
          name="is_public"
          type="radio"
          checked={props.values.is_public}
          onChange={() => props.setFieldValue("is_public", true)}
        />
        <span className="ml-1">
          <strong>Public:</strong> Anyone on the internet can see and use this app.{" "}
          {project?.status !== "running" &&
            "You will be given an option later to make it discoverable."}
        </span>
      </label>
    </p>
    <p>
      <label>
        <input
          id="make-private"
          name="is_public"
          type="radio"
          checked={!props.values.is_public}
          onChange={() => props.setFieldValue("is_public", false)}
        />
        <span className="ml-1">
          <strong>Private:</strong> You choose who can see and use this app.
        </span>
      </label>
    </p>
  </>
);

const Access: React.FC<{ props: FormikProps<ProjectValues>; project: Project }> = ({
  props,
  project,
}) => (
  <>
    <div className="mb-2">
      <PublicPrivateRadio props={props} project={project} />
    </div>
    {props.values.is_public && project.status === "running" && (
      <p className="my-2">
        <label>
          <Field
            component={CheckboxField}
            label="Listed: "
            description="Include this app in the public list of apps"
            name="listed"
            className="mt-1 d-inline-block mr-2"
          />
          <strong>Listed:</strong>
          <span className="ml-1">Include this app in the public list of apps.</span>
        </label>
      </p>
    )}
  </>
);

const AppTitle: React.FC<{ project: Project }> = ({ project }) => {
  const isMobile = window.innerWidth < 992;
  const id = `${project.owner}/${project.title}`;
  if (isMobile) {
    return (
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
    return (
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
};

const ReadmeField: React.FC<{}> = ({}) => (
  <div className="mt-3 mb-1">
    <label>
      <strong>README</strong>{" "}
      <Tip id="readme-markdown-icon" tip="Supports Markdown." placement="top">
        <a href="https://hackmd.io/new" target="_blank">
          <i className="fab fa-markdown mr-3" style={{ opacity: 0.8 }}></i>
        </a>
      </Tip>
    </label>
    <Field name="description">
      {({ field, meta }) => (
        <Row className="w-100">
          <Col>
            <textarea type="text" className="w-100" rows="10" {...field} />
            {meta.touched && meta.error && <div className="text-danger">{meta.error}</div>}
          </Col>
        </Row>
      )}
    </Field>
  </div>
);

const AboutAppFields: React.FC<{
  accessStatus: AccessStatus;
  props: FormikProps<ProjectValues>;
  project: Project;
  showReadme?: boolean;
}> = ({ accessStatus, props, project, showReadme }) => {
  return (
    <>
      <div>
        {!project && (
          <Field name="title">
            {({ field, meta }) => (
              <label>
                {" "}
                <strong>Title</strong>
                <Row className="justify-content-md-left">
                  {accessStatus.username && (
                    <>
                      <Col className="flex-grow-0 align-self-center">
                        <h5 className="lead font-weight-bold">{accessStatus.username}</h5>
                      </Col>
                      <Col className="flex-grow-0 align-self-center">
                        <p className="lead pt-2">/</p>
                      </Col>
                    </>
                  )}
                  <Col className="flex-grow-0 align-self-center">
                    <input
                      type="text"
                      {...field}
                      onChange={e => {
                        e.target.value = e.target.value.replace(/[^a-zA-Z0-9]+/g, "-");
                        field.onChange(e);
                      }}
                    />
                    {meta.touched && meta.error && <div className="text-danger">{meta.error}</div>}
                  </Col>
                </Row>
              </label>
            )}
          </Field>
        )}
      </div>
      <div className="my-2">
        <label>
          <strong>Description</strong>
          <span className="text-muted ml-1">(optional)</span>
        </label>
        <Field name="oneliner">
          {({ field, meta }) => (
            <Row className="w-100">
              <Col>
                <input type="text" className="w-100" {...field} />
                {meta.touched && meta.error && <div className="text-danger">{meta.error}</div>}
              </Col>
            </Row>
          )}
        </Field>
      </div>
      {showReadme && <ReadmeField />}
    </>
  );
};

const ViewProject: React.FC<{
  project: Project;
  accessStatus: AccessStatus;
}> = ({ project, accessStatus }) => {
  const id = `${project.owner}/${project.title}`;
  const goto = project.tech === "python-paramtools" ? `/${id}/new/` : `/${id}/viz/`;
  const image = node => (
    <div className="container-fluid">
      <img className="h-100 w-100" src={node.src} alt={node.alt} style={{ objectFit: "cover" }} />
    </div>
  );
  return (
    <Jumbotron className="shadow" style={{ backgroundColor: "white" }}>
      <Row className="justify-content-between mb-2">
        <Col className="col-auto align-self-center">
          <AppTitle project={project} />
        </Col>
        {accessStatus.can_write_project && (
          <Col className="col-auto align-self-center">
            <a
              className="btn btn-outline-primary"
              href={`/${project.owner}/${project.title}/settings/`}
            >
              Edit
            </a>
          </Col>
        )}
      </Row>
      <p className="lead">{project.oneliner}</p>
      <hr className="my-4" />
      <ReactMarkdown source={project.description} escapeHtml={false} renderers={{ image: image }} />
      <Row className="justify-content-between mt-5">
        <Col className="col-auto align-self-center">
          {project.status === "running" ? (
            <a className="btn btn-success" href={goto}>
              <strong>Go to App</strong>
            </a>
          ) : project.status === "staging" ? (
            <strong>Our team is preparing your app to be published.</strong>
          ) : (
            <a className="btn btn-success" href={`/${project.owner}/${project.title}/settings/`}>
              <strong>Connect App</strong>
            </a>
          )}
        </Col>
        <Col className="col-auto align-self-center">
          {project.tech && (
            <p>
              Built with{" "}
              <a href={techLinks[project.tech]}>
                <strong>{techTitles[project.tech]}</strong>
              </a>
              .
            </p>
          )}
        </Col>
      </Row>
    </Jumbotron>
  );
};

type Step = "create" | "configure" | "advanced" | "staging" | "access";

const NewProjectForm: React.FC<{
  props: FormikProps<ProjectValues>;
  project?: Project;
  accessStatus: AccessStatus;
  step: Step;
}> = ({ props, project, accessStatus, step }) => (
  <Form>
    {step === "create" && (
      <>
        <AboutAppFields
          accessStatus={accessStatus}
          props={props}
          project={project}
          showReadme={false}
        />
        <div className="mt-4">
          <PublicPrivateRadio props={props} project={project} />
        </div>
        <TechSelect props={props} project={project} />
      </>
    )}
    {project && !["running", "staging"].includes(step) && (
      <>
        <ReadmeField />
        <div className="py-4">
          <h5>Connect app:</h5>
          <TechSelect props={props} project={project} />
        </div>
        <div className="py-2">
          <i>
            Go to the{" "}
            <a href={`${techGuideLinks[props.values.tech]}`} target="_blank">
              {techTitles[props.values.tech]} guide
            </a>{" "}
            for more information.
          </i>
        </div>
        {props.values.tech === "python-paramtools" && <PythonParamTools />}
        {["bokeh", "dash"].includes(props.values.tech) && (
          <VizWithServer tech={props.values.tech} />
        )}
        <div className="py-4">
          <SourceCodeFields />
        </div>
      </>
    )}

    <div className="mt-5">
      <button className="btn inline-block btn-success" type="submit">
        <strong>{step === "create" ? "Create app" : "Connect app"}</strong>
      </button>
    </div>

    {!project && (
      <p className="mt-3">Next, you will learn how to connect your app based on your technology.</p>
    )}
  </Form>
);

const ProjectSettings: React.FC<{
  props: FormikProps<ProjectValues>;
  project?: Project;
  accessStatus: AccessStatus;
  section?: ProjectSettingsSection;
}> = ({ props, project, accessStatus, section }) => {
  return (
    <>
      <Row>
        <Col className="col-3">
          <Card>
            <Card.Header>Settings</Card.Header>
            <ListGroup variant="flush">
              <ListGroup.Item>
                <a href={`/${project.owner}/${project.title}/settings/about/`}>
                  <span className={section === "about" && "font-weight-bold"}>About</span>
                </a>
              </ListGroup.Item>
              <ListGroup.Item>
                <a href={`/${project.owner}/${project.title}/settings/configure/`}>
                  <span className={section === "configure" && "font-weight-bold"}>Configure</span>
                </a>
              </ListGroup.Item>
              <ListGroup.Item>
                <a href={`/${project.owner}/${project.title}/settings/environment/`}>
                  <span className={section === "environment" && "font-weight-bold"}>
                    Environment
                  </span>
                </a>
              </ListGroup.Item>
              <ListGroup.Item>
                <a href={`/${project.owner}/${project.title}/settings/access/`}>
                  <span className={section === "access" && "font-weight-bold"}>Access</span>
                </a>
              </ListGroup.Item>
            </ListGroup>
          </Card>
        </Col>
        <Col className="col-9">
          <Form>
            {section === "about" && (
              <AboutAppFields
                accessStatus={accessStatus}
                props={props}
                project={project}
                showReadme={true}
              />
            )}

            {section === "configure" && (
              <>
                <div className="py-2">
                  <TechSelect props={props} project={project} />
                </div>
                {props.values.tech === "python-paramtools" && <PythonParamTools />}
                {["bokeh", "dash"].includes(props.values.tech) && (
                  <VizWithServer tech={props.values.tech} />
                )}
              </>
            )}

            {section === "environment" && (
              <div className="py-2">
                <SourceCodeFields />
                <AdvancedFields />
              </div>
            )}

            {section === "access" && (
              <div className="py-2">
                <Access props={props} project={project} />
              </div>
            )}

            <button className="btn inline-block btn-success mt-5" type="submit">
              <strong>Save changes</strong>
            </button>
          </Form>
        </Col>
      </Row>
    </>
  );
};

class ProjectApp extends React.Component<
  PublishProps,
  PublishState & {
    showTechOpts: boolean;
    project?: Project;
    step: Step | null;
    showAuthDialog: boolean;
  }
> {
  constructor(props) {
    super(props);
    let initialValues = {};
    for (const [key, value] of Object.entries(this.props.initialValues)) {
      initialValues[key] = value === null ? "" : value;
    }
    this.state = {
      initialValues: initialValues as ProjectValues,
      showTechOpts: false,
      project: this.props.project,
      step: null,
      showAuthDialog: true,
    };
    this.stepFromProject = this.stepFromProject.bind(this);
  }

  stepFromProject(project) {
    if (!project || project.status === "created") {
      return "create";
    } else if (project?.status === "configuring") {
      return "configure";
    } else if (project?.status === "installing") {
      return "advanced";
    } else {
      return "create";
    }
  }

  render() {
    const { accessStatus } = this.props;
    const { project, showAuthDialog } = this.state;
    const step = this.state.step || this.stepFromProject(this.state.project);
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
                this.props.api.owner = project.owner;
                this.props.api.title = project.title;
                if (project.status !== "created" && project.status !== "configuring") {
                  window.location.href = `/${project.owner}/${project.title}/`;
                } else {
                  history.pushState(null, null, `/${project.owner}/${project.title}/`);
                  this.setState({ project, step: this.stepFromProject(project) });
                }
                actions.setStatus({ auth: null });
              })
              .catch(error => {
                console.log("error", error);
                console.log(error.response.data);
                actions.setSubmitting(false);
                if (error.response.status == 400) {
                  actions.setStatus(error.response.data);
                } else if (error.response.status == 401) {
                  actions.setStatus({
                    auth: "You must be logged in to publish an app.",
                  });
                }
                window.scroll(0, 0);
              });
          }}
          validateOnChange={true}
          validationSchema={Schema}
        >
          {(props: FormikProps<ProjectValues>) => (
            <>
              {props.status?.project_exists && (
                <div className="alert alert-danger" role="alert">
                  {props.status.project_exists}
                </div>
              )}
              {(props.status?.auth || !accessStatus.username) && (
                <div className="alert alert-primary alert-dismissible" role="alert">
                  You must be logged in to publish a model.
                </div>
              )}
              {props.status?.auth && !accessStatus.username && (
                <AuthDialog
                  show={showAuthDialog}
                  setShow={show => this.setState({ showAuthDialog: show })}
                  initialAction="sign-up"
                  resetAccessStatus={async () => {
                    await this.props.resetAccessStatus();
                    props.handleSubmit();
                  }}
                  message="You must be logged in to create or update an app."
                />
              )}
              {props.status?.collaborators && (
                <PrivateAppException
                  upgradeTo={(props.status.collaborators as ResourceLimitException).upgrade_to}
                />
              )}
              {project?.status === "running" || project?.status === "staging" ? (
                <ProjectSettings
                  props={props}
                  project={project}
                  accessStatus={accessStatus}
                  section={this.props.section}
                />
              ) : (
                <NewProjectForm
                  props={props}
                  project={project}
                  accessStatus={accessStatus}
                  step={step}
                />
              )}
            </>
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
    this.resetAccessStatus = this.resetAccessStatus.bind(this);
  }

  async resetAccessStatus() {
    const accessStatus = await this.api.getAccessStatus();
    this.setState({ accessStatus });
    return accessStatus;
  }

  async componentDidMount() {
    const accessStatus = await this.api.getAccessStatus();
    this.setState({
      accessStatus,
    });
  }

  render() {
    if (!this.state.accessStatus) {
      return <div />;
    }
    return (
      <>
        <AuthPortal>
          <AuthButtons
            accessStatus={this.state.accessStatus}
            resetAccessStatus={this.resetAccessStatus}
            message="You must be logged in to create an app."
          />
        </AuthPortal>

        <Card className="card-outer">
          <Row className="w-100 justify-content-center">
            <Col style={{ maxWidth: "1000px" }}>
              <Card.Body>
                <Card.Title>
                  <h1 className="mb-2 pb-2 border-bottom">Create a new application</h1>
                  <small className="mb-3">
                    <i>
                      Not sure where to get started?{" "}
                      <a href="mailto:hank@compute.studio?subject=Getting%20Started&body=Hi%20Hank,%20I'm%20%20interested%20in%20publishing%20an%20app.%20Can%20you%20help%20me%20out?">
                        Send us a message.
                      </a>
                    </i>
                  </small>
                </Card.Title>
                <ProjectApp
                  initialValues={initialValues}
                  accessStatus={this.state.accessStatus}
                  resetAccessStatus={this.resetAccessStatus}
                  api={this.api}
                />
              </Card.Body>
            </Col>
          </Row>
        </Card>
      </>
    );
  }
}

class ProjectDetail extends React.Component<
  { match: Match; edit: boolean; section?: ProjectSettingsSection },
  { project?: Project; accessStatus?: AccessStatus; edit: boolean }
> {
  api: API;
  constructor(props) {
    super(props);
    this.state = { edit: this.props.edit };
    const owner = this.props.match.params.username;
    const title = this.props.match.params.app_name;
    this.api = new API(owner, title);

    this.resetAccessStatus = this.resetAccessStatus.bind(this);
  }

  async resetAccessStatus() {
    const accessStatus = await this.api.getAccessStatus();
    this.setState({ accessStatus });
    return accessStatus;
  }

  async componentDidMount() {
    const project = await this.api.getProject();
    const accessStatus = await this.api.getAccessStatus();
    this.setState({
      accessStatus,
      project,
    });
  }

  render() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const id = `${username}/${app_name}`;
    if (!this.state.project || !this.state.accessStatus) {
      return <div />;
    }
    let style;
    if (!["staging", "running"].includes(this.state.project?.status)) {
      style = { maxWidth: "1000px" };
    }
    return (
      <>
        <AuthPortal>
          <AuthButtons
            accessStatus={this.state.accessStatus}
            resetAccessStatus={this.resetAccessStatus}
            message="You must be logged in to update an app."
          />
        </AuthPortal>

        {this.state.edit ? (
          <Card className="card-outer">
            <Row className="w-100 justify-content-center">
              <Col style={style}>
                <Card.Body>
                  <Card.Title>
                    <AppTitle project={this.state.project} />
                  </Card.Title>
                  <ProjectApp
                    project={this.state.project}
                    accessStatus={this.state.accessStatus}
                    resetAccessStatus={this.resetAccessStatus}
                    initialValues={(this.state.project as unknown) as ProjectValues}
                    api={this.api}
                    section={this.props.section}
                    edit={this.props.edit}
                  />
                </Card.Body>
              </Col>
            </Row>
          </Card>
        ) : (
          <ViewProject project={this.state.project} accessStatus={this.state.accessStatus} />
        )}
      </>
    );
  }
}

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route exact path="/publish/" component={CreateProject} />
      <Route exact path="/new/" component={CreateProject} />
      <Route
        path="/:username/:app_name/settings/about/"
        render={routeProps => <ProjectDetail edit={true} section="about" {...routeProps} />}
      />
      <Route
        path="/:username/:app_name/settings/configure/"
        render={routeProps => <ProjectDetail edit={true} section="configure" {...routeProps} />}
      />
      <Route
        path="/:username/:app_name/settings/environment/"
        render={routeProps => <ProjectDetail edit={true} section="environment" {...routeProps} />}
      />
      <Route
        path="/:username/:app_name/settings/access/"
        render={routeProps => <ProjectDetail edit={true} section="access" {...routeProps} />}
      />
      <Route
        path="/:username/:app_name/settings/"
        render={routeProps => <ProjectDetail edit={true} section="about" {...routeProps} />}
      />

      <Route
        path="/:username/:app_name/"
        render={routeProps => <ProjectDetail edit={false} {...routeProps} />}
      />
    </Switch>
  </BrowserRouter>,
  domContainer
);
