"use strict";

import * as React from "react";
import { Card, Jumbotron, Row, Col, Dropdown, Button } from "react-bootstrap";
import * as yup from "yup";
import { AccessStatus, MiniSimulation, Simulation, RemoteOutputs } from "../types";
import { FormikActions, Formik, ErrorMessage, Field, Form } from "formik";
import { Message } from "../fields";
import moment = require("moment");
import API from "./API";
import { AxiosError } from "axios";

interface DescriptionProps {
  accessStatus: AccessStatus;
  api: API;
  remoteSim: Simulation<RemoteOutputs>;
}

interface DescriptionValues {
  title: string;
  is_public: boolean;
}


let Schema = yup.object().shape({
  title: yup.string(),
});


type DescriptionState = Readonly<{
  initialValues: DescriptionValues;
  isEditMode: boolean;
  showTitleBorder: boolean;
  showAuth: boolean;
  parentSims?: Array<MiniSimulation>;
  forkError?: string;
}>;


const HistoryDropDown: React.FC<{ history: Array<MiniSimulation> }> = ({ history }) => {
  let nsims = history.length;
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
  let dropdownItems = [
    <Dropdown.Header key={0} style={{ minWidth: "500px" }}>
      <Row>
        <Col>
          {`${nsims + 1}${suffix} Simulation in line`}
        </Col>
      </Row>
    </Dropdown.Header >
  ]
  dropdownItems.push(...history.map((sim, ix) => {
    return (
      <Dropdown.Item key={ix + 1} href={sim.gui_url} style={{ minWidth: "500px" }}>
        <Row>
          <Col className="col-3">{sim.model_pk}</Col>
          <Col className="col-3 text-truncate">{sim.title}</Col>
          <Col className="col-3">by {sim.owner}</Col>
          <Col className="col-3">on {moment(sim.creation_date).format("YYYY-MM-DD")}</Col>
        </Row>
      </Dropdown.Item>
    );
  }));


  return (
    <Dropdown>
      <Dropdown.Toggle variant="dark" id="dropdown-basic" className="w-100" style={{ backgroundColor: "rgba(60, 62, 62, 1)" }}>
        <><i className="fas fa-history mr-2"></i>History</>
      </Dropdown.Toggle>
      <Dropdown.Menu>
        {dropdownItems}
      </Dropdown.Menu>
    </Dropdown >
  );
}

const AuthorDropDown: React.FC<{ author: string }> = ({ author }) => {
  return (
    <Dropdown>
      <Dropdown.Toggle variant="dark" id="dropdown-basic" className="w-100" style={{ backgroundColor: "rgba(60, 62, 62, 1)" }}>
        <><i className="fas fa-user-friends mr-2"></i>Author</>
      </Dropdown.Toggle>
      <Dropdown.Menu>
        <Dropdown.Item key={0}>
          {author}
        </Dropdown.Item>
      </Dropdown.Menu>
    </Dropdown >
  );
}

export default class DescriptionComponent extends React.PureComponent<
  DescriptionProps,
  DescriptionState
  > {

  titleInput: React.RefObject<HTMLInputElement>;

  constructor(props) {
    super(props);
    this.state = {
      initialValues: null,
      isEditMode: false,
      parentSims: null,
      showAuth: false,
      showTitleBorder: false,
    };
    this.toggleEditMode = this.toggleEditMode.bind(this);
    this.writable = this.writable.bind(this);
    this.forkSimulation = this.forkSimulation.bind(this);
    this.titleInput = React.createRef<HTMLInputElement>();
  }

  writable() {
    return (
      ["profile", "customer"].includes(this.props.accessStatus.user_status) &&
      this.user() === this.props.remoteSim?.owner
    );
  }

  componentDidUpdate() {
    if (this.state.isEditMode) {
      this.titleInput.current.focus();
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

  render() {
    const api = this.props.api;
    const { isEditMode, showTitleBorder } = this.state;
    let title, owner, is_public;

    if (this.props.remoteSim) {
      title = this.props.remoteSim.title;
      owner = this.props.remoteSim.owner;
      is_public = this.props.remoteSim.is_public;
    } else {
      title = "Untitled Simulation";
      owner = this.user();
      is_public = false;
    }

    let subtitle: string;
    if (api.modelpk) {
      subtitle = `${api.owner}/${api.title} #${api.modelpk.toString()}`;
    } else {
      subtitle = `New ${api.owner}/${api.title}`;
    }

    const titleStyle = { display: "inline-block", padding: "5px", margin: 0 }
    return (
      <Formik
        initialValues={{ title: title, is_public: is_public }}
        onSubmit={(values: DescriptionValues, actions: FormikActions<DescriptionValues>) => {
          let formdata = new FormData();
          for (const field in values) {
            formdata.append(field, values[field]);
          }
          formdata.append("model_pk", api.modelpk.toString());
          this.props.api.putDescription(formdata).then(data => {
            this.setState({ isEditMode: false })
          })
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
                              <h3 style={titleStyle} onClick={this.toggleEditMode}>{field.value || "Untitled Simulation"}</h3>
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
                  <Col className={`col-3 ml-sm-auto mt-1`}>
                    <h5 style={{ color: "#6c757d" }}>{subtitle}</h5>
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
                    <HistoryDropDown history={this.props.remoteSim?.parent_sims || []} />
                  </Col>
                  {this.user() !== "anon" ?
                    <Col className="col-sm-2">
                      <Button className="w-100" onClick={this.forkSimulation} variant="dark" style={{ backgroundColor: "rgba(60, 62, 62, 1)" }} >
                        <><i className="fas fa-code-branch mr-2"></i> Fork</>
                      </Button>
                    </Col>
                    : null}
                  {this.writable() ?
                    <Col className="col-sm-2 ml-sm-auto" style={{ paddingRight: 0 }}>
                      <Button variant="dark" style={{ backgroundColor: "rgba(60, 62, 62, 1)" }} className="mb-4 w-100" onClick={e => {
                        e.target.value = !values.is_public;
                        setFieldValue("is_public", !values.is_public);
                        // put handleSubmit in setTimeout since setFieldValue is async
                        // but does not return a promise
                        // https://github.com/jaredpalmer/formik/issues/529
                        setTimeout(() => handleSubmit(e), 0);
                      }}>
                        {values.is_public ?
                          <><i className="fas fa-lock-open mr-2"></i>Public</> :
                          <><i className="fas fa-lock mr-2"></i>Private</>}
                      </Button>
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
