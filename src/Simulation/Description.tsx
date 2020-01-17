"use strict";

import * as React from "react";
import { Card, Row, Col, Dropdown, Button, OverlayTrigger, Tooltip } from "react-bootstrap";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faHistory, faLock, faLockOpen, faUserFriends, faCodeBranch } from '@fortawesome/free-solid-svg-icons'
import * as yup from "yup";
import { AccessStatus, MiniSimulation, Simulation, RemoteOutputs } from "../types";
import { FormikActions, Formik, ErrorMessage, Field, Form, FormikProps } from "formik";
import { Message } from "../fields";
import moment = require("moment");
import API from "./API";
import ReadmeEditor from "./editor"
import { AxiosError } from "axios";

interface DescriptionProps {
  accessStatus: AccessStatus;
  api: API;
  remoteSim: Simulation<RemoteOutputs>;
}

interface DescriptionValues {
  title: string;
  readme: { [key: string]: any }[] | Node[];
  is_public: boolean;
}


let Schema = yup.object().shape({
  title: yup.string(),
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


const defaultReadme: { [key: string]: any }[] = [{
  type: "paragraph",
  children: [{ text: "" }],
}];

const Tip: React.FC<{ tip: string, children: JSX.Element }> = ({ tip, children }) => (
  <OverlayTrigger
    placement="top"
    delay={{ show: 400, hide: 400 }}
    overlay={(props) => <Tooltip {...props} show={props.show.toString()}>{tip}</Tooltip>}>
    {children}
  </OverlayTrigger>
)

const HistoryDropDownItems = (isOwner: boolean, historyType: "Public" | "Private", history: Array<MiniSimulation>): JSX.Element[] => {
  let viewableHistory = history.filter(
    sim => historyType === "Public" ? sim.is_public : true
  );
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
  let lockOpen = <i className="fas fa-lock-open mr-2"></i>
  // Hides behind inputs form w/out z-index set to 10000.
  let dropdownItems = [
    <Dropdown.Header key={historyType + "-0"}>
      <Row>
        <Col>
          {`${isOwner ? historyType + " History: " : ""}${nsims + 1}${suffix} Simulation in this line`}
        </Col>
      </Row>
    </Dropdown.Header >
  ]
  dropdownItems.push(...viewableHistory.map((sim, ix) => {
    return (
      <Dropdown.Item key={historyType + "-" + ix.toString()} href={sim.gui_url} className="w-100">
        <Row>
          <Col className="col-1">{sim.is_public ? lockOpen : lock}</Col>
          <Col className="col-1">{sim.model_pk}</Col>
          <Col className="col-5 text-truncate">{sim.title}</Col>
          <Col className="col-2">{sim.owner}</Col>
          <Col className="col-3 text-truncate">{moment(sim.creation_date).format("YYYY-MM-DD")}</Col>
        </Row>
      </Dropdown.Item>
    );
  }));
  return dropdownItems;
}


const HistoryDropDown: React.FC<{ isOwner: boolean, history: Array<MiniSimulation> }> = ({ isOwner, history }) => {
  let style = { width: "300%", zIndex: 10000 }
  let dropdownItems = HistoryDropDownItems(isOwner, "Public", history);
  if (isOwner) {
    dropdownItems.push(<Dropdown.Divider key="divider" />);
    dropdownItems.push(...HistoryDropDownItems(isOwner, "Private", history));
  }
  return (
    <Tip tip="List of previous simulations.">
      <Dropdown >
        <Dropdown.Toggle variant="dark" id="dropdown-basic" className="w-100" style={{ backgroundColor: "rgba(60, 62, 62, 1)" }}>
          <><FontAwesomeIcon icon={faHistory} className="mr-2" /> History</>
        </Dropdown.Toggle>
        <Dropdown.Menu style={style}>
          {dropdownItems}
        </Dropdown.Menu>
      </Dropdown >
    </Tip>
  );
}

const AuthorDropDown: React.FC<{ author: string }> = ({ author }) => {
  return (
    <Tip tip="Author(s) of the simulation.">
      <Dropdown>
        <Dropdown.Toggle variant="dark" id="dropdown-basic" className="w-100" style={{ backgroundColor: "rgba(60, 62, 62, 1)" }}>
          <><FontAwesomeIcon icon={faUserFriends} className="mr-2" /> Author</>
        </Dropdown.Toggle>
        <Dropdown.Menu>
          <Dropdown.Item key={0}>
            {author}
          </Dropdown.Item>
        </Dropdown.Menu>
      </Dropdown>
    </Tip>
  );
}

export default class DescriptionComponent extends React.PureComponent<
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
    }
    this.state = {
      initialValues: initialValues,
      isEditMode: false,
      parentSims: null,
      showAuth: false,
      showTitleBorder: false,
      dirty: false,
    };

    this.toggleEditMode = this.toggleEditMode.bind(this);
    this.writable = this.writable.bind(this);
    this.forkSimulation = this.forkSimulation.bind(this);
    this.titleInput = React.createRef<HTMLInputElement>();
    this.save = this.save.bind(this);
  }

  writable() {
    if (this.props.remoteSim) {
      return this.props.remoteSim.has_write_access;
    } else {
      return true;
    }
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
    if (this.writable()) {
      this.setState({
        isEditMode: !this.state.isEditMode
      });
    }
  }

  user() {
    return this.props.accessStatus && this.props.accessStatus.username ?
      this.props.accessStatus.username : "anon"
  }

  forkSimulation() {
    let api = this.props.api;
    if (api.modelpk) {
      api.forkSimulation().then(data => {
        window.location.href = data.gui_url;
      })
        .catch((err: AxiosError) => {
          if (err.response.status == 400 && err.response.data.fork) {
            this.setState({ forkError: err.response.data.fork })
          }
        }
        );
    }
  }

  save(values: DescriptionValues) {
    let formdata = new FormData();
    for (const field in values) {
      if (values[field]) formdata.append(field, values[field]);
    }
    formdata.append("model_pk", this.props.api.modelpk.toString());
    formdata.append("readme", JSON.stringify(values.readme));
    this.props.api.putDescription(formdata).then(data => {
      this.setState({ isEditMode: false, dirty: false, initialValues: values })
    });
  }

  render() {
    const api = this.props.api;
    const { isEditMode, showTitleBorder } = this.state;
    let is_public;

    let owner = this.props.remoteSim?.owner || this.user();

    let subtitle: string;
    if (api.modelpk) {
      subtitle = `${api.owner}/${api.title} #${api.modelpk.toString()}`;
    } else {
      subtitle = `New ${api.owner}/${api.title}`;
    }

    const titleStyle = { display: "inline-block", padding: "5px", margin: 0 }

    return (
      <Formik
        initialValues={this.state.initialValues}
        onSubmit={(values: DescriptionValues, actions: FormikActions<DescriptionValues>) => {
          if (!api.modelpk) {
            this.setState((prevState) => ({
              initialValues: {
                ...prevState.initialValues,
                ...values,
              },
              dirty: true,
              isEditMode: false,
            }));
          } else {
            this.save(values);
          }
        }}
        validationSchema={Schema}
        render={({ values, handleSubmit, setFieldValue }) => (
          <Form>
            <Card className="card-outer">
              <Card.Body>
                <Row className="justify-content-start">
                  <Col className="col-sm-5">
                    <Field name="title">
                      {({
                        field,
                      }) => {
                        return (
                          <>
                            <Card style={{ borderColor: "white" }} className={isEditMode ? "" : "d-none"}>
                              <input
                                ref={this.titleInput}
                                disabled={!isEditMode}
                                type="text"
                                placeholder="Untitled Simulation"
                                {...field}
                                className="form-cotnrol h3"
                                onBlur={handleSubmit}
                                style={titleStyle} />
                            </Card>
                            <Card
                              className={isEditMode ? "d-none" : ""}
                              style={showTitleBorder ? {} : { borderColor: "white" }}
                              onMouseEnter={() => this.writable() ? this.setState({ showTitleBorder: true }) : null}
                              onMouseLeave={() => this.writable() ? this.setState({ showTitleBorder: false }) : null}
                            >
                              <Tip tip={
                                this.writable() ?
                                  "Rename." :
                                  "You be an owner of this simulation to edit the title."}>
                                <h3 style={titleStyle} onClick={this.toggleEditMode}>{field.value || "Untitled Simulation"}</h3>
                              </Tip>
                            </Card>
                          </>
                        );
                      }}
                    </Field>
                    <ErrorMessage
                      name="title"
                      render={msg => <Message msg={msg} />}
                    />
                  </Col>
                  <Col className={`col-3 ml-sm-auto`}>
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
                      {({ field }) => <ReadmeEditor
                        fieldName="readme"
                        value={field.value}
                        setFieldValue={setFieldValue}
                        handleSubmit={handleSubmit}
                        readOnly={!this.writable()}
                      />}
                    </Field>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
            <Card className="text-center" style={{ backgroundColor: "inherit", border: 0, paddingLeft: 0, paddingRight: 0 }}>
              <Card.Body style={{ paddingLeft: "1rem", paddingRight: "1rem" }}>
                {this.state.forkError ?
                  <div className="alert alert-danger" role="alert">
                    {this.state.forkError}
                  </div> : null}
                <Row className="justify-content-left">
                  <Col className="col-sm-2" style={{ paddingLeft: 0 }}>
                    <AuthorDropDown author={owner} />
                  </Col>
                  <Col className="col-sm-2" >
                    <HistoryDropDown isOwner={this.writable()} history={this.props.remoteSim?.parent_sims || []} />
                  </Col>
                  {this.user() !== "anon" ?
                    <Col className="col-sm-2">
                      <Tip tip="Create a copy of this simulation.">
                        <Button className="w-100" onClick={this.forkSimulation} variant="dark" style={{ backgroundColor: "rgba(60, 62, 62, 1)" }} >
                          <><FontAwesomeIcon icon={faCodeBranch} className="mr-2" /> Fork</>
                        </Button>
                      </Tip>
                    </Col>
                    : null}
                  {this.writable() ?
                    <Col className="col-sm-2 ml-sm-auto" style={{ paddingRight: 0 }}>
                      <Tip tip={`Make this simulation ${values.is_public ? "private" : "public"}.`}>
                        <Button variant="dark" style={{ backgroundColor: "rgba(60, 62, 62, 1)" }} className="mb-4 w-100" onClick={e => {
                          e.target.value = !values.is_public;
                          setFieldValue("is_public", !values.is_public);
                          // put handleSubmit in setTimeout since setFieldValue is async
                          // but does not return a promise
                          // https://github.com/jaredpalmer/formik/issues/529
                          setTimeout(() => handleSubmit(e), 0);
                        }}>
                          {values.is_public ?
                            <><FontAwesomeIcon icon={faLockOpen} className="mr-2" />Public</> :
                            <><FontAwesomeIcon icon={faLock} className="mr-2" />Private</>}
                        </Button>
                      </Tip>
                    </Col> :
                    null
                  }
                </Row>
              </Card.Body>
            </Card>
          </ Form>
        )}
      />
    );
  }
}
