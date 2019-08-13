import React from "react";
import { Card } from "react-bootstrap";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    console.log("error boundary");
    this.state = { error: null, errorInfo: null };
  }

  componentDidCatch(error, errorInfo) {
    // You can also log the error to an error reporting service
    console.log("did catch?", error, errorInfo);
    console.log(process.env.NODE_ENV);
    this.setState({
      error: error,
      errorInfo: errorInfo
    })
  }

  render() {
    console.log("triggered!!!!", this.state.errorInfo)
    if (this.state.errorInfo) {
      // Error path
      return (
        <Card>
          <Card.Title>Something went wrong.</Card.Title>
          <Card.Body>
            <details style={{ whiteSpace: 'pre-wrap' }}>
              {this.state.error && this.state.error.toString()}
              <br />
              {this.state.errorInfo.componentStack}
            </details>
          </Card.Body>
        </Card>
      );
    }

    return this.props.children;
  }
}
