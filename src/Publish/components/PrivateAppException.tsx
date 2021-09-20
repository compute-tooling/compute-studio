import React = require("react");
import { Row, Col, Button } from "react-bootstrap";

const PrivateAppException: React.FC<{ upgradeTo: "pro" }> = ({ upgradeTo }) => {
  let plan;
  if (upgradeTo === "pro") {
    plan = "Compute Studio Pro";
  }
  return (
    <div className="alert alert-primary alert-dismissible fade show" role="alert">
      You must upgrade to{" "}
      <a href="/billing/upgrade/">
        <strong>{plan}</strong>
      </a>{" "}
      to make this app private.
      <Row className="w-100 justify-content-center">
        <Col className="col-auto">
          <Button
            variant="primary"
            style={{ fontWeight: 600 }}
            className="w-100 mt-3"
            href="/billing/upgrade/"
          >
            Upgrade to {plan}
          </Button>
        </Col>
      </Row>
      <button type="button" className="close" data-dismiss="alert" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>
  );
};

export { PrivateAppException };
