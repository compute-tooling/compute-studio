"use strict";

import * as React from "react";
import { Card, Jumbotron, Row, Col, Dropdown } from "react-bootstrap";
import ReactLoading from "react-loading";
import * as yup from "yup";
import { AccessStatus, MiniSimulation, Simulation, RemoteOutput, RemoteOutputs } from "./types";
import { FormikActions, Formik, ErrorMessage, Field, Form } from "formik";
import { Message } from "./fields";
import moment = require("moment");
import { RequireLoginDialog } from "./modal";
import API from "./API";

interface DescriptionProps {
  accessStatus: AccessStatus;
  api: API;
  remoteSim: Simulation<RemoteOutputs>;
}

interface DescriptionValues {
  title: string,
}


let Schema = yup.object().shape({
  title: yup.string(),
});


type DescriptionState = Readonly<{
  initialValues: DescriptionValues
  preview: Boolean;
  showAuth: Boolean;
  parentSims?: Array<MiniSimulation>;
}>;


const HistoryDropDown: React.FC<{ history: Array<MiniSimulation> }> = ({ history }) => {

  return (
    < Dropdown >
      <Dropdown.Toggle variant="outline-dark" id="dropdown-basic">
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
    };
    this.togglePreview = this.togglePreview.bind(this);
    this.writable = this.writable.bind(this);
  }

  writable() {
    return (
      ["profile", "customer"].includes(this.props.accessStatus.user_status) &&
      this.user() === this.props.remoteSim?.owner
    );
  }

  togglePreview() {
    event.preventDefault();
    if (this.writable()) {
      this.setState({ preview: !this.state.preview });
    }
  }

  user() {
    return this.props.accessStatus && this.props.accessStatus.username ?
      this.props.accessStatus.username : "anon"
  }

  render() {
    let style = this.state.preview ? {
      border: 0
    } : {}
    let api = this.props.api;
    let { preview } = this.state;

    let title, owner;
    if (this.props.remoteSim) {
      title = this.props.remoteSim.title;
      owner = this.props.remoteSim.owner;
    } else {
      title = "Untitled Simulation";
      owner = this.user();
    }
    return (
      <Jumbotron className="shadow" style={{ backgroundColor: "white" }}>
        <Formik
          initialValues={{ title: title }}
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
          render={({ values, handleSubmit }) => (
            <Form>
              <Row className="mt-1 mb-1 justify-content-start">
                <Col className="col-5">
                  <Field name="title">
                    {({
                      field,
                      form: { touched, errors },
                      meta,
                    }) => (
                        preview ?
                          <Card style={style} onClick={this.togglePreview}>
                            <h1>{field.value}</h1>
                          </Card> :
                          <Card style={{ border: 0 }}>
                            <input type="text" placeholder="Untitled Simulation" {...field} className="form-cotnrol" onBlur={handleSubmit} />
                          </Card>
                      )}
                  </Field>
                  <ErrorMessage
                    name="title"
                    render={msg => <Message msg={msg} />}
                  />
                </Col>
                <Col className="col-1 offset-md-2">
                  <HistoryDropDown history={this.props.remoteSim?.parent_sims || []} />
                </Col>
              </Row>
              <Row className="justify-content-start">
                <Col className="col-4">
                  <Card style={{ border: 0 }}>
                    <h5 className="mt-1">by {owner}</h5>
                  </Card>
                </Col>
              </Row>
            </Form>
          )}
        />
      </Jumbotron>
    );
  }
}
