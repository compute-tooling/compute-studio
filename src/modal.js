import { Modal, Button } from "react-bootstrap";
import React from "react";
import ReactLoading from "react-loading";
import axios from "axios";

export class LoadingModal extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      show: true,
      setShow: true,
      status: "PENDING",
      inputs_url: this.props.inputs_url,
      sim_url: null,
    }
    this.handleClose = this.handleShow.bind(this);
    this.handleShow = this.handleShow.bind(this);
  }

  handleClose() {
    this.setState({ setShow: false, show: false });
  }
  handleShow() {
    this.setState({ setShow: true, show: true });
  }

  componentDidMount() {
    console.log("mounted", this.state.inputs_url);
    this.timer = setInterval(() => {
      axios
        .get(this.state.inputs_url)
        .then(response => {
          console.log("success");
          console.log(response);
          console.log("has simUrl");
          let simUrl = !!response.data.sim ? response.data.sim.gui_url : null;
          let status = response.data.status;
          let isPending = status === "PENDING";
          this.setState({
            status: status,
            setShow: isPending,
            show: isPending,
            simUrl: simUrl,
          });
          console.log("done");
        })
        .catch(error => {
          console.log(error);
        })
    },
      500
    );
  }

  componentWillUnmount() {
    console.log("unmounting???");
    clearInterval(this.timer);
  }

  render() {
    console.log("rendering modal")
    if (this.state.status != "PENDING" && this.state.simUrl) {
      window.location.replace(this.state.simUrl);
    }
    console.log(this.state);
    return (
      <div>
        <Modal show={this.state.show} onHide={this.handleClose}>
          <Modal.Header closeButton>
            <Modal.Title>Validating inputs...</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <div className="d-flex justify-content-center">
              <ReactLoading type="spokes" color="#28a745" />
            </div>
          </Modal.Body>
        </Modal>
      </div >
    );
  }
}

export const RunModal = ({ handleSubmit }) => {
  const [show, setShow] = React.useState(false);

  const handleClose = () => setShow(false);
  const handleShow = () => setShow(true);
  const handleCloseWithSubmit = () => {
    setShow(false);
    handleSubmit();
  }
  return (
    <>
      <div className="card card-body card-outer">
        <Button variant="primary" onClick={handleShow} className="btn btn-block btn-success">
          Run
         </Button>
      </div>
      <Modal show={show} onHide={handleClose}>
        <Modal.Header closeButton>
          <Modal.Title>Are you sure that you want to run this simulation?</Modal.Title>
        </Modal.Header>
        <Modal.Body>TODO: add info about sponsored or not.</Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleClose}>
            Close
          </Button>
          <Button variant="primary" onClick={handleCloseWithSubmit} type="submit" className="btn-block btn-success">
            <b>Run</b>
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
}
