import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import ReactLoading from "react-loading";
import axios from "axios";
import * as yup from "yup";

import ErrorBoundary from "../ErrorBoundary";
import { RolePerms } from "../roles";
import API from "./API";
import { default as SimAPI } from "../Simulation/API";
import { MiniSimulation, Project, Simulation, RemoteOutputs, AccessStatus } from "../types";
import moment = require("moment");
import { Button, Row, Col, Dropdown, Modal, Card, Tab, Nav } from "react-bootstrap";
import { Tip, FocusableCard } from "../components";
import { Formik, Field, ErrorMessage, FormikProps } from "formik";
import { Message } from "../fields";
import {
  saveCollaborators,
  CollaboratorValues,
  CollaborationModal
} from "../Simulation/collaborators";

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
  accessStatus: AccessStatus;
}

const Model: React.FC<{ model: Project; index: number }> = ({ model, index }) => {
  let margin;
  if (index === 0) {
    margin = "mb-2";
  } else {
    margin = "my-2";
  }

  let simCountEl;
  if (model.sim_count === 0) {
    if (!["live", "updating"].includes(model.status)) {
      simCountEl = (
        <a className="btn btn-outline-success btn-sm" href={`/${model.owner}/${model.title}/new/`}>
          Create the first simulation
        </a>
      );
    } else {
      simCountEl = null;
    }
  } else if (model.sim_count === undefined) {
    simCountEl = null;
  } else {
    simCountEl = (
      <p>
        {model.sim_count}
        <span className="text-muted"> simulations created by </span>
        {model.user_count}
        <span className="text-muted">{model.user_count > 1 ? " users" : " user"}</span>
      </p>
    );
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
          <Col className="col-sm-8">
            <Card.Title>
              <h5>{`${model.owner}/${model.title}`}</h5>
            </Card.Title>
            <Card.Subtitle className="text-muted" onClick={e => e.stopPropagation()}>
              <h6>{model.oneliner}</h6>
            </Card.Subtitle>
            {model.version ? (
              <Row className="justify-content-start">
                <Col>
                  <p>
                    <span className="text-muted">Version: </span>
                    {model.version}
                  </p>
                </Col>
              </Row>
            ) : null}
          </Col>
          <Col className="col-sm-4">
            <Row className="w-100 justify-content-start">
              {<Col className="col-3 align-self-center">{modelStatus(model.status)}</Col>}
              {model.has_write_access ? (
                <Col className="col-3 align-self-center">
                  <Tip id="edit-widget" tip="Click to edit">
                    <a className="color-inherit" href={`/${model.owner}/${model.title}/detail/`}>
                      <i className="fas fa-edit ml-2 hover-blue" style={{ fontSize: "1.4rem" }}></i>
                    </a>
                  </Tip>
                </Col>
              ) : null}
            </Row>
            {simCountEl ? (
              <Row className="w-100 justify-content-start mt-1">
                <Col>{simCountEl}</Col>
              </Row>
            ) : null}
          </Col>
        </Row>
      </Card.Body>
    </FocusableCard>
  );
};

const ModelFeed: React.FC<{ models: Array<Project> }> = ({ models }) => {
  return (
    <div className="container-fluid px-0">
      {models.map((model, ix) => (
        <Model model={model} key={`${model.owner}/${model.title}`} index={ix} />
      ))}
      <div className="container-fluid text-center my-2">
        <a className="btn btn-success" href="/publish/">
          <strong>Publish a new model</strong>
        </a>
      </div>
    </div>
  );
};

const Sim: React.FC<{ initMiniSim: MiniSimulation; index: number; accessStatus: AccessStatus }> = ({
  initMiniSim,
  index,
  accessStatus
}) => {
  const [miniSim, setMiniSim] = React.useState(initMiniSim);
  const [remoteSim, setRemoteSim] = React.useState(null as Simulation<RemoteOutputs> | null);
  const [editTitle, setEditTitle] = React.useState(false);
  const [showCollabModal, setShowCollabModal] = React.useState(false);
  const [owner, title] = miniSim.project.split("/");
  const simapi = new SimAPI(owner, title, miniSim.model_pk.toString());
  const resetRemoteSim = () => {
    return simapi.getRemoteOutputs().then(remoteSim => {
      setRemoteSim(remoteSim);
    });
  };

  const handleShowCollabModal = (show: boolean) => {
    if (show && !!remoteSim) {
      setShowCollabModal(true);
    } else if (show && !remoteSim) {
      resetRemoteSim().then(() => setShowCollabModal(true));
    } else {
      setShowCollabModal(false);
    }
  };

  let simLink;
  if (miniSim.status === "STARTED") {
    simLink = `${miniSim.gui_url}edit/`;
  } else {
    simLink = miniSim.gui_url;
  }
  let margin;
  if (index === 0) {
    margin = "mb-2";
  } else {
    margin = "my-2";
  }
  return (
    <Formik
      initialValues={{
        title: miniSim.title,
        is_public: miniSim.is_public,
        author: { add: { username: "", msg: "" }, remove: { username: "" } },
        access: { read: { grant: { username: "", msg: "" }, remove: { username: "" } } }
      }}
      validationSchema={yup.object().shape({ title: yup.string(), is_public: yup.boolean() })}
      onSubmit={(values, actions) => {
        let formdata = new FormData();
        for (const field in values) {
          if (values[field]) formdata.append(field, values[field]);
        }
        actions.setStatus({ collaboratorLimit: null });
        saveCollaborators(simapi, values, resetRemoteSim)
          .then(() =>
            simapi
              .putDescription(formdata)
              .then(newMiniSim => {
                setMiniSim(prevSim => ({
                  ...prevSim,
                  title: newMiniSim.title,
                  is_public: newMiniSim.is_public
                }));
                resetRemoteSim();
              })
              .catch(error => {
                if (error.response.status == 400 && error.response.data.collaborators) {
                  resetRemoteSim().then(() => {
                    actions.setStatus({
                      collaboratorLimit: error.response.data.collaborators
                    });
                    setShowCollabModal(true);
                  });
                }
              })
          )
          .catch(error => {
            if (error.response.status == 400 && error.response.data.collaborators) {
              resetRemoteSim().then(() => {
                actions.setStatus({
                  collaboratorLimit: error.response.data.collaborators
                });
                setShowCollabModal(true);
              });
            }
          })
          .finally(() => actions.setSubmitting(false));
      }}
    >
      {(props: FormikProps<{ title: string; is_public: boolean } & CollaboratorValues>) => (
        <>
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
                        props.handleSubmit(e);
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
                      props.handleSubmit();
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
                <Col className="col-md-9">
                  <Card.Title>
                    <h5>{miniSim.title}</h5>
                  </Card.Title>
                  <Card.Subtitle className="text-muted" onClick={e => e.stopPropagation()}>
                    <h6 style={{ whiteSpace: "nowrap" }}>
                      <a href={miniSim.project} className="color-inherit">
                        {miniSim.project}
                      </a>
                      <span className="ml-1">#{miniSim.model_pk} </span>
                    </h6>
                  </Card.Subtitle>
                </Col>
                {/* right half */}
                <Col className="col-md-3">
                  <Row className="w-100 justify-content-start">
                    <Col className="col-auto align-self-center">{simStatus(miniSim.status)}</Col>
                    <Col className="col-auto align-self-center">
                      <Tip id="public_or_private" tip={miniSim.is_public ? "Public" : "Private"}>
                        {miniSim.is_public ? (
                          <i className="fas fa-lock-open"></i>
                        ) : (
                          <i className="fas fa-lock"></i>
                        )}
                      </Tip>
                    </Col>
                    {RolePerms.hasAdminAccess(miniSim) ? (
                      <Col className="col-auto align-self-center">
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
                                handleShowCollabModal(true);
                              }}
                            >
                              Share
                            </Dropdown.Item>
                          </Dropdown.Menu>
                        </Dropdown>
                      </Col>
                    ) : null}
                  </Row>
                  <Row className="w-100 justify-content-start">
                    <Col>
                      <Tip
                        id="sim-creation-date"
                        tip={moment(miniSim.creation_date).format("MMMM Do YYYY, h:mm:ss a")}
                        placement="bottom"
                      >
                        <span className="text-muted" style={{ whiteSpace: "nowrap" }}>
                          {moment(miniSim.creation_date).fromNow()}
                        </span>
                      </Tip>
                    </Col>
                  </Row>
                </Col>
              </Row>
            </Card.Body>
          </FocusableCard>
          {remoteSim ? (
            <CollaborationModal
              api={simapi}
              user={accessStatus.username}
              remoteSim={remoteSim}
              formikProps={props}
              plan={accessStatus.plan.name}
              show={showCollabModal}
              setShow={setShowCollabModal}
            />
          ) : null}
        </>
      )}
    </Formik>
  );
};

const SimFeed: React.FC<{ sims: Array<MiniSimulation>; accessStatus: AccessStatus }> = ({
  sims,
  accessStatus
}) => {
  if (sims.length > 0) {
    return (
      <div className="container-fluid px-0">
        {sims.map((sim, ix) => (
          <Sim
            initMiniSim={sim}
            key={`${sim.project}#${sim.model_pk}`}
            index={ix}
            accessStatus={accessStatus}
          />
        ))}
      </div>
    );
  } else {
    return (
      <div className="container-fluid px-0">
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
        className={`p-0 ${ix > 0 ? "border-top-0" : ""} ${ix >= 3 ? "d-none d-sm-block" : ""}`}
        style={{ borderRadius: 0 }}
        onClick={() => (window.location.href = `/${model.owner}/${model.title}/`)}
      >
        <Card.Body>
          <Card.Title>
            <Tip id="new_simulation" tip="Create new simulation">
              <h6 onClick={e => e.stopPropagation()}>
                <a href={`/${model.owner}/${model.title}/new/`}>
                  {`${model.owner}/${model.title}`}{" "}
                  <i className="fas fa-plus-circle text-success"></i>
                </a>
              </h6>
            </Tip>
          </Card.Title>
          <Card.Subtitle className="text-muted d-none d-sm-none d-md-block">
            {model.oneliner}
          </Card.Subtitle>
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
  <Dropdown drop="left">
    <Dropdown.Toggle
      variant="link"
      style={{ border: 0 }}
      id="dropdown-sort"
      className="color-inherit p-0"
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
      homeTab: "sims",
      accessStatus: null
    };

    this.loadNextSimulations = this.loadNextSimulations.bind(this);
    this.updateOrder = this.updateOrder.bind(this);
  }

  componentDidMount() {
    this.api.getAccessStatus().then(accessStatus => {
      this.setState({ accessStatus: accessStatus });
    });
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
            <SimFeed sims={sims} accessStatus={this.state.accessStatus} />
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
      <Tab.Container
        id="home-tabs"
        defaultActiveKey={this.state.homeTab}
        transition={false}
        activeKey={this.state.homeTab}
        onSelect={(homeTab: "sims" | "models") => {
          if (homeTab) this.setState({ homeTab: homeTab });
        }}
      >
        <Row className="w-100 px-0 m-0 justify-content-between mb-3 d-flex flex-md-row">
          <Col
            className={`col-md-auto ${this.api.username ? "" : " offset-md-3"} align-self-center`}
          >
            <Nav variant="pills" className="d-flex d-sm-block">
              <Row className="flex-1">
                <Col className="p-0 align-self-center">
                  <Nav.Item className="left-nav-item text-center sub-nav-item flex-2">
                    <Nav.Link
                      className="border"
                      eventKey="sims"
                      style={{ fontSize: "15px", fontWeight: 600 }}
                    >
                      Simulations
                    </Nav.Link>
                  </Nav.Item>
                </Col>
                <Col className="p-0 align-self-center">
                  <Nav.Item className="right-nav-item text-center sub-nav-item flex-1">
                    <Nav.Link
                      className="border"
                      eventKey="models"
                      style={{ fontSize: "15px", fontWeight: 600 }}
                    >
                      Models
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
          <Row className="w-100 m-0">
            <Col className="col-md-3 pl-0 mobile-pr-0 mb-3">
              {recentModels ? <RecentModelsPanel recentModels={recentModels} /> : null}
            </Col>
            <Col className="col-md-9 px-0">{feed}</Col>
          </Row>
        ) : (
          <Row className="w-100 m-0">
            <Col className="p-0">{feed}</Col>
          </Row>
        )}
      </Tab.Container>
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
        <Tip id="sim-status" tip="Staging">
          <i className="fas fa-rocket text-primary"></i>
        </Tip>
      );
    case "PENDING":
      return (
        <Tip id="sim-status" tip="Running">
          <i className="fas fa-clock text-warning"></i>
        </Tip>
      );
    case "SUCCESS":
      return (
        <Tip id="sim-status" tip="Success">
          <i className="fas fa-check-circle text-success"></i>
        </Tip>
      );
    case "FAIL":
      return (
        <Tip id="sim-status" tip="Fail">
          <i className="fas fa-exclamation-circle text-danger"></i>
        </Tip>
      );
    case "WORKER_FAILURE":
      return (
        <Tip id="sim-status" tip="Worker failure">
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
    case "updating":
      return (
        <Tip id="live" tip="This model is live.">
          <Button className="btn-sm btn-outline-success">live</Button>
        </Tip>
      );
    case "pending":
      return (
        <Tip id="staging" tip="This model is not live right now.">
          <Button className="btn-sm btn-outline-primary">staging</Button>
        </Tip>
      );
    default:
      return (
        <Tip id="staging" tip="This model is not live right now.">
          <Button className="btn-sm btn-outline-primary">staging</Button>
        </Tip>
      );
  }
};
