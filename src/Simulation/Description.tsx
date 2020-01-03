"use strict";

import * as React from "react";
import { Card, Jumbotron, Row, Col, Dropdown, Button } from "react-bootstrap";
import * as yup from "yup";
import { AccessStatus, MiniSimulation, Simulation, RemoteOutputs } from "../types";
import { FormikActions, Formik, ErrorMessage, Field, Form } from "formik";
import { Message } from "../fields";
import moment = require("moment");
import API from "./API";

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
  preview: boolean;
  showTitleBorder: boolean;
  showAuth: boolean;
  parentSims?: Array<MiniSimulation>;
}>;


const HistoryDropDown: React.FC<{ history: Array<MiniSimulation> }> = ({ history }) => {
  return (
    <Dropdown>
      <Dropdown.Toggle variant="dark" id="dropdown-basic" className="w-100" style={{ backgroundColor: "rgba(60, 62, 62, 1)" }}>
        History
      </Dropdown.Toggle>
      <Dropdown.Menu>
        {history.map((sim, ix) => {

          return (
            <Dropdown.Item key={ix} href={sim.gui_url} style={{ minWidth: "500px" }}>
              <Row>
                <Col className="col-3">{sim.model_pk}</Col>
                <Col className="col-3">{sim.title}</Col>
                <Col className="col-3">by {sim.owner}</Col>
                <Col className="col-3">on {moment(sim.creation_date).format("YYYY-MM-DD")}</Col>
              </Row>
            </Dropdown.Item>
          );
        })}
      </Dropdown.Menu>
    </Dropdown >
  );
}

const AuthorDropDown: React.FC<{ author: string }> = ({ author }) => {
  return (
    <Dropdown>
      <Dropdown.Toggle variant="dark" id="dropdown-basic" className="w-100" style={{ backgroundColor: "rgba(60, 62, 62, 1)" }}>
        Author
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
  constructor(props) {
    super(props);
    this.state = {
      initialValues: null,
      preview: true,
      parentSims: null,
      showAuth: false,
      showTitleBorder: false,
    };
    this.togglePreview = this.togglePreview.bind(this);
    this.writable = this.writable.bind(this);
    this.forkSimulation = this.forkSimulation.bind(this);
  }

  writable() {
    return (
      ["profile", "customer"].includes(this.props.accessStatus.user_status) &&
      this.user() === this.props.remoteSim?.owner
    );
  }

  togglePreview() {
    if (this.writable()) {
      this.setState({ preview: !this.state.preview });
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
      }); // TODO: catch error on pending objs
    }
  }

  render() {
    let api = this.props.api;
    let { preview, showTitleBorder } = this.state;

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
            this.setState({ preview: true })
          })
        }}
        validationSchema={Schema}
        render={({ values, handleSubmit, setFieldValue }) => (
          <Form>
            <Card className="card-outer">
              <Card.Body>
                <Row className="mt-1 mb-1 justify-content-start">
                  <Col className="col-5">
                    <Field name="title">
                      {({
                        field,
                        form: { touched, errors },
                        meta,
                      }) => {
                        const inline = { display: "inline-block" }

                        return (preview ?
                          <Card
                            style={showTitleBorder ? {} : { border: 0 }}
                            onMouseEnter={() => this.writable() ? this.setState({ showTitleBorder: true }) : null}
                            onMouseLeave={() => this.writable() ? this.setState({ showTitleBorder: false }) : null}
                          >
                            <h3 style={inline} onClick={this.togglePreview}>{field.value}</h3>
                          </Card> :
                          <Card style={{ border: 0 }} >
                            <input type="text" placeholder="Untitled Simulation" {...field} className="form-cotnrol" onBlur={handleSubmit} />
                          </Card>);
                      }}
                    </Field>
                    <ErrorMessage
                      name="title"
                      render={msg => <Message msg={msg} />}
                    />
                  </Col>
                </Row>
              </Card.Body>
            </Card>
            <Card className="text-center" style={{ backgroundColor: "inherit", border: 0, paddingLeft: 0, paddingRight: 0 }}>
              <Card.Body style={{ paddingLeft: "1rem", paddingRight: "1rem" }}>
                <Row className="justify-content-left">
                  <Col className="col-2" style={{ paddingLeft: 0 }}>
                    <AuthorDropDown author={owner} />
                  </Col>
                  <Col className="col-2" >
                    <HistoryDropDown history={this.props.remoteSim?.parent_sims || []} />
                  </Col>
                  <Col className="col-2">
                    <Button onClick={this.forkSimulation} variant="dark" style={{ backgroundColor: "rgba(60, 62, 62, 1)" }} >
                      Copy Simulation
                    </Button>
                  </Col>
                  {this.writable() ?
                    <Col className="col-2" style={{ paddingRight: 0 }}>
                      <Button variant="dark" style={{ backgroundColor: "rgba(60, 62, 62, 1)" }} className="mb-4 w-100" onClick={e => {
                        e.target.value = !values.is_public;
                        setFieldValue("is_public", !values.is_public);
                        // put handleSubmit in setTimeout since setFieldValue is async
                        // but does not return a promise
                        // https://github.com/jaredpalmer/formik/issues/529
                        setTimeout(() => handleSubmit(e), 0);
                      }}>
                        {values.is_public ?
                          <><img className="mr-1" src="https://cdnjs.cloudflare.com/ajax/libs/octicons/8.5.0/svg/eye.svg" alt="public" /> public</> :
                          <><img className="mr-1" src="https://cdnjs.cloudflare.com/ajax/libs/octicons/8.5.0/svg/eye-closed.svg" alt="private" />private</>}
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
