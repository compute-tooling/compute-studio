import React = require("react");
import { Card, Col, Row } from "react-bootstrap";
import { AuthPortal, AuthButtons } from "../../auth";
import { AccessStatus } from "../../types";
import API from "../API";
import { ProjectApp } from "../components";
import { initialValues } from "../initialValues";

class NewProject extends React.Component<{}, { accessStatus?: AccessStatus }> {
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

export { NewProject };
