import moment = require("moment");
import React = require("react");
import ReactLoading from "react-loading";

import { Row, Col, Card, Button, ListGroup, ListGroupItem } from "react-bootstrap";
import { AuthPortal, AuthButtons } from "../../auth";
import { Tip } from "../../components";
import { Project, AccessStatus, Build } from "../../types";
import API from "../API";
import { AppTitle } from "../components";
import { Match } from "../types";

type LogItem = {
  stage: String;
  logs: String;
  cmd: String;
};

const statusOrder = {
  created: 0,
  building: 1,
  testing: 2,
  pushing: 3,
  success: 4,
  failure: 5,
  cancelled: 6,
};

const isBefore = (status, other) => statusOrder[status] < statusOrder[other];
const isAfter = (status, other) => statusOrder[status] > statusOrder[other];

const StageComponent: React.FC<{
  name: string;
  label: string;
  currentStage: string;
  logItem?: LogItem;
  failed_at_stage?: string;
}> = ({ name, label, currentStage, logItem, failed_at_stage }) => {
  const [showLogs, setShowLogs] = React.useState(false);
  return (
    <ListGroupItem className="w-100">
      <Row className="w-50">
        {logItem?.logs && (
          <Col className="col-3">
            <Button variant="outline-primary" onClick={() => setShowLogs(!showLogs)}>
              <i className={`fas fa-arrow-${showLogs ? "down" : "right"}`}></i>
            </Button>
          </Col>
        )}

        <Col className="col-1">
          {name === currentStage && (
            <Tip id="build-status" tip="Running">
              <ReactLoading type="spin" color="#DBAB0A" height={"20px"} width={"20px"} />
            </Tip>
          )}
          {failed_at_stage === name && (
            <Tip id="build-status" tip="Failure">
              <i className="fas fa-times-circle text-danger"></i>
            </Tip>
          )}
          {isBefore(name, currentStage) &&
            (!failed_at_stage || isBefore(name, failed_at_stage)) &&
            currentStage !== "cancelled" && (
              <Tip id="build-status" tip="Success">
                <i className="fas fa-check-circle text-success"></i>
              </Tip>
            )}

          {currentStage === "cancelled" && (
            <Tip id="build-status" tip="Cancelled">
              <i className="fas fa-exclamation-circle text-info"></i>
            </Tip>
          )}
        </Col>
        <Col className="col-8">
          <h3>{label}</h3>
        </Col>
      </Row>
      {showLogs && (
        <Row className="py-4 rounded" style={{ backgroundColor: "rgb(36, 41, 47)" }}>
          <Col>
            <pre>
              <code style={{ color: "rgb(208, 215, 222)" }}>
                {logItem?.logs || "Logs unavailable."}
              </code>
            </pre>
          </Col>
        </Row>
      )}
    </ListGroupItem>
  );
};

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
    this.setState({ build });
    window.location.replace(`/${username}/${app_name}/builds/${build.id}/`);
  }

  async promoteTag() {
    const { image_tag, version } = this.state.build?.tag;
    await this.api.promoteTag(image_tag, version);
    const { username, app_name } = this.props.match.params;
    window.location.replace(`/${username}/${app_name}/builds/`);
  }

  async refreshBuild() {
    const { build_id } = this.props.match.params;
    const build = await this.api.getBuild(build_id);
    this.setState({ build });

    if (
      ["success", "cancelled", "failure"].includes(build.status) &&
      !build.provider_data?.logs?.length
    ) {
      const { build_id } = this.props.match.params;
      const build = await this.api.getBuild(build_id, true);
      this.setState({ build });
    } else {
      setTimeout(async () => await this.refreshBuild(), 10000);
    }
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
    if (!["success", "cancelled", "failure"].includes(build.status)) {
      setTimeout(async () => await this.refreshBuild(), 5000);
    }
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
                  <Row className="justify-conent-between align-items-center">
                    <Col className="col-9">
                      <AppTitle project={this.state.project} />
                    </Col>
                    <Col className="col-3">
                      <a href={`/${username}/${app_name}/builds/`}>
                        <i className="fas fa-history"></i> Build History
                      </a>
                    </Col>
                  </Row>
                </Card.Title>
                {build_id ? (
                  <div>
                    {/* <summary>
                      Build Details:{" "}
                      <details>
                        <pre>
                          <code>{JSON.stringify(build || {}, null, 2)}</code>
                        </pre>
                      </details>
                    </summary> */}
                    {build.status === "success" && (
                      <p className="lead">
                        <Tip id="build-status" tip="Success">
                          <i className="fas fa-check-circle text-success"></i>
                        </Tip>
                        <span className="px-2">Build succeeded</span>
                      </p>
                    )}
                    {build.status === "failure" && (
                      <p className="lead">
                        <Tip id="build-status" tip="Failure">
                          <i className="fas fa-times-circle text-danger"></i>
                        </Tip>
                        <span className="px-2">Build failed</span>
                      </p>
                    )}
                    {build.status === "cancelled" && (
                      <p className="lead">
                        <Tip id="build-status" tip="Cancelled">
                          <i className="fas fa-exclamation-circle text-info"></i>
                        </Tip>
                        <span className="px-2">Build cancelled</span>
                      </p>
                    )}

                    <p>Started at {moment(build.created_at).format("lll")}.</p>
                    {build.finished_at && (
                      <p>
                        Completed in{" "}
                        {moment
                          .duration(
                            new Date(build.finished_at).getTime() -
                              new Date(build.created_at).getTime()
                          )
                          .humanize()}
                        .
                      </p>
                    )}
                    {build.status === "success" && (
                      <p>Project version: {build.tag?.version || "Version not available."}</p>
                    )}

                    <Card className={`mt-5 ${build.status === "created" && "border-0"}`}>
                      {build.status === "created" && <p>Starting the build...</p>}
                      {isAfter(build.status, "created") && (
                        <>
                          <Card.Header>Stages</Card.Header>
                          <StageComponent
                            name="building"
                            label="Build"
                            currentStage={build.status}
                            logItem={(build.provider_data?.logs as Array<LogItem>)?.find(
                              item => item.stage === "build"
                            )}
                            failed_at_stage={build.failed_at_stage}
                          />
                          <StageComponent
                            name="testing"
                            label="Test"
                            currentStage={build.status}
                            logItem={(build.provider_data?.logs as Array<LogItem>)?.find(
                              item => item.stage === "test"
                            )}
                            failed_at_stage={build.failed_at_stage}
                          />
                          <StageComponent
                            name="pushing"
                            label="Stage"
                            currentStage={build.status}
                            logItem={(build.provider_data?.logs as Array<LogItem>)?.find(
                              item => item.stage === "push"
                            )}
                            failed_at_stage={build.failed_at_stage}
                          />
                        </>
                      )}
                    </Card>
                    <div className="py-5">
                      {build.status === "success" && (
                        <Button onClick={async () => await this.promoteTag()}>Release</Button>
                      )}
                      {["failure", "cancelled"].includes(build.status) && (
                        <Button onClick={async () => await this.startNewBuild()}>
                          Failure. Start new build
                        </Button>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="py-2">
                    <Button variant="success" onClick={async () => await this.startNewBuild()}>
                      New Build
                    </Button>
                  </div>
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
