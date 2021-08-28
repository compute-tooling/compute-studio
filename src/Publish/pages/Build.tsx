import moment = require("moment");
import React = require("react");
import { Row, Col, Card, Button } from "react-bootstrap";
import { AuthPortal, AuthButtons } from "../../auth";
import { Project, AccessStatus, Build } from "../../types";
import API from "../API";
import { AppTitle } from "../components";
import { Match, ProjectSettingsSection } from "../types";

class BuildPage extends React.Component<
  { match: Match },
  { project?: Project; accessStatus?: AccessStatus; build?: Build }
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

  async startNewBuild() {
    const { username, app_name, build_id } = this.props.match.params;
    const build = await this.api.createBuild({});
    this.setState({build})
    window.location.replace(`/${username}/${app_name}/builds/${build.id}/`);
  }

  async refreshBuild() {
    const { build_id } = this.props.match.params;
    const build = await this.api.getBuild(build_id);
    this.setState({build});
  }

  async componentDidMount() {
    const project = await this.api.getProject();
    const accessStatus = await this.api.getAccessStatus();
    let build;
    if (this.props.match.params.build_id) {
      build = await this.api.getBuild(this.props.match.params.build_id);
    }
    this.setState({
      accessStatus,
      project,
      build: build,
    });
  }

  render() {
    const { username, app_name, build_id } = this.props.match.params;
    const { project, accessStatus, build } = this.state;
    const id = `${username}/${app_name}`;
    if (!project || !accessStatus) {
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
                {build_id ? (
                  <div>
                    Build Details:{" "}
                    <pre>
                      <code>{JSON.stringify(build || {}, null, 2)}</code>
                    </pre>
                    {!["success", "failure"].includes(build.status) && <Button onClick={async () => await this.refreshBuild()}>Refresh Status</Button>}
                    {build.status === "success" && <Button onClick={() => alert("noop ha ha")}>Make it live!</Button>}
                    {build.status === "failure" && <Button onClick={async () => await this.startNewBuild()}>Failure. Start new build</Button>}

                  </div>
                ) : (
                  <Button variant="success" onClick={async () => await this.startNewBuild()}>New Build</Button>
                )}
              </Card.Body>
            </Col>
          </Row>
        </Card>
      </>
    );
  }
}

export { BuildPage };
