import { Step } from "bokehjs";
import { Formik, FormikHelpers, FormikProps } from "formik";
import React = require("react");
import { Card, Col, Row } from "react-bootstrap";
import { AuthPortal, AuthButtons, AuthDialog } from "../../auth";
import { AccessStatus, Build, Project, ResourceLimitException } from "../../types";
import API from "../API";
import { NewProjectForm, PrivateAppException, ProjectApp, ProjectSettings } from "../components";
import { initialValues } from "../initialValues";
import { Schema } from "../schema";
import { ProjectValues } from "../types";
import { BuildPage } from "./Build";

class NewProject extends React.Component<
  {},
  { accessStatus?: AccessStatus; showAuthDialog: boolean; project?: Project; build?: Build }
> {
  api: API;
  constructor(props) {
    super(props);
    this.state = {
      showAuthDialog: false,
    };

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
    const { accessStatus, showAuthDialog, project, build } = this.state;
    if (!accessStatus) {
      return <div />;
    }
    return (
      <>
        <AuthPortal>
          <AuthButtons
            accessStatus={accessStatus}
            resetAccessStatus={this.resetAccessStatus}
            message="You must be logged in to create an app."
          />
        </AuthPortal>

        <Card className="card-outer">
          <Row className="w-100 justify-content-center">
            <Col>
              <Card.Body>
                <Card.Title>
                  <h1 className="mb-2 pb-2 border-bottom">Create a new project</h1>
                  <small className="mb-3">
                    <i>
                      Not sure where to get started?{" "}
                      <a href="mailto:hank@compute.studio?subject=Getting%20Started&body=Hi%20Hank,%20I'm%20%20interested%20in%20publishing%20an%20app.%20Can%20you%20help%20me%20out?">
                        Send us a message.
                      </a>
                    </i>
                  </small>
                </Card.Title>
                <Formik
                  initialValues={initialValues}
                  onSubmit={(values: ProjectValues, actions: FormikHelpers<ProjectValues>) => {
                    var formdata = new FormData();
                    for (const field in values) {
                      formdata.append(field, values[field]);
                    }
                    this.api
                      .save(formdata)
                      .then(project => {
                        actions.setSubmitting(false);
                        this.api.owner = project.owner;
                        this.api.title = project.title;
                        history.pushState(null, null, `/${project.owner}/${project.title}/`);
                        if (!this.state.project) {
                          // go ahead and create build if  project is new.
                          this.api.createBuild({}).then(build => {
                            this.setState({ build });
                          });
                        }
                        this.setState({ project });
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
                      {(props.status?.auth || !this.state.accessStatus.username) && (
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
                            await this.resetAccessStatus();
                            props.handleSubmit();
                          }}
                          message="You must be logged in to create or update an app."
                        />
                      )}
                      {props.status?.private_app && (
                        <PrivateAppException
                          upgradeTo={
                            (props.status.private_app as ResourceLimitException).upgrade_to
                          }
                        />
                      )}
                      <Row>
                        <Col className={build ? "col-3" : "col-12"}>
                          <NewProjectForm
                            props={props}
                            project={project}
                          />
                        </Col>
                        {!!build && (
                          <Col className="col-9">
                            <BuildPage
                              api={this.api}
                              match={{
                                params: {
                                  username: project.owner,
                                  app_name: project.title,
                                  build_id: build.id,
                                },
                              }}
                            />
                          </Col>
                        )}
                      </Row>
                    </>
                  )}
                </Formik>
              </Card.Body>
            </Col>
          </Row>
        </Card>
      </>
    );
  }
}

export { NewProject };
