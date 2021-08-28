import React = require("react");
import { Card, Col, Row } from "react-bootstrap";
import { AuthPortal, AuthButtons } from "../../auth";
import { Project, AccessStatus } from "../../types";
import API from "../API";
import { ProjectApp, AppTitle, ViewProject } from "../components";
import { Match, ProjectSettingsSection, ProjectValues } from "../types";

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

export { ProjectDetail };
