import * as React from "react";
import ReactLoading from "react-loading";
import * as Bokeh from "bokehjs";
import {
  Card,
  Row,
  Col,
  OverlayTrigger,
  Tooltip,
  Modal,
  Button
} from "react-bootstrap";
import * as moment from "moment";
import {
  RemoteOutputs,
  Outputs,
  SimAPIData,
  Output,
  TableOutput,
  BokehOutput
} from "./types";

interface OutputsProps {
  fetchRemoteOutputs: () => Promise<SimAPIData<RemoteOutputs>>;
  fetchOutputs: () => Promise<SimAPIData<Outputs>>;
}

type OutputsState = Readonly<{
  remoteSim: SimAPIData<RemoteOutputs>;
  sim: SimAPIData<Outputs>;
}>;

const TableComponent: React.FC<{ output: TableOutput }> = ({ output }) => (
  <div
    dangerouslySetInnerHTML={{ __html: output.data }} // needs to be sanitized somehow.
    className="card publish markdown"
  />
);

const BokehComponent: React.FC<{ output: BokehOutput }> = ({ output }) => {
  // @ts-ignore
  window.Bokeh.embed.embed_item(output.data, output.id);
  return (
    <div id={output.id} data-root-id={output.id} className="bk-root"></div>
  );
};

const OutputModal: React.FC<{
  output: Output | BokehOutput | TableOutput;
  children: JSX.Element;
}> = ({ output, children }) => {
  const [show, setShow] = React.useState(false);

  let el;
  switch (output.media_type) {
    case "table":
      el = <TableComponent output={output as TableOutput} />;
      break;
    case "bokeh":
      console.log("bokeh", output);
      el = <BokehComponent output={output as BokehOutput} />;
      break;
    default:
      el = <div dangerouslySetInnerHTML={{ __html: output.data }} />;
  }

  return (
    <>
      <Button variant="outline-light" style={{ border: 0 }} onClick={() => setShow(true)}>
        {children}
      </Button>
      <Modal
        show={show}
        onHide={() => setShow(false)}
        size="xl"
        className="output-modal"
      >
        <Modal.Header closeButton>
          <Modal.Title>{output.title}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Card style={{ backgroundColor: "white" }} >
            <Card.Body className="d-flex justify-content-center" style={{ overflow: "auto" }}>
              {el}
            </Card.Body>
          </Card>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-primary" onClick={() => setShow(false)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
};


const Pending: React.FC<> = () => (
  <Card className="card-outer">
    <Card.Body>
      <div className="d-flex justify-content-center">
        <ReactLoading type="spokes" color="#2b2c2d" />
      </div>
    </Card.Body>
  </Card>
);


const Traceback: React.FC<{ remoteSim: SimAPIData<RemoteOutputs> }> = ({ remoteSim }) => (
  <Card className="card-outer">
    <Card className="card-inner">
      <Card.Body>
        <Card.Title><h2>Your calculation failed. You may re-enter your parameters and try again.</h2></Card.Title>
        <p className="lead">Compute Studio developers have already been notified about this failure. You are welcome to email me at <a href="mailto:hank@compute.studio">hank@compute.studio</a> if you would like to get in touch about this error.</p>
        <h4>Traceback:</h4>
        <pre>
          <code>
            {remoteSim.traceback}
          </code>
        </pre>
      </Card.Body>
    </Card>
  </Card>
);

export default class OutputsComponent extends React.Component<
  OutputsProps,
  OutputsState
  > {
  constructor(props) {
    super(props);
    this.state = {
      remoteSim: null,
      sim: null
    };
  }

  componentDidMount() {
    this.props.fetchRemoteOutputs().then(data => {
      this.setState({ remoteSim: data });
    });
    this.props.fetchOutputs().then(data => {
      this.setState({ sim: data });
    });
  }

  render() {
    let remoteSim = this.state.remoteSim;
    if (!remoteSim || (remoteSim && remoteSim.status === "PENDING")) {
      return <Pending />;
    } else if (remoteSim.traceback) {
      return <Traceback remoteSim={remoteSim} />;
    }
    let creation_date = moment(this.state.remoteSim.creation_date).format(
      "MMMM Do YYYY, h:mm:ss a"
    );
    let model_version = this.state.remoteSim.model_version;
    let project = this.state.remoteSim.project;
    let remoteOutputs = this.state.remoteSim.outputs.outputs;

    let outputs: Outputs = null;
    if (this.state.sim !== null) {
      outputs = this.state.sim.outputs;
      console.log("outputs", outputs);
    }
    return (
      <Card className="card-outer" style={{ overflow: "auto" }}>
        <Card className="card-inner">
          <Card.Body>
            <p className="lead">
              {`These results were generated by ${project.title} on ${creation_date} using ${model_version}.`}
            </p>
            <Row className="text-center">
              {remoteOutputs.renderable.outputs.map((remoteOutput, ix) => {
                let media_type = remoteOutput.media_type;
                let output: TableOutput | BokehOutput;
                if (outputs !== null && media_type == "table") {
                  output = outputs.renderable[ix];
                } else if (outputs !== null && media_type == "bokeh") {
                  output = outputs.renderable[ix];
                }
                let img = new Image();
                img.src = remoteOutput.screenshot;
                let [height, width] = [img.height, img.width];
                let factor = 1;
                if (height > width) {
                  factor = height / 600;
                } else {
                  factor = width / 600;
                }
                height = Math.floor(height / factor);
                width = Math.floor(width / factor);

                return (
                  <Col style={{ margin: "1rem", maxWidth: width }} key={`output-${ix}`}>
                    <OverlayTrigger
                      trigger={["hover", "click"]}
                      overlay={
                        <Tooltip id={`${ix}-tooltip`}>
                          {remoteOutput.title}
                        </Tooltip>
                      }
                    >
                      {outputs !== null ? (
                        <OutputModal output={output}>
                          <img
                            style={{ objectFit: "contain" }}
                            src={remoteOutput.screenshot}
                            alt={remoteOutput.title}
                            height={height}
                            width={width}
                          />
                        </OutputModal>
                      ) : (
                          <img
                            style={{ objectFit: "contain" }}
                            src={remoteOutput.screenshot}
                            alt={remoteOutput.title}
                            height={height}
                            width={width}
                          />
                        )}
                    </OverlayTrigger>
                  </Col>
                );
              })}
            </Row>
          </Card.Body>
        </Card>
      </Card>
    );
  }
}