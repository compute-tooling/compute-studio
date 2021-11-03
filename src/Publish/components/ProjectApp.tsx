import { Step } from "bokehjs";
import { Formik, FormikHelpers, FormikProps } from "formik";
import React = require("react");
import { AuthDialog } from "../../auth";
import { Project, ResourceLimitException } from "../../types";
import { Schema } from "../schema";
import { PublishProps, PublishState, ProjectValues } from "../types";
import { NewProjectForm, PrivateAppException, ProjectSettings } from ".";

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

  stepFromProject(project): Step {
    if (!project || project.status === "created") {
      return ("create" as unknown) as Step;
    } else if (project?.status === "configuring") {
      return ("configure" as unknown) as Step;
    } else if (project?.status === "installing") {
      return ("advanced" as unknown) as Step;
    } else {
      return ("create" as unknown) as Step;
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
                  actions.setStatus({ private_app: error.response.data?.app });
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
              {props.status?.private_app && (
                <PrivateAppException
                  upgradeTo={(props.status.private_app as ResourceLimitException).upgrade_to}
                />
              )}
              {project?.status === "running" || project?.status === "staging" ? (
                <ProjectSettings
                  props={props}
                  project={project}
                  section={this.props.section}
                />
              ) : (
                <NewProjectForm
                  props={props}
                  project={project}
                  accessStatus={accessStatus}
                  step={(step as unknown) as Step}
                />
              )}
            </>
          )}
        </Formik>
      </div>
    );
  }
}

export { ProjectApp };
