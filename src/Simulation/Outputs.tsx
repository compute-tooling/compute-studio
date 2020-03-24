import * as React from "react";
import ReactLoading from "react-loading";
import {
  Card,
  Row,
  Col,
  OverlayTrigger,
  Tooltip,
  Modal,
  Button,
  ProgressBar
} from "react-bootstrap";
import * as moment from "moment";
import { RemoteOutputs, Outputs, Simulation, Output, TableOutput, BokehOutput } from "../types";
import { imgDims } from "../utils";
import API from "./API";
import { NotifyOnCompletion } from "./notify";
import { RolePerms } from "../roles";

import { lt as semverlt } from "semver";

interface OutputsProps {
  api: API;
  remoteSim?: Simulation<RemoteOutputs>;
  sim?: Simulation<Outputs>;
  setNotifyOnCompletion?: (notify: boolean) => void;
}

type OutputsState = Readonly<{}>;

const TableComponent: React.FC<{ output: TableOutput }> = ({ output }) => (
  <div
    dangerouslySetInnerHTML={{ __html: output.data }} // needs to be sanitized somehow.
    className="card publish markdown"
  />
);

const BokehComponent: React.FC<{ output: BokehOutput }> = ({ output }) => {
  // @ts-ignore
  let bokeh = window.Bokeh200;
  // @ts-ignore
  if (semverlt(output.data.doc.version, "2.0.0")) {
    // @ts-ignore
    bokeh = window.Bokeh140;
  }
  console.log("bokeh", bokeh);
  // @ts-ignore
  bokeh.embed.embed_item(output.data, output.id);
  return <div id={output.id} data-root-id={output.id} className="bk-root"></div>;
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
    case "PNG":
      el = <img src={`data:image/png;base64, ${output.data}`} />;
      break;
    case "JPEG":
      el = <img src={`data:image/jpeg;base64, ${output.data}`} />;
      break;
    default:
      el = <div dangerouslySetInnerHTML={{ __html: output.data }} />;
  }

  return (
    <>
      <Button variant="outline-light" style={{ border: 0 }} onClick={() => setShow(true)}>
        {children}
      </Button>
      <Modal show={show} onHide={() => setShow(false)} size="xl" className="output-modal">
        <Modal.Header closeButton>
          <Modal.Title>{output.title}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Card style={{ backgroundColor: "white" }}>
            <Card.Body
              className={`d-flex ${
                window.innerWidth < 992 ? "justify-content-left" : "justify-content-center"
              }`}
              style={{ overflow: "auto" }}
            >
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

const Pending: React.FC<{
  eta?: number;
  originalEta?: number;
  notify?: boolean;
  setNotify?: (notify: boolean) => void;
  showNotify?: boolean;
}> = ({ eta, originalEta, notify, setNotify, showNotify }) => {
  let el;
  if (eta !== null && originalEta !== null) {
    let percent = 100 * (1 - eta / originalEta);
    el = (
      <div>
        <Card.Title>
          <h3 className="text-center">
            Estimated time remaining: {moment.duration(eta, "seconds").humanize()}
          </h3>
          {showNotify ? (
            <div className="text-center">
              <NotifyOnCompletion notify={notify} setNotify={setNotify} />
            </div>
          ) : null}
        </Card.Title>
        <ProgressBar
          className="mt-5 mb-5"
          now={percent}
          style={{ height: "1.8rem" }}
          label={`${percent}%`}
          srOnly
          animated
        />
      </div>
    );
  } else {
    el = (
      <div className="d-flex justify-content-center">
        <ReactLoading type="spokes" color="#2b2c2d" />
      </div>
    );
  }
  return (
    <Card className="card-outer">
      <Card className="card-inner">
        <Card.Body>{el}</Card.Body>
      </Card>
    </Card>
  );
};

const Traceback: React.FC<{ remoteSim: Simulation<RemoteOutputs> }> = ({ remoteSim }) => (
  <Card className="card-outer">
    <Card className="card-inner">
      <Card.Body>
        <Card.Title>
          <h2>Your calculation failed. You may re-enter your parameters and try again.</h2>
        </Card.Title>
        <p className="lead">
          Compute Studio developers have already been notified about this failure. You are welcome
          to email me at <a href="mailto:hank@compute.studio">hank@compute.studio</a> if you would
          like to get in touch about this error.
        </p>
        <h4>Traceback:</h4>
        <pre>
          <code>{remoteSim.traceback}</code>
        </pre>
      </Card.Body>
    </Card>
  </Card>
);

const NewSimulation: React.FC<{}> = () => (
  <Card className="card-outer">
    <Card className="card-inner">
      <Card.Body>
        <Card.Title>
          <h2>You have not run your simulation yet.</h2>
        </Card.Title>
      </Card.Body>
    </Card>
  </Card>
);

const V0Simulation: React.FC<{ remoteSim: Simulation<RemoteOutputs> }> = ({ remoteSim }) => {
  let project = remoteSim.project;
  let { model_version, gui_url } = remoteSim;
  let creation_date = moment(remoteSim.creation_date).format("MMMM Do YYYY, h:mm:ss a");

  return (
    <Card>
      <Card.Body>
        <p>
          These results were generated by {project.title} on {creation_date} using {model_version}.
          Since the outputs data format has been updated since this simulation was created, they
          must be viewed on the outputs page hosted at this link: <a href={gui_url}>{gui_url}</a>.
        </p>
        <div className="text-center">
          <Button variant="success" href={gui_url}>
            {" "}
            Click to View Results
          </Button>
        </div>
      </Card.Body>
    </Card>
  );
};

export default class OutputsComponent extends React.Component<OutputsProps, OutputsState> {
  constructor(props) {
    super(props);
  }

  render() {
    let { api, remoteSim, sim } = this.props;

    if (api.modelpk !== remoteSim?.model_pk.toString()) {
      return <Pending />;
    } else if (!api.modelpk || remoteSim?.status === "STARTED") {
      return <NewSimulation />;
    } else if (!remoteSim) {
      return <Pending />;
    } else if (remoteSim?.status === "PENDING") {
      return (
        <Pending
          eta={remoteSim.eta}
          originalEta={remoteSim.original_eta}
          showNotify={RolePerms.hasWriteAccess(remoteSim)}
          notify={remoteSim.notify_on_completion}
          setNotify={this.props.setNotifyOnCompletion}
        />
      );
    } else if (remoteSim.traceback || sim?.traceback) {
      return <Traceback remoteSim={remoteSim} />;
    } else if (remoteSim?.outputs_version === "v0") {
      return <V0Simulation remoteSim={remoteSim} />;
    }

    let creation_date = moment(remoteSim.creation_date).format("MMMM Do YYYY, h:mm:ss a");
    let model_version = remoteSim.model_version;
    let project = remoteSim.project;
    let remoteOutputs = remoteSim.outputs.outputs;

    let outputs: Outputs = null;
    if (sim) {
      outputs = sim.outputs;
    }

    return (
      <Card className="card-outer" style={{ overflow: "auto" }}>
        <Card className="card-inner">
          <Card.Body>
            <p className="lead">
              {`These results were generated by ${project.title} on ${creation_date} using ${model_version}.`}
            </p>
            <Row className="align-items-center">
              {remoteOutputs.renderable.outputs.map((remoteOutput, ix) => {
                let media_type = remoteOutput.media_type;
                let output: TableOutput | BokehOutput | any;
                if (outputs) {
                  switch (media_type) {
                    case "table":
                      output = outputs.renderable[ix];
                      break;
                    case "bokeh":
                      output = outputs.renderable[ix];
                      break;
                    default:
                      output = outputs.renderable[ix];
                  }
                }

                let [width, height] = imgDims(remoteOutput.screenshot);
                width = width ? width : 500;
                height = height ? height : 500;
                return (
                  <Col
                    className="align-self-center"
                    style={{ margin: "1rem", maxWidth: width }}
                    key={`output-${ix}`}
                  >
                    <OverlayTrigger
                      trigger={["hover", "click"]}
                      overlay={<Tooltip id={`${ix}-tooltip`}>{remoteOutput.title}</Tooltip>}
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
            <Row className="text-center">
              <Col>
                <a
                  href={`/${project.owner}/${project.title}/${remoteSim.model_pk}/download/`}
                  className="btn btn-lg btn-match-nav"
                >
                  Download Results
                </a>
              </Col>
            </Row>
          </Card.Body>
        </Card>
      </Card>
    );
  }
}
