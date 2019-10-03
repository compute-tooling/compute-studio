import React from "react";
import { Card } from "react-bootstrap";
import * as Sentry from "@sentry/browser";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null, errorInfo: null };
  }

  componentDidCatch(error, errorInfo) {
    if (process.env.NODE_ENV === "production") {
      Sentry.withScope(scope => {
        scope.setExtras(errorInfo);
        const eventId = Sentry.captureException(error);
        this.setState({
          eventId,
          error: error,
          errorInfo: errorInfo
        });
      });
    } else {
      this.setState({
        error,
        errorInfo
      });
    }
  }

  render() {
    if (this.state.errorInfo) {
      // Error path
      return (
        <Card className="card-outer">
          <Card.Body>
            <Card.Title>
              <h2>Whoops! Compute Studio has experienced an error.</h2>
            </Card.Title>
            <Card.Text>
              The Compute Studio technical team has been notified of this error
              and is working to fix it. In addition, you are welcome to discuss
              this issue with the Compute Studio technical team by opening an{" "}
              <a href="https://github.com/compute-tooling/compute-studio/issues/new">
                issue
              </a>{" "}
              in the Compute Studio source code repository or{" "}
              <a href="mailto:hank@compute.studio">emailing Hank</a>.
            </Card.Text>
          </Card.Body>
        </Card>
      );
    }

    return this.props.children;
  }
}
