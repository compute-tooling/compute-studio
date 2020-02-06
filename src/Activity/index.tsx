import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import ReactLoading from "react-loading";
import axios from "axios";

import ErrorBoundary from "../ErrorBoundary";
import API from "./API";
import { MiniSimulation } from "../types";
import moment = require("moment");
import { Button, Row, Col, Dropdown } from "react-bootstrap";
import { Tip } from "../components";

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
}

// Necessary to stop click on dropdown toggle from propagating up to the parent elements.
const CustomToggle = React.forwardRef<any, any>(({ children, onClick }, ref) => (
  <Button
    variant="link"
    style={{ border: 0, color: "inherit" }}
    href=""
    ref={ref}
    onClick={e => {
      e.stopPropagation();
      e.preventDefault();
      onClick(e);
    }}
  >
    {children}
  </Button>
));

const GridRow: React.FC<{ sim: MiniSimulation }> = ({ sim }) => {
  let [focus, setFocus] = React.useState(false);
  let simLink;
  if (sim.status === "STARTED") {
    simLink = `${sim.gui_url}edit/`;
  } else {
    simLink = sim.gui_url;
  }
  let rowStyle: { [key: string]: any } = { borderRadius: "20px" };
  if (focus) {
    rowStyle = { ...rowStyle, backgroundColor: "rgb(245, 248, 250)", cursor: "pointer" };
  }
  console.log(rowStyle);
  return (
    <Row
      className="justify-content-center my-4 border p-3"
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
      <Col className="col-3 text-truncate">{sim.title}</Col>
      <Col className="col-3">{sim.project}</Col>
      <Col className="col-1">#{sim.model_pk}</Col>
      <Col className="col-1">
        <a href={sim.gui_url}>{status(sim.status)}</a>
      </Col>
      <Col className="col-2 text-truncate">{moment(sim.creation_date).fromNow()}</Col>
      <Col className="col-1">
        {sim.is_public ? <i className="fas fa-lock-open"></i> : <i className="fas fa-lock"></i>}
      </Col>
      <Col className="col-1">
        <Dropdown>
          <Dropdown.Toggle id="dropdown-basic" as={CustomToggle}>
            <i className="fas fa-ellipsis-v"></i>
          </Dropdown.Toggle>
          <Dropdown.Menu>
            <Dropdown.Item key={0} href="">
              Rename
            </Dropdown.Item>
            <Dropdown.Item key={1} href="">
              Make {sim.is_public ? "private" : "public"}
            </Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown>
      </Col>
    </Row>
  );
};

const Grid: React.FC<{ sims: Array<MiniSimulation> }> = ({ sims }) => {
  return (
    <div className="container-fluid">
      {sims.map(sim => (
        <GridRow sim={sim} />
      ))}
    </div>
  );
};

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
  }

  loadNextSimulations() {
    // check if we are at the end of the results.
    if (!this.state.feed?.next) return;
    this.setState({ loading: true });
    this.api.nextSimulations(this.state.feed.next).then(feed => {
      if (!feed.results.length) {
        console.log("heyoooo");
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
    return (
      <div className="container-fluid">
        <Row className="w-100 justify-content-end">
          <Col className="col-1">
            <Dropdown>
              <Dropdown.Toggle
                variant="link"
                style={{ border: 0, color: "inherit" }}
                id="dropdown-sort"
                className="caret-off"
              >
                <i className="fas fa-sort"></i>
              </Dropdown.Toggle>
              <Dropdown.Menu>
                <Dropdown.Item
                  key={0}
                  active={this.state.ordering.includes("creation_date")}
                  onClick={() => this.updateOrder("creation_date")}
                >
                  Creation Date
                </Dropdown.Item>
                <Dropdown.Item
                  key={1}
                  active={this.state.ordering.includes("project__owner")}
                  onClick={() => this.updateOrder("project__owner")}
                >
                  Model Owner
                </Dropdown.Item>
                <Dropdown.Item
                  key={2}
                  active={this.state.ordering.includes("project__title")}
                  onClick={() => this.updateOrder("project__title")}
                >
                  Model Title
                </Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>
          </Col>
        </Row>
        <Grid sims={sims} />
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
