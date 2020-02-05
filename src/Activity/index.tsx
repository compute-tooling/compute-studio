import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import {
  useTable,
  useSortBy,
  ColumnInstance,
  TableHeaderProps,
  DefaultSortTypes
} from "react-table";
import ReactLoading from "react-loading";
import axios from "axios";

import ErrorBoundary from "../ErrorBoundary";
import API from "./API";
import { MiniSimulation } from "../types";
import moment = require("moment");
import { Button, Row, Col } from "react-bootstrap";

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
  sims?: Array<MiniSimulation>;
  loading: boolean;
}

interface ColumnInstanceExt extends ColumnInstance {
  getSortByToggleProps: () => TableHeaderProps;
  isSorted?: boolean;
  isSortedDesc?: boolean;
}

// const schema = yup.array().of(
//   yup.object().shape<MiniSimulation>({
//     api_url: yup.string(),
//     creation_date: yup.date(),
//     gui_url: yup.string(),
//     is_public: yup.boolean(),
//     model_pk: yup.number(),
//     model_version: yup.string().nullable(),
//     notify_on_completion: yup.boolean(),
//     owner: yup.string(),
//     project: yup.string(),
//     // @ts-ignore
//     // readme: yup.object(),
//     // @ts-ignore
//     status: yup.string(),
//     title: yup.string()
//   })
// );

const Table: React.FC<{
  columns: Array<{
    Header: string;
    accessor: string | ((MiniSimulation) => any);
    sortType?: DefaultSortTypes;
    Cell?: (any) => string | JSX.Element;
  }>;
  data: Array<MiniSimulation>;
}> = ({ columns, data }) => {
  // Use the state and functions returned from useTable to build your UI
  const { getTableProps, getTableBodyProps, headerGroups, rows, prepareRow } = useTable(
    {
      columns,
      data
    },
    useSortBy
  );

  // Render the UI for your table
  return (
    <table {...getTableProps()} className="table">
      <thead>
        {headerGroups.map(headerGroup => (
          <tr {...headerGroup.getHeaderGroupProps()}>
            {headerGroup.headers.map((column: ColumnInstanceExt) => (
              <th {...column.getHeaderProps(column.getSortByToggleProps())}>
                <>
                  {column.render("Header")}

                  {column.isSorted ? (
                    column.isSortedDesc ? (
                      <i className="fas fa-sort-down ml-1"></i>
                    ) : (
                      <i className="fas fa-sort-up ml-1"></i>
                    )
                  ) : (
                    <i className="fas fa-sort ml-1"></i>
                  )}
                </>
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody {...getTableBodyProps()}>
        {rows.map((row, i) => {
          prepareRow(row);
          return (
            <tr {...row.getRowProps()}>
              {row.cells.map(cell => {
                return <td {...cell.getCellProps()}>{cell.render("Cell")}</td>;
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
};

const SimTable: React.FC<{ sims: Array<MiniSimulation> }> = ({ sims }) => {
  const columns: Array<{
    Header: string;
    accessor: string | ((MiniSimulation) => any);
    sortType?: DefaultSortTypes;
    Cell?: (any) => string | JSX.Element;
  }> = [
    {
      Header: "Output",
      accessor: "model_pk",
      Cell: ({ cell }) => (
        <Row>
          <Col>
            <a href={cell.row.original.gui_url}>{cell.value}</a>
          </Col>
          <Col>
            <a className="color-inherit hover-blue" href={`${cell.row.original.gui_url}edit/`}>
              <i className="fas fa-edit fa-sm"></i>
            </a>
          </Col>
        </Row>
      )
    },
    {
      Header: "Title",
      accessor: "title",
      Cell: ({ cell }) => <span style={{ wordBreak: "break-all" }}>{cell.value}</span>
    },
    { Header: "Model", accessor: "project" },
    {
      Header: "Status",
      accessor: "status",
      Cell: ({ cell }) => (
        <span className={`text-${textColor(cell.value as MiniSimulation["status"])}`}>
          {cell.value}
        </span>
      )
    },
    {
      Header: "Creation Date",
      accessor: (row: MiniSimulation) => new Date(row.creation_date),
      sortType: "datetime",
      Cell: ({ cell }) => moment(cell.value as Date).format("MMMM Do YYYY, h:mm:ss a")
    },
    {
      Header: "Access",
      accessor: "is_public",
      Cell: ({ cell }) =>
        cell.value ? <i className="fas fa-lock-open"></i> : <i className="fas fa-lock"></i>
    }
  ];

  return <Table columns={columns} data={sims} />;
};

class Activity extends React.Component<ActivityProps, ActivityState> {
  api: API;
  constructor(props) {
    super(props);
    super(props);
    const { username } = this.props.match.params;
    this.api = new API(username);
    this.state = {
      loading: false
    };

    this.loadAllSimulations = this.loadAllSimulations.bind(this);
  }

  componentDidMount() {
    this.api.getSimulations(50).then(sims => {
      this.setState({ sims });
    });
  }

  loadAllSimulations() {
    this.setState({ loading: true });
    this.api.getSimulations().then(sims => {
      this.setState({ sims, loading: false });
    });
  }

  render() {
    const { sims } = this.state;
    if (!sims) {
      return (
        <div className="d-flex justify-content-center">
          <ReactLoading type="spokes" color="#2b2c2d" />
        </div>
      );
    }
    console.log(sims);

    return (
      <div className="container-fluid">
        <SimTable sims={sims} />
        <Row className="text-center">
          <Col>
            <Button variant="outline-primary" onClick={this.loadAllSimulations}>
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

const textColor = (status: MiniSimulation["status"]) => {
  switch (status) {
    case "STARTED":
      return "primary";
    case "PENDING":
      return "warning";
    case "SUCCESS":
      return "success";
    case "FAIL":
      return "danger";
    case "WORKER_FAILURE":
      return "danger";
    default:
      return "dark";
  }
};
