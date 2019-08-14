import React from "react";
import { Card } from "react-bootstrap";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null, errorInfo: null };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
  }

  render() {
    if (this.state.errorInfo) {
      // Error path
      return (
        <Card className="card-outer">
          <Card.Body>
            <Card.Title>
              <h2>Whoops! COMP has experienced an error.</h2>
            </Card.Title>
            <Card.Text>
              <p>
                The COMP technical team has been notified of this error and is
                working to fix it. In addition, you are welcome to discuss this
                issue with the COMP technical team by opening an{" "}
                <a href="https://github.com/comp-org/comp-ce/issues/new">
                  issue
                </a>{" "}
                in the COMP source code repository or{" "}
                <a href="mailto:henrymdoupe@gmail.com">emailing Hank</a>.
              </p>
            </Card.Text>
          </Card.Body>
        </Card>
      );
    }

    return this.props.children;
  }
}
