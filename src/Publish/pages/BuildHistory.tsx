import moment = require("moment");
import React = require("react");
import { Row, Col, Card } from "react-bootstrap";
import { AuthPortal, AuthButtons } from "../../auth";
import { Project, AccessStatus, Build } from "../../types";
import API from "../API";
import { AppTitle } from "../components";
import { Match, ProjectSettingsSection } from "../types";

class BuildHistory extends React.Component<
  { match: Match; section?: ProjectSettingsSection },
  { project?: Project; accessStatus?: AccessStatus; builds?: Build[] }
> {
  api: API;
  constructor(props) {
    super(props);
    this.state = {};
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
    const buildResults = await this.api.listBuilds();
    this.setState({
      accessStatus,
      project,
      builds: buildResults.results,
    });
  }

  render() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const { project, accessStatus, builds } = this.state;
    const id = `${username}/${app_name}`;
    if (!project || !accessStatus || builds === undefined) {
      return <div />;
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
        <Card className="card-outer">
          <Row className="w-100 justify-content-center">
            <Col>
              <Card.Body>
                <Card.Title>
                  <AppTitle project={this.state.project} />
                </Card.Title>
                {this.state.builds.map((build, index) => (
                  <Row key={index}>
                    <Col>{build.created_at && moment(build.created_at).toLocaleString()}</Col>
                    <Col>{build.status}</Col>
                  </Row>
                ))}
              </Card.Body>
            </Col>
          </Row>
        </Card>
      </>
    );
  }
}

export { BuildHistory };
