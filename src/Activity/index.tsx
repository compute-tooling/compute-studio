import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import ReactLoading from "react-loading";
import axios from "axios";
import * as yup from "yup";

import ErrorBoundary from "../ErrorBoundary";
import API from "./API";
import { default as SimAPI } from "../Simulation/API";
import { MiniSimulation, Project } from "../types";
import moment = require("moment");
import { Button, Row, Col, Dropdown, Modal, Card } from "react-bootstrap";
import { Tip } from "../components";
import { Formik, Field, ErrorMessage } from "formik";
import { Message } from "../fields";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const domContainer = document.querySelector("#activity-container");

interface URLProps {
  match: {
    params: {
      username?: string;
    };
  };
}

interface ActivityProps extends URLProps {}

interface ActivityState {
  feed?: {
    count: number;
    next: string;
    previous: string;
    results: Array<MiniSimulation>;
  };
  loading: boolean;
  ordering?: Array<"project__owner" | "project__title" | "creation_date">;
  recentModels?: Array<Project>;
}

const GridRow: React.FC<{ initSim: MiniSimulation; index: number }> = ({ initSim, index }) => {
  let [focus, setFocus] = React.useState(false);
  let [sim, setSim] = React.useState(initSim);
  let [editTitle, setEditTitle] = React.useState(false);
  let simLink;
  if (sim.status === "STARTED") {
    simLink = `${sim.gui_url}edit/`;
  } else {
    simLink = sim.gui_url;
  }
  let rowStyle: { [key: string]: any } = { borderRadius: "2px" };
  if (focus) {
    rowStyle = { ...rowStyle, backgroundColor: "rgb(245, 248, 250)", cursor: "pointer" };
  }
  let margin;
  if (index === 0) {
    margin = "mb-3";
  } else {
    margin = "my-3";
  }
  return (
    <Formik
      initialValues={{ title: sim.title, is_public: sim.is_public }}
      validationSchema={yup.object().shape({ title: yup.string(), is_public: yup.boolean() })}
      onSubmit={values => {
        let [owner, title] = sim.project.split("/");
        let simapi = new SimAPI(owner, title, sim.model_pk.toString());
        let formdata = new FormData();
        for (const field in values) {
          if (values[field]) formdata.append(field, values[field]);
        }
        simapi.putDescription(formdata).then(data => {
          setSim(prevSim => ({ ...prevSim, title: values.title, is_public: values.is_public }));
        });
      }}
    >
      {({ values, setFieldValue, handleSubmit }) => (
        <Card
          className={`${margin} border p-0`}
          style={rowStyle}
          onClick={e => {
            window.location.href = simLink;
          }}
          onMouseEnter={() => {
            setFocus(true);
          }}
          onMouseLeave={() => {
            setFocus(false);
          }}
        >
          <Card.Body>
            <Modal
              show={editTitle}
              onHide={() => setEditTitle(false)}
              onClick={e => e.stopPropagation()}
            >
              <Modal.Header closeButton>
                <Modal.Title>Rename Simulation</Modal.Title>
              </Modal.Header>
              <Modal.Body>
                <Field
                  name="title"
                  className="form-control"
                  onKeyPress={e => {
                    if (e.key === "Enter") {
                      handleSubmit(e);
                      setEditTitle(false);
                    }
                  }}
                />
                <ErrorMessage name="title" render={msg => <Message msg={msg} />} />
              </Modal.Body>
              <Modal.Footer>
                <Button
                  variant="outline-primary"
                  onClick={e => {
                    setEditTitle(false);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={e => {
                    handleSubmit();
                    setEditTitle(false);
                  }}
                >
                  Save
                </Button>
              </Modal.Footer>
            </Modal>
            {/* top level row for card */}
            <Row className="w-100">
              {/* left half */}
              <Col className="col-8">
                <Card.Title>
                  <h5>{sim.title}</h5>
                </Card.Title>
                <Card.Subtitle className="text-muted" onClick={e => e.stopPropagation()}>
                  <h6>
                    <a href={sim.project} className="color-inherit">
                      {sim.project}
                    </a>
                    <span className="ml-1">#{sim.model_pk} </span>
                  </h6>
                </Card.Subtitle>
              </Col>
              {/* right half */}
              <Col className="col-4">
                <Row className="w-100 justify-content-start">
                  <Col className="col-3 align-self-center">{status(sim.status)}</Col>
                  <Col className="col-3 align-self-center">
                    {sim.is_public ? (
                      <i className="fas fa-lock-open"></i>
                    ) : (
                      <i className="fas fa-lock"></i>
                    )}
                  </Col>
                  {sim.has_write_access ? (
                    <Col className="col-3 align-self-center">
                      <Dropdown onClick={e => e.stopPropagation()}>
                        <Dropdown.Toggle
                          id="dropdown-basic"
                          variant="link"
                          className="color-inherit"
                          style={{ border: 0 }}
                        >
                          <i className="fas fa-ellipsis-v"></i>
                        </Dropdown.Toggle>
                        <Dropdown.Menu>
                          <Dropdown.Item
                            key={0}
                            href=""
                            onClick={() => {
                              setEditTitle(true);
                            }}
                          >
                            Rename
                          </Dropdown.Item>
                          <Dropdown.Item
                            key={1}
                            href=""
                            onClick={() => {
                              setFieldValue("is_public", !values.is_public);
                              setTimeout(() => handleSubmit(), 0);
                            }}
                          >
                            Make {values.is_public ? "private" : "public"}
                          </Dropdown.Item>
                        </Dropdown.Menu>
                      </Dropdown>
                    </Col>
                  ) : null}
                </Row>
                <Row className="w-100 justify-content-start">
                  <Col>
                    <span className="text-muted">{moment(sim.creation_date).fromNow()}</span>
                  </Col>
                </Row>
              </Col>
            </Row>
          </Card.Body>
        </Card>
      )}
    </Formik>
  );
};

const Grid: React.FC<{ sims: Array<MiniSimulation> }> = ({ sims }) => {
  return (
    <div className="container-fluid">
      {sims.map((sim, ix) => (
        <GridRow initSim={sim} key={`${sim.project}#${sim.model_pk}`} index={ix} />
      ))}
    </div>
  );
};

const RecentModelsPanel: React.FC<{ recentModels: Array<Project> }> = ({ recentModels }) => (
  <>
    {recentModels.map((model, ix) => (
      <Card className={`p-0 ${ix > 0 ? "border-top-0" : ""}`} style={{ borderRadius: 0 }}>
        <Card.Body>
          <Card.Title>
            <Tip tip="Create new simulation">
              <h6>
                <a
                  // className="color-inherit"
                  href={`/${model.owner}/${model.title}/new/`}
                >
                  {`${model.owner}/${model.title}`}{" "}
                  <i className="fas fa-plus-circle text-success"></i>
                </a>
              </h6>
            </Tip>
          </Card.Title>
          <Card.Subtitle className="text-muted">{model.oneliner}</Card.Subtitle>
        </Card.Body>
      </Card>
    ))}
  </>
);

const OrderingDropDown: React.FC<{ ordering: Array<string>; updateOrder: (string) => void }> = ({
  ordering,
  updateOrder
}) => (
  <Dropdown>
    <Dropdown.Toggle
      variant="link"
      style={{ border: 0 }}
      id="dropdown-sort"
      className="caret-off color-inherit"
    >
      <i style={{ fontSize: "1.5rem" }} className="fas fa-sort"></i>
    </Dropdown.Toggle>
    <Dropdown.Menu>
      <Dropdown.Item
        key={0}
        active={ordering.includes("creation_date")}
        onClick={() => updateOrder("creation_date")}
      >
        Creation Date
      </Dropdown.Item>
      <Dropdown.Item
        key={1}
        active={ordering.includes("project__owner")}
        onClick={() => updateOrder("project__owner")}
      >
        Model Owner
      </Dropdown.Item>
      <Dropdown.Item
        key={2}
        active={ordering.includes("project__title")}
        onClick={() => updateOrder("project__title")}
      >
        Model Title
      </Dropdown.Item>
    </Dropdown.Menu>
  </Dropdown>
);

class Activity extends React.Component<ActivityProps, ActivityState> {
  api: API;
  constructor(props) {
    super(props);
    super(props);
    const { username } = this.props.match.params;
    this.api = new API(username);
    this.state = {
      loading: false,
      ordering: []
    };

    this.loadNextSimulations = this.loadNextSimulations.bind(this);
    this.updateOrder = this.updateOrder.bind(this);
  }

  componentDidMount() {
    this.api.initSimulations().then(feed => {
      this.setState({ feed });
    });
    if (!this.api.username) {
      this.api.getRecentModels().then(recentModels => {
        this.setState({ recentModels });
      });
    }
  }

  loadNextSimulations() {
    // check if we are at the end of the results.
    if (!this.state.feed?.next) return;
    this.setState({ loading: true });
    this.api.nextSimulations(this.state.feed.next).then(feed => {
      if (!feed.results.length) {
        this.setState({ loading: false });
      }
      this.setState(prevState => ({
        feed: { ...feed, results: [...prevState.feed.results, ...feed.results] },
        loading: false
      }));
    });
  }

  updateOrder(order: "project__owner" | "project__title" | "creation_date") {
    const toggleOrder = prevOrdering => {
      if (prevOrdering.includes(order)) {
        return prevOrdering.filter(prevOrder => prevOrder !== order);
      } else {
        return [order, ...prevOrdering];
      }
    };
    this.setState(prevState => ({
      ordering: toggleOrder(prevState.ordering),
      loading: true
    }));
    this.api.updateOrder(toggleOrder(this.state.ordering)).then(feed => {
      this.setState({ feed, loading: false });
    });
  }

  render() {
    const { feed } = this.state;
    if (!feed) {
      return (
        <div className="d-flex justify-content-center">
          <ReactLoading type="spokes" color="#2b2c2d" />
        </div>
      );
    }
    const sims = feed.results;
    const recentModels = this.state.recentModels;
    return (
      <div className="container-fluid">
        <Row className="w-100 justify-content-end">
          <Col className="col-1">
            <OrderingDropDown ordering={this.state.ordering} updateOrder={this.updateOrder} />
          </Col>
        </Row>
        {!this.api.username ? (
          <Row>
            <Col className="col-3">
              {recentModels ? <RecentModelsPanel recentModels={recentModels} /> : null}
            </Col>
            <Col className="col-9">
              <Grid sims={sims} />
            </Col>
          </Row>
        ) : (
          <Grid sims={sims} />
        )}
        {this.state.feed?.next ? (
          <Row className="text-center">
            <Col>
              <Button variant="outline-primary" onClick={this.loadNextSimulations}>
                <p className="mb-0" style={{ display: "flex", justifyContent: "center" }}>
                  {this.state.loading ? (
                    <ReactLoading type="spokes" color="#2b2c2d" height={"20%"} width={"20%"} />
                  ) : (
                    "Load more"
                  )}
                </p>
              </Button>
            </Col>
          </Row>
        ) : null}
      </div>
    );
  }
}

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route
        exact
        path="/"
        render={routeProps => (
          <ErrorBoundary>
            <Activity {...routeProps} />
          </ErrorBoundary>
        )}
      />
      <Route
        exact
        path="/:username/"
        render={routeProps => (
          <ErrorBoundary>
            <Activity {...routeProps} />
          </ErrorBoundary>
        )}
      />
    </Switch>
  </BrowserRouter>,
  domContainer
);

const status = (status: MiniSimulation["status"]) => {
  switch (status) {
    case "STARTED":
      // return "primary";
      return (
        <Tip tip="Started">
          <i className="fas fa-play-circle text-primary"></i>
        </Tip>
      );
    case "PENDING":
      // return "warning";
      return (
        <Tip tip="Pending">
          <i className="fas fa-spinner text-warning"></i>
        </Tip>
      );
    case "SUCCESS":
      // return "success";
      return (
        <Tip tip="Success">
          <i className="fas fa-check-circle text-success"></i>
        </Tip>
      );
    case "FAIL":
      // return "danger";
      return (
        <Tip tip="Fail">
          <i className="fas fa-exclamation-circle text-danger"></i>
        </Tip>
      );
    case "WORKER_FAILURE":
      // return "danger";
      return (
        <Tip tip="Worker failure">
          <i className="fas fa-exclamation-circle text-danger"></i>
        </Tip>
      );
    default:
      return "";
  }
};
