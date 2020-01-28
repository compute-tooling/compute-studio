import { Button, Modal, Collapse, Row, Col } from "react-bootstrap";
import * as React from "react";
import ReactLoading from "react-loading";

import { AuthDialog } from "../auth";
import { AccessStatus } from "../types";
import { NotifyOnCompletion } from "./notify";

export const ValidatingModal: React.FC<{ defaultShow?: boolean }> = ({ defaultShow = true }) => {
  const [show, setShow] = React.useState(defaultShow);

  return (
    <div>
      <Modal show={show} onHide={() => setShow(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Validating inputs...</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="d-flex justify-content-center">
            <ReactLoading type="spokes" color="#28a745" />
          </div>
        </Modal.Body>
      </Modal>
    </div>
  );
};

const PricingInfoCollapse: React.FC<{ accessStatus: AccessStatus }> = ({ accessStatus }) => {
  const [collapseOpen, setCollapseOpen] = React.useState(false);

  return (
    <>
      <Button
        onClick={() => setCollapseOpen(!collapseOpen)}
        aria-controls="pricing-collapse-text"
        aria-expanded={collapseOpen}
        className="mt-3 mb-3"
        variant="outline-info"
      >
        Pricing
      </Button>
      <Collapse in={collapseOpen}>
        <div id="pricing-collapse-text">
          The models are offered for free, but you pay for the computational resources used to run
          them. The prices are equal to Google Cloud Platform compute pricing, subject to costing at
          least one penny for a single run.
          <ul>
            <li>
              The price per hour of a server running this model is: ${`${accessStatus.server_cost}`}
              /hour.
            </li>
            <li>
              The expected time required for a single run of this model is:{" "}
              {`${accessStatus.exp_time}`} seconds.
            </li>
          </ul>
        </div>
      </Collapse>
    </>
  );
};

const RequirePmtDialog: React.FC<{
  accessStatus: AccessStatus;
  show: boolean;
  setShow?: React.Dispatch<any>;
  handleSubmit: () => void;
}> = ({ accessStatus, show, setShow, handleSubmit }) => {
  const handleCloseWithRedirect = (e, redirectLink) => {
    e.preventDefault();
    setShow(false);
    window.location.href = redirectLink;
  };
  return (
    <Modal show={show} onHide={() => setShow(false)}>
      <Modal.Header closeButton>
        <Modal.Title>Add a payment method</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        You must submit a payment method to run paid simulations.
        <PricingInfoCollapse accessStatus={accessStatus} />
      </Modal.Body>
      <Modal.Footer>
        <Button variant="outline-secondary" onClick={() => setShow(false)}>
          Close
        </Button>
        <Button variant="success" onClick={e => handleCloseWithRedirect(e, "/billing/update/")}>
          <b>Add payment method</b>
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

const RunDialog: React.FC<{
  accessStatus: AccessStatus;
  show: boolean;
  setShow?: React.Dispatch<any>;
  handleSubmit: () => void;
  setNotify: (notify: boolean) => void;
  notify: boolean;
}> = ({ accessStatus, show, setShow, handleSubmit, setNotify, notify }) => {
  const handleCloseWithSubmit = () => {
    setShow(false);
    handleSubmit();
  };

  let message = "This model's simulations are sponsored and thus, are free for you.";
  if (accessStatus.sponsor_message) {
    message = accessStatus.sponsor_message;
  }

  let body;
  if (accessStatus.is_sponsored) {
    body = (
      <Modal.Body>
        <div dangerouslySetInnerHTML={{ __html: message }} />
      </Modal.Body>
    );
  } else {
    body = (
      <Modal.Body>
        <p>
          This simulation will cost ${`${accessStatus.exp_cost}`}. You will be billed at the end of
          the monthly billing period.
        </p>
        <PricingInfoCollapse accessStatus={accessStatus} />
      </Modal.Body>
    );
  }

  return (
    <Modal show={show} onHide={() => setShow(false)}>
      <Modal.Header closeButton>
        <Modal.Title>Are you sure that you want to run this simulation?</Modal.Title>
      </Modal.Header>
      {body}
      <Modal.Footer style={{ justifyContent: "none" }}>
        <Row className="align-items-center w-100">
          <Col className="align-self-start col-7">
            <NotifyOnCompletion setNotify={setNotify} notify={notify} />
          </Col>
          <Col className="align-self-end">
            <Button className="mr-2" variant="secondary" onClick={() => setShow(false)}>
              Close
            </Button>
            {/* </Col>
          <Col className="align-self-end"> */}
            <Button variant="success" onClick={handleCloseWithSubmit} type="submit">
              Run
            </Button>
          </Col>
        </Row>
      </Modal.Footer>
    </Modal>
  );
};

const Dialog: React.FC<{
  accessStatus: AccessStatus;
  resetAccessStatus: () => void;
  show: boolean;
  setShow: React.Dispatch<any>;
  handleSubmit: () => void;
  setNotify: (notify: boolean) => void;
  notify: boolean;
}> = ({ accessStatus, resetAccessStatus, show, setShow, handleSubmit, setNotify, notify }) => {
  // pass new show and setShow so main run dialog is not closed.
  const [authShow, setAuthShow] = React.useState(true);
  if (accessStatus.can_run) {
    return (
      <RunDialog
        accessStatus={accessStatus}
        show={show}
        setShow={setShow}
        handleSubmit={handleSubmit}
        setNotify={setNotify}
        notify={notify}
      />
    );
  } else if (accessStatus.user_status === "anon") {
    // only consider showing AuthDialog if the run dialog is shown.
    return (
      <AuthDialog
        show={show ? authShow : false}
        setShow={setAuthShow}
        initialAction="sign-up"
        resetAccessStatus={resetAccessStatus}
      />
    );
  } else if (accessStatus.user_status === "profile") {
    return (
      <RequirePmtDialog
        accessStatus={accessStatus}
        show={show}
        setShow={setShow}
        handleSubmit={handleSubmit}
      />
    );
  }
};

export const RunModal: React.FC<{
  showModal: boolean;
  setShowModal: (showModal: boolean) => void;
  action: "Run" | "Fork and Run";
  handleSubmit: () => void;
  accessStatus: AccessStatus;
  resetAccessStatus: () => void;
  setNotify: (notify: boolean) => void;
  notify: boolean;
}> = ({
  showModal,
  setShowModal,
  action,
  handleSubmit,
  accessStatus,
  resetAccessStatus,
  setNotify,
  notify
}) => {
  let runbuttontext: string;
  if (!accessStatus.is_sponsored) {
    runbuttontext = `${action} ($${accessStatus.exp_cost})`;
  } else {
    runbuttontext = action;
  }

  return (
    <>
      <div className="card card-body card-outer">
        <Button
          variant="primary"
          onClick={() => setShowModal(true)}
          className="btn btn-block btn-success"
        >
          <b>{runbuttontext}</b>
        </Button>
      </div>
      <Dialog
        accessStatus={accessStatus}
        resetAccessStatus={resetAccessStatus}
        show={showModal}
        setShow={setShowModal}
        handleSubmit={handleSubmit}
        setNotify={setNotify}
        notify={notify}
      />
    </>
  );
};

export const AuthModal: React.FC<{ msg?: string }> = ({
  msg = "You must be logged in to run simulations."
}) => {
  const [show, setShow] = React.useState(true);

  const handleClose = () => setShow(false);
  const handleCloseWithRedirect = (e, redirectLink) => {
    e.preventDefault();
    setShow(false);
    window.location.replace(redirectLink);
  };
  return (
    <>
      <Modal show={show} onHide={handleClose}>
        <Modal.Header closeButton>
          <Modal.Title>Sign up</Modal.Title>
        </Modal.Header>
        <Modal.Body>{msg}</Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleClose}>
            Close
          </Button>
          <Button variant="secondary" onClick={e => handleCloseWithRedirect(e, "/users/login")}>
            <b>Sign in</b>
          </Button>
          <Button variant="success" onClick={e => handleCloseWithRedirect(e, "/users/signup")}>
            <b>Sign up</b>
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
};

export const UnsavedChangesModal: React.FC<{ handleClose: () => void }> = ({ handleClose }) => {
  const [show, setShow] = React.useState(true);
  const close = () => {
    setShow(false);
    handleClose();
  };

  return (
    <>
      <Modal show={show} onHide={close}>
        <Modal.Header closeButton>
          <Modal.Title>Unsaved Changes</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          You have unsaved changes in the inputs form. You must create a new simulation to get new
          outputs corresponding to these changes.
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-primary" onClick={close}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
};
