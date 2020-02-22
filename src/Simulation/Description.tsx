"use strict";

import * as React from "react";
import {
  Card,
  Row,
  Col,
  Dropdown,
  Button,
  OverlayTrigger,
  Tooltip,
  Modal,
  Container
} from "react-bootstrap";
import * as yup from "yup";
import { AccessStatus, MiniSimulation, Simulation, RemoteOutputs, Role } from "../types";
import { Formik, FormikHelpers, ErrorMessage, Field, Form, FormikProps, FastField } from "formik";
import { Message } from "../fields";
import moment = require("moment");
import API from "./API";
import ReadmeEditor from "./editor";
import { AxiosError } from "axios";
import { RolePerms } from "../roles";

interface DescriptionProps {
  accessStatus: AccessStatus;
  api: API;
  remoteSim: Simulation<RemoteOutputs>;
  resetOutputs: () => void;
}

interface DescriptionValues {
  title: string;
  readme: { [key: string]: any }[] | Node[];
  is_public: boolean;
  author: {
    add: string;
    remove: string;
  };
  access: {
    read: { grant: string; remove: string };
  };
}

let Schema = yup.object().shape({
  title: yup.string()
});

type DescriptionState = Readonly<{
  initialValues: DescriptionValues;
  dirty: boolean;
  isEditMode: boolean;
  showTitleBorder: boolean;
  showAuth: boolean;
  parentSims?: Array<MiniSimulation>;
  forkError?: string;
}>;

const defaultReadme: { [key: string]: any }[] = [
  {
    type: "paragraph",
    children: [{ text: "" }]
  }
];

const Tip: React.FC<{ tip: string; children: JSX.Element }> = ({ tip, children }) => (
  <OverlayTrigger
    placement="top"
    delay={{ show: 400, hide: 400 }}
    overlay={props => (
      <Tooltip {...props} show={props.show.toString()}>
        {tip}
      </Tooltip>
    )}
  >
    {children}
  </OverlayTrigger>
);

const HistoryDropDownItems = (
  historyType: "Public" | "Private",
  history: Array<MiniSimulation>
): JSX.Element[] => {
  let viewableHistory = history.filter(sim => (historyType === "Public" ? sim.is_public : true));
  let nsims = viewableHistory.length;
  let suffix;
  switch (nsims) {
    case 0:
      suffix = "st";
      break;
    case 1:
      suffix = "nd";
      break;
    case 2:
      suffix = "rd";
      break;
    default:
      suffix = "th";
  }

  let lock = <i className="fas fa-lock mr-2"></i>;
  let lockOpen = <i className="fas fa-lock-open mr-2"></i>;
  // Hides behind inputs form w/out z-index set to 10000.
  let dropdownItems = [
    <Dropdown.Header key={historyType + "-header"}>
      <Row>
        <Col>{`${historyType + " History: "}${nsims + 1}${suffix} Simulation in this line`}</Col>
      </Row>
    </Dropdown.Header>
  ];
  dropdownItems.push(
    ...viewableHistory.map((sim, ix) => {
      return (
        <Dropdown.Item key={historyType + "-" + ix.toString()} href={sim.gui_url} className="w-100">
          <Row>
            <Col className="col-1">{sim.is_public ? lockOpen : lock}</Col>
            <Col className="col-1">{sim.model_pk}</Col>
            <Col className="col-5 text-truncate">{sim.title}</Col>
            <Col className="col-2">{sim.owner}</Col>
            <Col className="col-3 text-truncate">
              {moment(sim.creation_date).format("YYYY-MM-DD")}
            </Col>
          </Row>
        </Dropdown.Item>
      );
    })
  );
  return dropdownItems;
};

const HistoryDropDown: React.FC<{ history: Array<MiniSimulation> }> = ({ history }) => {
  let style = { width: "300%", zIndex: 10000 };
  let dropdownItems = HistoryDropDownItems("Public", history);
  let privateDropdownItems = HistoryDropDownItems("Private", history);
  if (privateDropdownItems.length > 0) {
    dropdownItems.push(<Dropdown.Divider key="divider" />);
    dropdownItems.push(...privateDropdownItems);
  }
  return (
    <Tip tip="List of previous simulations.">
      <Dropdown>
        <Dropdown.Toggle
          variant="dark"
          id="dropdown-basic"
          className="w-100"
          style={{ backgroundColor: "rgba(60, 62, 62, 1)" }}
        >
          <>
            <i className="fas fa-history mr-2"></i> History
          </>
        </Dropdown.Toggle>
        <Dropdown.Menu style={style}>{dropdownItems}</Dropdown.Menu>
      </Dropdown>
    </Tip>
  );
};

const AuthorsDropDown: React.FC<{ authors: string[] }> = ({ authors }) => {
  return (
    <Tip tip="Author(s) of the simulation.">
      <Dropdown>
        <Dropdown.Toggle
          variant="dark"
          id="dropdown-basic"
          className="w-100"
          style={{ backgroundColor: "rgba(60, 62, 62, 1)" }}
        >
          <>
            <i className="fas fa-user-friends mr-2"></i> {`Author${authors.length > 1 ? "s" : ""}`}
          </>
        </Dropdown.Toggle>
        <Dropdown.Menu>
          {authors.map((author, ix) => (
            <Dropdown.Item key={ix}>{author}</Dropdown.Item>
          ))}
        </Dropdown.Menu>
      </Dropdown>
    </Tip>
  );
};

export const UserQuery: React.FC<{
  show: boolean;
  selectedUsers: Array<{ username: string }>;
  query: Array<{ username: string }>;
  onSelectUser: (user: { username: string }) => void;
}> = ({ show, selectedUsers, query, onSelectUser }) => {
  if (!query || query.length === 0 || !show) return null;

  return (
    <div className="border rounded shadow mt-2 custom-dropdown-menu">
      {query.map((user, qix) => (
        // TODO: maybe set this as FocusableCard
        <Row className="my-2 mx-3 w-auto" key={qix}>
          <Col>
            <a
              className="color-inherit"
              role="button"
              style={{ cursor: "pointer" }}
              onClick={() => onSelectUser(user)}
            >
              {user.username}
              {selectedUsers.find(sel => sel.username === user.username) ? (
                <span className="text-muted"> &#183; Already selected.</span>
              ) : null}
            </a>
          </Col>
        </Row>
      ))}
    </div>
  );
};

export const CollaborationSettings: React.FC<{
  api: API;
  user: string;
  remoteSim?: Simulation<RemoteOutputs>;
  formikProps: FormikProps<DescriptionValues>;
}> = ({ api, user, remoteSim, formikProps }) => {
  const [show, setShow] = React.useState(false);
  const [viewAuthorQuery, setViewAuthorQuery] = React.useState(false);
  const [authorQuery, setAuthorQuery] = React.useState<Array<{ username: string }>>([]);

  const [accessQuery, setAccessQuery] = React.useState<Array<{ username: string }>>([]);
  const [viewAccessQuery, setViewAccessQuery] = React.useState(false);

  let authors: Array<{
    username: string;
    pending?: boolean;
  }> = (remoteSim?.authors || []).map((author, ix) => ({ username: author }));
  if (remoteSim?.pending_permissions) {
    for (const pp of remoteSim.pending_permissions) {
      if (pp.permission_name === "add_author" && !pp.is_expired) {
        authors.push({ username: pp.profile, pending: true });
      }
    }
  }

  const handleQuery = (e, updateFunc: (users: Array<{ username: string }>) => void) => {
    api.queryUsers(e.target.value).then(data => {
      updateFunc(data);
    });
  };

  const { values, setFieldValue, handleSubmit } = formikProps;

  return (
    <>
      <Button
        variant="dark"
        style={{ backgroundColor: "rgba(60, 62, 62, 1)" }}
        className="mb-4 w-100 mt-1"
        onClick={() => setShow(true)}
      >
        <>
          <i className={`fas fa-${formikProps.values.is_public ? "lock-open" : "lock"} mr-2`}></i>
          Share
        </>
      </Button>

      <Modal show={show} onHide={() => setShow(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Collaboration Settings</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Row className="w-100 my-2 mx-0">
            <Col>
              <p className="lead ml-0">Authors</p>
              {(authors.length > 0 ? authors : [{ username: user }]).map((author, ix) => (
                <Row
                  key={ix}
                  className={`w-100 p-2 justify-content-between border ${
                    ix === 0 ? " rounded-top " : " "
                  }
                    ${ix < authors.length - 1 ? " border-bottom-0" : " rounded-bottom"}`}
                >
                  <Col className="col-7">
                    <span>{author.username}</span>
                  </Col>
                  <Col className="col-4">
                    {author.pending ? (
                      <Tip tip={`Waiting for ${author.username}'s approval.`}>
                        <span className="text-muted">pending</span>
                      </Tip>
                    ) : null}
                    {author.username === remoteSim?.owner ? (
                      <span className="text-success">owner</span>
                    ) : null}
                  </Col>
                  <Col className="col-1">
                    {/* owner cannt be removed, to remove an author user must have
                    write access or be removing themselves. */}
                    {remoteSim &&
                    author.username !== remoteSim?.owner &&
                    ((remoteSim && RolePerms.hasAdminAccess(remoteSim)) ||
                      user === author.username) ? (
                      <a
                        className="color-inherit"
                        role="button"
                        style={{ maxHeight: 0.5, cursor: "pointer" }}
                        onClick={() => {
                          setFieldValue("author.remove", author.username);
                          setTimeout(handleSubmit, 0);
                          setTimeout(() => setFieldValue("author.remove", ""), 0);
                        }}
                      >
                        <i className="far fa-trash-alt hover-red"></i>
                      </a>
                    ) : null}
                  </Col>
                </Row>
              ))}
            </Col>
          </Row>
          {remoteSim && RolePerms.hasAdminAccess(remoteSim) ? (
            <Row className="w-100 justify-content-left my-2">
              <Col>
                <FastField
                  name="author.add"
                  className="form-control"
                  placeholder="Search by email or username."
                  onFocus={() => {
                    setViewAuthorQuery(true);
                  }}
                  onChange={e => {
                    setViewAuthorQuery(true);
                    handleQuery(e, users => setAuthorQuery(users));
                    setFieldValue("author.add", e.target.value);
                  }}
                />
                <UserQuery
                  query={authorQuery}
                  selectedUsers={authors}
                  show={viewAuthorQuery}
                  onSelectUser={selected => {
                    if (authors.find(a => a.username === selected.username)) return;
                    setFieldValue("author.add", selected.username);
                    setTimeout(handleSubmit, 0);
                    setTimeout(() => setFieldValue("author.add", ""), 0);
                    setAuthorQuery([]);
                  }}
                />
              </Col>
            </Row>
          ) : null}
          {RolePerms.hasAdminAccess(remoteSim) || !remoteSim ? (
            <Row className="w-100 mt-4 mb-2 mx-0">
              <Col>
                <p className="lead">Who has access</p>
                {values.is_public ? (
                  <p>
                    This simulation is <strong>public</strong> and can be viewed by anyone.
                  </p>
                ) : (
                  <p>
                    This simulation is <strong>private</strong> and can only be viewed by users who
                    have been granted access to it.
                  </p>
                )}
                <Row className="w-100 justify-content-center">
                  <Col className="col-auto">
                    <Button
                      variant="dark"
                      style={{ backgroundColor: "rgba(60, 62, 62, 1)", fontWeight: 450 }}
                      className="mb-4 w-100 mt-1"
                      onClick={() => {
                        setFieldValue("is_public", !values.is_public);
                        // put handleSubmit in setTimeout since setFieldValue is async
                        // but does not return a promise
                        // https://github.com/jaredpalmer/formik/issues/529
                        setTimeout(handleSubmit, 0);
                      }}
                    >
                      Make this simulation {values.is_public ? "private" : "public"}
                    </Button>
                  </Col>
                </Row>
              </Col>
            </Row>
          ) : null}
          {RolePerms.hasAdminAccess(remoteSim) ? (
            <>
              <Row className="w-100 my-2 mx-0">
                <Col>
                  <p className="lead">Manage access</p>
                  {remoteSim.access.map((accessobj, ix) => (
                    <Row
                      key={ix}
                      className={`w-100 p-2 justify-content-between border ${
                        ix === 0 ? " rounded-top " : " "
                      }
                    ${ix < remoteSim.access.length - 1 ? " border-bottom-0" : " rounded-bottom"}`}
                    >
                      <Col className="col-7">
                        <span>{accessobj.username}</span>
                      </Col>
                      <Col className="col-4">
                        {accessobj.is_owner ? (
                          <span className="text-success">owner</span>
                        ) : (
                          <span className="text-muted">{accessobj.role}</span>
                        )}
                      </Col>
                      <Col className="col-1">
                        {/* owner cannot lose access, and authors must be removed as authors
                        before they can lose access to the simulation. */}
                        {accessobj.username !== remoteSim?.owner &&
                        !authors.find(author => author.username === accessobj.username) ? (
                          <a
                            className="color-inherit"
                            role="button"
                            style={{ maxHeight: 0.5, cursor: "pointer" }}
                            onClick={() => {
                              setFieldValue("access.read.remove", accessobj.username);
                              setTimeout(handleSubmit, 0);
                              setTimeout(() => setFieldValue("access.read.remove", ""), 0);
                            }}
                          >
                            <i className="far fa-trash-alt hover-red"></i>
                          </a>
                        ) : null}
                      </Col>
                    </Row>
                  ))}
                </Col>
              </Row>
              <Row className="w-100 justify-content-left my-2">
                <Col>
                  <FastField
                    name="access.read.grant"
                    className="form-control"
                    placeholder="Search by email or username."
                    onFocus={() => {
                      setViewAccessQuery(true);
                    }}
                    onChange={e => {
                      setViewAccessQuery(true);
                      handleQuery(e, users => setAccessQuery(users));
                      setFieldValue("access.read.grant", e.target.value);
                    }}
                  />
                  <UserQuery
                    query={accessQuery}
                    selectedUsers={authors}
                    show={viewAccessQuery}
                    onSelectUser={selected => {
                      if (remoteSim.access.find(a => a.username === selected.username)) return;
                      setFieldValue("access.read.grant", selected.username);
                      setTimeout(handleSubmit, 0);
                      setTimeout(() => setFieldValue("access.read.grant", ""), 0);
                      setAccessQuery([]);
                    }}
                  />
                </Col>
              </Row>
            </>
          ) : null}
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

export default class DescriptionComponent extends React.Component<
  DescriptionProps,
  DescriptionState
> {
  titleInput: React.RefObject<HTMLInputElement>;

  constructor(props) {
    super(props);
    let initialValues: DescriptionValues = {
      title: this.props.remoteSim?.title || "Untitled Simulation",
      readme: this.props.remoteSim?.readme || defaultReadme,
      is_public: this.props.remoteSim?.is_public || false,
      author: { add: "", remove: "" },
      access: { read: { grant: "", remove: "" } }
    };
    this.state = {
      initialValues: initialValues,
      isEditMode: false,
      parentSims: null,
      showAuth: false,
      showTitleBorder: false,
      dirty: false
    };

    this.toggleEditMode = this.toggleEditMode.bind(this);
    this.hasWriteAccess = this.hasWriteAccess.bind(this);
    this.hasAdminAccess = this.hasAdminAccess.bind(this);
    this.hasAuthorPortalAccess = this.hasAuthorPortalAccess.bind(this);
    this.forkSimulation = this.forkSimulation.bind(this);
    this.titleInput = React.createRef<HTMLInputElement>();
    this.save = this.save.bind(this);
  }

  hasWriteAccess() {
    if (this.props.remoteSim) {
      return RolePerms.hasWriteAccess(this.props.remoteSim);
    } else {
      return true;
    }
  }

  hasAdminAccess() {
    if (this.props.remoteSim) {
      return RolePerms.hasAdminAccess(this.props.remoteSim);
    } else {
      return true;
    }
  }

  hasAuthorPortalAccess() {
    return this.hasAdminAccess() || this.props.remoteSim.authors.includes(this.user());
  }

  shouldComponentUpdate(nextProps: DescriptionProps, nextState: DescriptionState) {
    // Only update on state changes, simulation id changes, or username changes.
    // In the future, we may want to update the accessStatus check to compare more
    // fields than just the username.
    return (
      this.state !== nextState ||
      this.state.initialValues !== nextState.initialValues ||
      this.props.api.modelpk !== nextProps.api.modelpk ||
      this.props.accessStatus.username !== nextProps.accessStatus.username ||
      this.props.remoteSim?.model_pk !== nextProps.remoteSim?.model_pk ||
      this.props.remoteSim?.pending_permissions !== nextProps.remoteSim?.pending_permissions ||
      this.props.remoteSim?.authors !== nextProps.remoteSim?.authors
    );
  }

  componentDidUpdate() {
    if (this.state.isEditMode) {
      this.titleInput.current.select();
    }
    if (this.state.dirty && this.props.api.modelpk) {
      this.save(this.state.initialValues);
    }
  }

  toggleEditMode() {
    if (this.hasWriteAccess()) {
      this.setState({
        isEditMode: !this.state.isEditMode
      });
    }
  }

  user() {
    return this.props.accessStatus && this.props.accessStatus.username
      ? this.props.accessStatus.username
      : "anon";
  }

  forkSimulation() {
    let api = this.props.api;
    if (api.modelpk) {
      api
        .forkSimulation()
        .then(data => {
          window.location.href = data.gui_url;
        })
        .catch((err: AxiosError) => {
          if (err.response.status == 400 && err.response.data.fork) {
            this.setState({ forkError: err.response.data.fork });
          }
        });
    }
  }

  save(values: DescriptionValues) {
    if (this.hasWriteAccess()) {
      let formdata = new FormData();
      for (const field of ["title", "readme", "is_public"]) {
        if (values[field]) formdata.append(field, values[field]);
      }
      formdata.append("model_pk", this.props.api.modelpk.toString());
      formdata.append("readme", JSON.stringify(values.readme));
      this.props.api.putDescription(formdata).then(data => {
        this.setState({ isEditMode: false, dirty: false, initialValues: values });
      });
    }

    if (values.author?.add) {
      this.props.api.addAuthors({ authors: [values.author.add] }).then(data => {
        this.props.resetOutputs();
        this.setState(prevState => ({
          initialValues: { ...prevState.initialValues, author: { add: "", remove: "" } }
        }));
      });
    }
    if (values.author?.remove) {
      this.props.api.deleteAuthor(values.author.remove).then(data => {
        this.props.resetOutputs();
        this.setState(prevState => ({
          initialValues: { ...prevState.initialValues, author: { add: "", remove: "" } }
        }));
      });
    }
    if (values.access?.read) {
      if (values.access.read.grant) {
        this.props.api
          .putAccess([{ username: values.access.read.grant, role: "read" as Role }])
          .then(resp => {
            this.props.resetOutputs();
          });
      } else if (values.access.read.remove) {
        this.props.api
          .putAccess([{ username: values.access.read.remove, role: null }])
          .then(resp => {
            this.props.resetOutputs();
          });
      }
    }
  }

  render() {
    const api = this.props.api;
    const { isEditMode, showTitleBorder } = this.state;

    let authors = this.props.remoteSim?.authors || [this.user()];

    let subtitle: string;
    if (api.modelpk) {
      subtitle = `${api.owner}/${api.title} #${api.modelpk.toString()}`;
    } else {
      subtitle = `New ${api.owner}/${api.title}`;
    }

    const titleStyle = { display: "inline-block", padding: "5px", margin: 0 };

    return (
      <Formik
        initialValues={this.state.initialValues}
        onSubmit={(values: DescriptionValues, actions: FormikHelpers<DescriptionValues>) => {
          if (!api.modelpk) {
            this.setState(prevState => ({
              initialValues: {
                ...prevState.initialValues,
                ...values
              },
              dirty: true,
              isEditMode: false
            }));
          } else {
            this.save(values);
          }
        }}
        validationSchema={Schema}
      >
        {(formikProps: FormikProps<DescriptionValues>) => (
          <Form>
            <Card className="card-outer">
              <Card.Body>
                <Row className="justify-content-start">
                  <Col className="col-md-9">
                    <Field name="title">
                      {({ field }) => {
                        return (
                          <>
                            <Card
                              style={{ borderColor: "white" }}
                              className={isEditMode ? "" : "d-none"}
                            >
                              <input
                                ref={this.titleInput}
                                disabled={!isEditMode}
                                type="text"
                                placeholder="Untitled Simulation"
                                {...field}
                                className="form-cotnrol h3"
                                onBlur={formikProps.handleSubmit}
                                style={titleStyle}
                              />
                            </Card>
                            <Card
                              className={isEditMode ? "d-none" : ""}
                              style={showTitleBorder ? {} : { borderColor: "white" }}
                              onMouseEnter={() =>
                                this.hasWriteAccess()
                                  ? this.setState({ showTitleBorder: true })
                                  : null
                              }
                              onMouseLeave={() =>
                                this.hasWriteAccess()
                                  ? this.setState({ showTitleBorder: false })
                                  : null
                              }
                            >
                              <Tip
                                tip={
                                  this.hasWriteAccess()
                                    ? "Rename."
                                    : "You be an owner of this simulation to edit the title."
                                }
                              >
                                <h3 style={titleStyle} onClick={this.toggleEditMode}>
                                  {field.value || "Untitled Simulation"}
                                </h3>
                              </Tip>
                            </Card>
                          </>
                        );
                      }}
                    </Field>
                    <ErrorMessage name="title" render={msg => <Message msg={msg} />} />
                  </Col>
                  <Col className={`col-md-3 ml-md-auto`}>
                    <h5 style={{ color: "#6c757d", marginTop: "0.89rem" }}>{subtitle}</h5>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
            <Card className="card-outer">
              <Card.Body>
                <Row className="justify-content-start">
                  <Col>
                    <Field name="readme">
                      {({ field }) => (
                        <ReadmeEditor
                          fieldName="readme"
                          value={field.value}
                          setFieldValue={formikProps.setFieldValue}
                          handleSubmit={formikProps.handleSubmit}
                          readOnly={!this.hasWriteAccess()}
                        />
                      )}
                    </Field>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
            <Card
              className="text-center"
              style={{ backgroundColor: "inherit", border: 0, paddingLeft: 0, paddingRight: 0 }}
            >
              <Card.Body style={{ paddingLeft: "1rem", paddingRight: "1rem" }}>
                {this.state.forkError ? (
                  <div className="alert alert-danger" role="alert">
                    {this.state.forkError}
                  </div>
                ) : null}
                <Row className="justify-content-left">
                  <Col className="col-sm-2 mt-1" style={{ paddingLeft: 0 }}>
                    <AuthorsDropDown authors={authors} />
                  </Col>
                  <Col className="col-sm-2 mt-1">
                    <HistoryDropDown history={this.props.remoteSim?.parent_sims || []} />
                  </Col>
                  {this.user() !== "anon" ? (
                    <Col className="col-sm-2 mt-1">
                      <Tip tip="Create a copy of this simulation.">
                        <Button
                          className="w-100"
                          onClick={this.forkSimulation}
                          variant="dark"
                          style={{ backgroundColor: "rgba(60, 62, 62, 1)" }}
                        >
                          <>
                            <i className="fas fa-code-branch mr-2"></i> Fork
                          </>
                        </Button>
                      </Tip>
                    </Col>
                  ) : null}
                  {this.hasAuthorPortalAccess() ? (
                    <Col className="col-sm-2 ml-sm-auto mt-1" style={{ paddingRight: 0 }}>
                      <CollaborationSettings
                        api={api}
                        user={this.user()}
                        remoteSim={this.props.remoteSim}
                        formikProps={formikProps}
                      />
                    </Col>
                  ) : null}
                </Row>
              </Card.Body>
            </Card>
          </Form>
        )}
      </Formik>
    );
  }
}
