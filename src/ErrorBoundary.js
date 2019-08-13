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
        <Card>
          <Card.Title>Something went wrong.</Card.Title>
          <Card.Body>
            {process.env.NODE_ENV === "production" ? (
              <p>
                Please notify COMP developers by opening an issue in the COMP
                source code repository or emailing Hank.
              </p>
            ) : (
              <details style={{ whiteSpace: "pre-wrap" }}>
                {this.state.error && this.state.error.toString()}
                <br />
                {this.state.errorInfo.componentStack}
              </details>
            )}
          </Card.Body>
        </Card>
      );
    }

    return this.props.children;
  }
}
