import moment = require("moment");
import React = require("react");
import ReactLoading from "react-loading";
import { Row, Col, Card, Button, Table } from "react-bootstrap";
import { AuthPortal, AuthButtons } from "../../auth";
import { Tip } from "../../components";
import { Project, AccessStatus, Build } from "../../types";
import API from "../API";
import { AppTitle, SettingsSidebar } from "../components";
import { Match, ProjectSettingsSection } from "../types";

const BuildStatus: React.FC<{ status: string }> = ({ status }) => {
  switch (status) {
    case "success":
      return (
        <Tip id="build-status" tip="Success">
          <i className="fas fa-check-circle text-success"></i>
        </Tip>
      );
    case "failure":
      return (
        <Tip id="build-status" tip="Failure">
          <i className="fas fa-times-circle text-danger"></i>
        </Tip>
      );
    case "cancelled":
      return (
        <Tip id="build-status" tip="Cancelled">
          <i className="fas fa-exclamation-circle text-info"></i>
        </Tip>
      );
    default:
      return (
        <Tip id="build-status" tip="Running">
          <ReactLoading type="spin" color="#DBAB0A" height={"20px"} width={"20px"} />
        </Tip>
      );
  }
};

class BuildHistory extends React.Component<
  { match: Match; section?: ProjectSettingsSection },
  { project?: Project; accessStatus?: AccessStatus; builds?: Build[]; errorMessage?: string }
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
    if ((build as any).errors) {
      this.setState({ errorMessage: (build as any).errors });
      window.scrollTo(0, 0);
      return;
    }
    window.location.replace(`/${username}/${app_name}/builds/${build.id}/`);
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
        <Card className="card-outer p-4">
          <Row className="w-100 justify-content-center">
            <Col className="col-md-3">
              <SettingsSidebar project={project} section="build-history" />
            </Col>
            <Col className="col-md-9">
              <Card.Body>
                <Card.Title>
                  <AppTitle project={this.state.project} />
                </Card.Title>
                {this.state.errorMessage && (
                  <div className="alert alert-danger" role="alert">
                    {this.state.errorMessage}
                  </div>
                )}

                <Table>
                  <thead>
                    <tr>
                      <th>Link</th>
                      <th>Created at</th>
                      <th>Status</th>
                      <th>Tag</th>
                      <th>Version</th>
                    </tr>
                  </thead>
                  <tbody>
                    {this.state.builds.map((build, index) => (
                      <tr key={index}>
                        <th>
                          <a href={`/${build.project}/builds/${build.id}/`}>
                            <i className="fas fa-link" />
                          </a>
                        </th>
                        <th>{build.created_at && moment(build.created_at).format("lll")}</th>
                        <th>
                          <BuildStatus status={build.status} />
                        </th>
                        <th>
                          {build.tag?.image_tag ? (
                            <code>{build.tag.image_tag.slice(0, 6)}</code>
                          ) : (
                            "N/A"
                          )}
                        </th>
                        <th>{build.tag?.version || "N/A"}</th>
                      </tr>
                    ))}
                  </tbody>
                </Table>
                <Button variant="success" onClick={async () => await this.startNewBuild()}>
                  New Build
                </Button>
              </Card.Body>
            </Col>
          </Row>
        </Card>
      </>
    );
  }
}

export { BuildHistory };
