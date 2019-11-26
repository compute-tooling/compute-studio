import { Button, Modal, Collapse } from "react-bootstrap";
import * as React from "react";
import ReactLoading from "react-loading";

import { LoginForm, SignupForm } from "./AuthForms";
import axios from "axios";
import { AccessStatus } from "./types";


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
}

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
          The models are offered for free, but you pay for the computational
          resources used to run them. The prices are equal to Google Cloud
          Platform compute pricing, subject to costing at least one penny
          for a single run.
        <ul>
            <li>The price per hour of a server running this model is: ${`${accessStatus.server_cost}`}/hour.</li>
            <li>The expected time required for a single run of this model is: {`${accessStatus.exp_time}`} seconds.</li>
          </ul>
        </div>
      </Collapse>
    </>
  );
}

export const RequireLoginDialog: React.FC<{
  accessStatus: AccessStatus,
  show: boolean,
  setShow?: React.Dispatch<any>,
  handleSubmit: () => void
}> = ({ accessStatus, show, setShow, handleSubmit }) => {
  const [authenticated, setAuthStatus] = React.useState(false);
  const [hasSubmitted, setHasSubmitted] = React.useState(false);
  const [newDialog, updateNewDialog] = React.useState(null);
  const [isLogIn, setIsLogIn] = React.useState(true);
  const getVariant = (isLogIn: boolean) => isLogIn ? "outline-primary" : "outline-success"
  if (authenticated && !hasSubmitted) {
    axios.get(
      accessStatus.api_url
    ).then(resp => {
      let accessStatus = resp.data;
      let dialog = <Dialog accessStatus={accessStatus} show={show} setShow={null} handleSubmit={handleSubmit} />
      updateNewDialog(dialog);
    });
    setHasSubmitted(true);
  }
  if (newDialog !== null) {
    return newDialog;
  }

  return (
    <Modal show={show} onHide={() => setShow(false)}>
      <Modal.Header closeButton>
        <Modal.Title>You must be logged in to run simulations.</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <div className="mt-2" >
          {isLogIn ?
            <LoginForm setAuthStatus={setAuthStatus} />
            :
            <SignupForm setAuthStatus={setAuthStatus} />
          }
        </div>
        <Button className="mt-3" variant={getVariant(isLogIn)} onClick={() => setIsLogIn(!isLogIn)} >{!isLogIn ? "Log in" : "Sign up"}</Button>
      </Modal.Body>

      <Modal.Footer>
        <Button variant="outline-secondary" onClick={() => setShow(false)}>
          Close
        </Button>
      </Modal.Footer>
    </Modal >
  );
}

const RequirePmtDialog: React.FC<{
  accessStatus: AccessStatus,
  show: boolean,
  setShow?: React.Dispatch<any>,
  handleSubmit: () => void
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
        <Button
          variant="success"
          onClick={e => handleCloseWithRedirect(e, "/billing/update/")}
        >
          <b>Add payment method</b>
        </Button>
      </Modal.Footer>
    </Modal >
  );
}

const RunDialog: React.FC<{
  accessStatus: AccessStatus,
  show: boolean,
  setShow?: React.Dispatch<any>,
  handleSubmit: () => void
}> = ({ accessStatus, show, setShow, handleSubmit }) => {
  const handleCloseWithSubmit = () => {
    setShow(false);
    handleSubmit();
  };

  let body;
  if (accessStatus.is_sponsored) {
    body = <Modal.Body> This model's simulations are sponsored and thus, are free for you.</Modal.Body>;
  } else {
    body = (
      <Modal.Body>
        <p>This simulation will cost ${`${accessStatus.exp_cost}`}. You will be billed at the end of the monthly billing period.</p>
        <PricingInfoCollapse accessStatus={accessStatus} />
      </Modal.Body>
    );
  }

  return (
    <Modal show={show} onHide={() => setShow(false)}>
      <Modal.Header closeButton>
        <Modal.Title>
          Are you sure that you want to run this simulation?
    </Modal.Title>
      </Modal.Header>
      {body}
      <Modal.Footer>
        <Button variant="secondary" onClick={() => setShow(false)}>
          Close
    </Button>
        <Button
          variant="success"
          onClick={handleCloseWithSubmit}
          type="submit"
        >
          Run simulation
    </Button>
      </Modal.Footer>
    </Modal>
  );
}

const Dialog: React.FC<{
  accessStatus: AccessStatus,
  show: boolean,
  setShow?: React.Dispatch<any>,
  handleSubmit: () => void
}> = ({ accessStatus, show, setShow, handleSubmit }) => {
  if (setShow == null) {
    [show, setShow] = React.useState(show);
  }
  if (accessStatus.can_run) {
    return <RunDialog accessStatus={accessStatus} show={show} setShow={setShow} handleSubmit={handleSubmit} />;
  } else if (accessStatus.user_status === "anon") {
    return <RequireLoginDialog accessStatus={accessStatus} show={show} setShow={setShow} handleSubmit={handleSubmit} />;
  } else if (accessStatus.user_status === "profile") {
    return <RequirePmtDialog accessStatus={accessStatus} show={show} setShow={setShow} handleSubmit={handleSubmit} />
  }
}


export const RunModal: React.FC<{ handleSubmit: () => void, accessStatus: AccessStatus }> = ({ handleSubmit, accessStatus }) => {
  const [show, setShow] = React.useState(false);

  let runbuttontext: string;
  if (!accessStatus.is_sponsored) {
    runbuttontext = `Run ($${accessStatus.exp_cost})`;
  } else {
    runbuttontext = "Run";
  }

  return (
    <>
      <div className="card card-body card-outer">
        <Button
          variant="primary"
          onClick={() => setShow(true)}
          className="btn btn-block btn-success"
        >
          <b>{runbuttontext}</b>
        </Button>
      </div>
      <Dialog accessStatus={accessStatus} show={show} setShow={setShow} handleSubmit={handleSubmit} />
    </>
  );
};

export const AuthModal: React.FC<{ msg?: string }> = ({ msg = "You must be logged in to run simulations." }) => {
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
          <Button
            variant="secondary"
            onClick={e => handleCloseWithRedirect(e, "/users/login")}
          >
            <b>Log in</b>
          </Button>
          <Button
            variant="success"
            onClick={e => handleCloseWithRedirect(e, "/users/signup")}
          >
            <b>Sign up</b>
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
};
