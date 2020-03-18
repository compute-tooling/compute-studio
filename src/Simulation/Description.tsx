"use strict";

import * as React from "react";
import { Card, Row, Col, Dropdown, Button, OverlayTrigger, Tooltip } from "react-bootstrap";
import * as yup from "yup";
import {
  AccessStatus,
  MiniSimulation,
  Simulation,
  RemoteOutputs,
  Role,
  DescriptionValues
} from "../types";
import { Formik, FormikHelpers, ErrorMessage, Field, Form, FormikProps } from "formik";
import { Message } from "../fields";
import moment = require("moment");
import API from "./API";
import ReadmeEditor from "./editor";
import { AxiosError } from "axios";
import { RolePerms } from "../roles";
import { CollaborationSettings, saveCollaborators } from "./collaborators";

interface DescriptionProps {
  accessStatus: AccessStatus;
  api: API;
  remoteSim: Simulation<RemoteOutputs>;
  resetOutputs: () => void;
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
      author: { add: { username: "", msg: "" }, remove: { username: "" } },
      access: { read: { grant: { username: "", msg: "" }, remove: { username: "" } } }
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
    this.pendingPermission = this.pendingPermission.bind(this);
    this.plan = this.plan.bind(this);
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

  pendingPermission() {
    console.log(this.props.remoteSim?.pending_permissions);
    if (!this.props.remoteSim?.pending_permissions) {
      return undefined;
    }

    if (!!this.props.remoteSim.authors.find(author => author === this.user())) {
      return undefined;
    }

    return this.props.remoteSim.pending_permissions.find(
      pp => pp.profile === this.user() && !pp.is_expired
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

  plan() {
    return this.props.accessStatus.plan.name;
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

  save(values: DescriptionValues, actions?: FormikHelpers<DescriptionValues>) {
    const resetStatus = () => {
      if (!!actions) {
        actions.setStatus({ collaboratorLimit: null });
      }
    };

    const setSubmitting = (submitting: boolean) => {
      if (!!actions) {
        actions.setSubmitting(submitting);
      }
    };

    resetStatus();
    if (this.hasWriteAccess()) {
      let formdata = new FormData();
      for (const field of ["title", "readme", "is_public"]) {
        if (values[field]) formdata.append(field, values[field]);
      }
      formdata.append("model_pk", this.props.api.modelpk.toString());
      formdata.append("readme", JSON.stringify(values.readme));
      saveCollaborators(this.props.api, values, this.props.resetOutputs)
        .then(() =>
          this.props.api
            .putDescription(formdata)
            .then(data => {
              if (!!this.props.remoteSim && data.is_public !== this.props.remoteSim?.is_public) {
                this.props.resetOutputs();
              }
              this.setState({
                isEditMode: false,
                dirty: false,
                initialValues: {
                  ...values,
                  ...{
                    // is public is stored on the server side, except when the
                    // remoteSim has not been defined...i.e. new sim.
                    is_public: !!this.props.remoteSim
                      ? this.props.remoteSim?.is_public
                      : values.is_public
                  }
                }
              });
            })
            .catch(error => {
              if (!actions) throw error;
              if (error.response.status == 400 && error.response.data.collaborators) {
                window.scroll(0, 0);
                actions.setStatus({
                  collaboratorLimit: error.response.data.collaborators
                });
              }
              setSubmitting(false);
            })
        )
        .catch(error => {
          if (!actions) throw error;
          if (error.response.status == 400 && error.response.data.collaborators) {
            window.scroll(0, 0);
            actions.setStatus({
              collaboratorLimit: error.response.data.collaborators
            });
          }
          setSubmitting(false);
        })
        .finally(() => setSubmitting(false));
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
    const pendingPermission = this.pendingPermission();
    console.log("pending", pendingPermission);
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
            this.save(values, actions);
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
                                    : "You must be an owner of this simulation to edit the title."
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
                  {!!pendingPermission ? (
                    <Col className="col-sm-2 ml-sm-auto mt-1">
                      <a className="btn btn-success bold" href={pendingPermission.grant_url}>
                        <strong>Accept Author Invite</strong>
                      </a>
                    </Col>
                  ) : null}
                  {this.hasAuthorPortalAccess() ? (
                    <Col className="col-sm-2 ml-sm-auto mt-1" style={{ paddingRight: 0 }}>
                      <CollaborationSettings
                        api={api}
                        user={this.user()}
                        remoteSim={this.props.remoteSim}
                        formikProps={formikProps}
                        plan={this.plan()}
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
