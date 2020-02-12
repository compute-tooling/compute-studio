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
import { Button, Row, Col, Dropdown, Modal, Card, Tab, Nav } from "react-bootstrap";
import { Tip, FocusableCard } from "../components";
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
  simFeed?: {
    count: number;
    next?: string;
    previous: string;
    results: Array<MiniSimulation>;
  };
  modelFeed?: {
    count: number;
    next?: string;
    previous: string;
    results: Array<Project>;
  };
  loading: boolean;
  ordering?: Array<"project__owner" | "project__title" | "creation_date">;
  recentModels?: Array<Project>;
  homeTab: "sims" | "models";
}

const Model: React.FC<{ model: Project; index: number }> = ({ model, index }) => {
  let margin;
  if (index === 0) {
    margin = "mb-2";
  } else {
    margin = "my-2";
  }

  return (
    <FocusableCard
      className={`${margin} border p-0`}
      onClick={() => {
        window.location.href = `/${model.owner}/${model.title}/`;
      }}
    >
      <Card.Body>
        <Row className="w-100">
          <Col className="col-9">
            <Card.Title>
              <h5>{`${model.owner}/${model.title}`}</h5>
            </Card.Title>
            <Card.Subtitle className="text-muted" onClick={e => e.stopPropagation()}>
              <h6>{model.oneliner}</h6>
            </Card.Subtitle>
          </Col>
          <Col className="col-3">
            <p>Count: {model.sim_count}</p>
          </Col>
        </Row>
      </Card.Body>
    </FocusableCard>
  );
};

const ModelFeed: React.FC<{ models: Array<Project> }> = ({ models }) => {
  return (
    <div className="container-fluid" style={{ paddingLeft: 0 }}>
      {models.map((model, ix) => (
        <Model model={model} key={`${model.owner}/${model.title}`} index={ix} />
      ))}
      <div className="container-fluid text-center my-2">
        <a className="btn btn-success" href="/publish/">
          Publish a new model <i className="fas fa-plus ml-1"></i>
        </a>
      </div>
    </div>
  );
};

const Sim: React.FC<{ initSim: MiniSimulation; index: number }> = ({ initSim, index }) => {
  let [sim, setSim] = React.useState(initSim);
  let [editTitle, setEditTitle] = React.useState(false);
  let simLink;
  if (sim.status === "STARTED") {
    simLink = `${sim.gui_url}edit/`;
  } else {
    simLink = sim.gui_url;
  }
  let margin;
  if (index === 0) {
    margin = "mb-2";
  } else {
    margin = "my-2";
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
        simapi.putDescription(formdata).then(() => {
          setSim(prevSim => ({ ...prevSim, title: values.title, is_public: values.is_public }));
        });
      }}
    >
      {({ values, setFieldValue, handleSubmit }) => (
        <FocusableCard
          className={`${margin} border p-0`}
          onClick={e => {
            window.location.href = simLink;
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
              <Col className="col-9">
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
              <Col className="col-3">
                <Row className="w-100 justify-content-start">
                  <Col className="col-3 align-self-center">{simStatus(sim.status)}</Col>
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
                          className="color-inherit caret-off"
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
                    <Tip
                      tip={moment(sim.creation_date).format("MMMM Do YYYY, h:mm:ss a")}
                      placement="bottom"
                    >
                      <span className="text-muted">{moment(sim.creation_date).fromNow()}</span>
                    </Tip>
                  </Col>
                </Row>
              </Col>
            </Row>
          </Card.Body>
        </FocusableCard>
      )}
    </Formik>
  );
};

const SimFeed: React.FC<{ sims: Array<MiniSimulation> }> = ({ sims }) => {
  if (sims.length > 0) {
    return (
      <div className="container-fluid" style={{ paddingLeft: 0 }}>
        {sims.map((sim, ix) => (
          <Sim initSim={sim} key={`${sim.project}#${sim.model_pk}`} index={ix} />
        ))}
      </div>
    );
  } else {
    return (
      <div className="container-fluid" style={{ paddingLeft: 0 }}>
        <Card>
          <Card.Body>
            <Card.Title>No simulations available!</Card.Title>
            <Card.Subtitle>
              Create a simulation by selecting one of the models in the Models dropdown.
            </Card.Subtitle>
          </Card.Body>
        </Card>
      </div>
    );
  }
};

const RecentModelsPanel: React.FC<{ recentModels: Array<Project> }> = ({ recentModels }) => (
  <>
    {recentModels.map((model, ix) => (
      <FocusableCard
        key={ix}
        className={`p-0 ${ix > 0 ? "border-top-0" : ""}`}
        style={{ borderRadius: 0 }}
        onClick={() => (window.location.href = `/${model.owner}/${model.title}/`)}
      >
        <Card.Body>
          <Card.Title>
            <Tip tip="Create new simulation">
              <h6 onClick={e => e.stopPropagation()}>
                <a href={`/${model.owner}/${model.title}/new/`}>
                  {`${model.owner}/${model.title}`}{" "}
                  <i className="fas fa-plus-circle text-success"></i>
                </a>
              </h6>
            </Tip>
          </Card.Title>
          <Card.Subtitle className="text-muted">{model.oneliner}</Card.Subtitle>
        </Card.Body>
      </FocusableCard>
    ))}
  </>
);

const LoadSimulationsButton: React.FC<{ loading: boolean; loadNextSimulations: () => void }> = ({
  loading,
  loadNextSimulations
}) => (
  <Row className="text-center">
    <Col>
      <Button variant="outline-primary" onClick={loadNextSimulations}>
        <div className="mb-0" style={{ display: "flex", justifyContent: "center" }}>
          {loading ? (
            <ReactLoading type="spokes" color="#2b2c2d" height={"20%"} width={"20%"} />
          ) : (
            "Load more"
          )}
        </div>
      </Button>
    </Col>
  </Row>
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
      className="caret-off color-inherit p-0"
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
      ordering: [],
      homeTab: "sims"
    };

    this.loadNextSimulations = this.loadNextSimulations.bind(this);
    this.updateOrder = this.updateOrder.bind(this);
  }

  componentDidMount() {
    this.api.initSimulations().then(simFeed => {
      this.setState({ simFeed: simFeed });
    });
    this.api.getModels().then(modelFeed => {
      this.setState({ modelFeed: modelFeed });
    });
    if (!this.api.username) {
      this.api.getRecentModels().then(recentModels => {
        this.setState({ recentModels: recentModels });
      });
    }
  }

  loadNextSimulations() {
    // check if we are at the end of the results.
    if (!this.state.simFeed?.next) return;
    this.setState({ loading: true });
    this.api.nextSimulations(this.state.simFeed.next).then(simFeed => {
      if (!simFeed.results.length) {
        this.setState({ loading: false });
      }
      this.setState(prevState => ({
        simFeed: { ...simFeed, results: [...prevState.simFeed.results, ...simFeed.results] },
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
    this.api.updateOrder(toggleOrder(this.state.ordering)).then(simFeed => {
      this.setState({ simFeed: simFeed, loading: false });
    });
  }

  render() {
    const { simFeed, modelFeed, recentModels } = this.state;
    if (!simFeed || !modelFeed) {
      return (
        <div className="d-flex justify-content-center">
          <ReactLoading type="spokes" color="#2b2c2d" />
        </div>
      );
    }
    const sims = simFeed.results;
    const models = modelFeed.results;
    const feed = (
      <>
        <Tab.Content>
          <Tab.Pane eventKey="sims">
            <SimFeed sims={sims} />
            {this.state.simFeed?.next ? (
              <LoadSimulationsButton
                loading={this.state.loading}
                loadNextSimulations={this.loadNextSimulations}
              />
            ) : null}
          </Tab.Pane>
        </Tab.Content>
        <Tab.Content>
          <Tab.Pane eventKey="models">
            <ModelFeed models={models} />
          </Tab.Pane>
        </Tab.Content>
      </>
    );

    return (
      <div className="container-fluid">
        <Tab.Container
          id="home-tabs"
          defaultActiveKey={this.state.homeTab}
          activeKey={this.state.homeTab}
          onSelect={(homeTab: "sims" | "models") => {
            if (homeTab) this.setState({ homeTab: homeTab });
          }}
        >
          <Row className="w-100 justify-content-between mb-3">
            <Col className={`col-4 ${this.api.username ? "" : "offset-md-3"} align-self-center`}>
              <Nav variant="pills">
                <Row className="w-100">
                  <Col className="p-0 align-self-center">
                    <Nav.Item className="left-nav-item text-center sub-nav-item">
                      <Nav.Link className="border" eventKey="sims">
                        {this.api.username ? `Simulations` : "My simulations"}
                      </Nav.Link>
                    </Nav.Item>
                  </Col>
                  <Col className="p-0 align-self-center">
                    <Nav.Item className="right-nav-item text-center sub-nav-item">
                      <Nav.Link className="border" eventKey="models">
                        {this.api.username ? `Models` : "My models"}
                      </Nav.Link>
                    </Nav.Item>
                  </Col>
                </Row>
              </Nav>
            </Col>
            {this.state.homeTab === "sims" ? (
              <Col className="col-1 align-self-center">
                <OrderingDropDown ordering={this.state.ordering} updateOrder={this.updateOrder} />
              </Col>
            ) : null}
          </Row>
          {!this.api.username ? (
            <Row className="w-100">
              <Col className="col-md-3 pl-0">
                {recentModels ? <RecentModelsPanel recentModels={recentModels} /> : null}
              </Col>
              <Col className="col-md-9 px-0">{feed}</Col>
            </Row>
          ) : (
            <Row className="w-100">
              <Col className="p-0">{feed}</Col>
            </Row>
          )}
        </Tab.Container>
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

const simStatus = (status: MiniSimulation["status"]) => {
  switch (status) {
    case "STARTED":
      return (
        <Tip tip="Staging">
          <i className="fas fa-rocket text-primary"></i>
        </Tip>
      );
    case "PENDING":
      return (
        <Tip tip="Running">
          <i className="fas fa-clock text-warning"></i>
        </Tip>
      );
    case "SUCCESS":
      return (
        <Tip tip="Success">
          <i className="fas fa-check-circle text-success"></i>
        </Tip>
      );
    case "FAIL":
      return (
        <Tip tip="Fail">
          <i className="fas fa-exclamation-circle text-danger"></i>
        </Tip>
      );
    case "WORKER_FAILURE":
      return (
        <Tip tip="Worker failure">
          <i className="fas fa-exclamation-circle text-danger"></i>
        </Tip>
      );
    default:
      return "";
  }
};

const modelStatus = (status: Project["status"]) => {
  switch (status) {
    case "live":
      // return "primary";
      return (
        <Tip tip="Live">
          <Button className="btn-success-outline btn-sm" />
        </Tip>
      );
    case "PENDING":
      // return "warning";
      return (
        <Tip tip="Pending">
          <i className="fas fa-spinner text-warning"></i>
        </Tip>
      );
    default:
      return (
        <Tip tip="Pending">
          <i className="fas fa-spinner text-warning"></i>
        </Tip>
      );
  }
};
