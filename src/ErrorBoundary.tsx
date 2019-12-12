import * as React from "react";
import { Card } from "react-bootstrap";
import * as Sentry from "@sentry/browser";

type ErrorState = Readonly<{
  eventId: any,
  error: any,
  errorInfo: any
}>

export default class ErrorBoundary extends React.Component<{}, ErrorState> {
  isProduction: boolean
  constructor(props) {
    super(props);
    this.state = { error: null, errorInfo: null, eventId: null };
    this.isProduction = process.env.NODE_ENV === "production";
  }

  componentDidCatch(error, errorInfo) {
    if (this.isProduction) {
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

    if (this.state.errorInfo && this.isProduction) {
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
    } else if (this.state.errorInfo) {
      return (
        <Card>
          <Card.Body>
            <h2>Something went wrong.</h2>
            <details style={{ whiteSpace: 'pre-wrap' }}>
              {this.state.error && this.state.error.toString()}
              <br />
              {this.state.errorInfo.componentStack}
            </details>
          </Card.Body>
        </Card>
      )
    }

    return this.props.children;
  }
}
