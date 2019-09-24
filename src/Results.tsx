import * as React from "react";
import { Card } from "react-bootstrap";

export default class Results extends React.Component<{}, {}> {
  constructor(props) {
    super(props);
  }
  render() {
    return (
      <Card>
        <Card.Title>Hello world!</Card.Title>
      </Card>
    );
  }
}
