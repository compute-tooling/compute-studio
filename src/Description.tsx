"use strict";

import * as React from "react";
import { Card, Jumbotron, Row, Col, Dropdown } from "react-bootstrap";
import ReactLoading from "react-loading";
import * as yup from "yup";
import { RemoteOutputs, AccessStatus, Simulation, MiniSimulation } from "./types";
import { FormikActions, Formik, ErrorMessage, Field, Form } from "formik";
import { Message } from "./fields";
import moment = require("moment");
import { RequireLoginDialog } from "./modal";
import API from "./API";

interface DescriptionProps {
  accessStatus: AccessStatus;
  api: API;
}

interface DescriptionValues {
  title: string,
}


let Schema = yup.object().shape({
  title: yup.string(),
});


type DescriptionState = Readonly<{
  initialValues: DescriptionValues
  owner: string;
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
                <Col className="col-4">{sim.title}</Col>
                <Col className="col-4">by {sim.owner}</Col>
                <Col className="col-4">on {moment(sim.creation_date).format("YYYY-MM-DD")}</Col>
              </Row>
            </Dropdown.Item>
          );
        })}
      </Dropdown.Menu>
    </Dropdown >
  );
}

export default class DescriptionComponent extends React.Component<
  DescriptionProps,
  DescriptionState
  > {
  constructor(props) {
    super(props);
    this.state = {
      initialValues: null,
      owner: "",
      preview: true,
      parentSims: null,
      showAuth: false,
    };
    this.togglePreview = this.togglePreview.bind(this);
    this.writable = this.writable.bind(this);
  }

  componentDidMount() {
    // fetch title, description, version
    let api = this.props.api;
    console.log("this.props.isNew", !api.modelpk, this.props.accessStatus)
    if (!api.modelpk) {
      this.setState({
        initialValues: {
          title: "Untitled Simulation",
        },
        owner: this.props.accessStatus && this.props.accessStatus.username ?
          this.props.accessStatus.username : "anon",
        parentSims: [],
      })
    } else {
      this.props.api.getRemoteOutputs().then(data => {
        console.log("got data", data);
        this.setState({
          initialValues: {
            title: data.title,
          },
          owner: data.owner,
          parentSims: data.parent_sims,
        });
      });
    }
  }

  writable() {
    return (
      ["profile", "customer"].includes(this.props.accessStatus.user_status) &&
      this.props.accessStatus.username === this.state.owner
    );
  }

  togglePreview() {
    event.preventDefault();
    if (this.writable()) {
      this.setState({ preview: !this.state.preview });
    }
  }

  render() {
    if (!this.state.initialValues) {
      return (
        <Card className="card-outer">
          <Card className="card-inner">
            <Card.Body>
              <div className="d-flex justify-content-center">
                <ReactLoading type="spokes" color="#2b2c2d" />
              </div>
            </Card.Body>
          </Card>
        </Card>
      );
    }
    if (this.state.showAuth) {
      return <RequireLoginDialog
        accessStatus={this.props.accessStatus}
        show={true}
        setShow={show => this.setState({ showAuth: !show })}
        handleSubmit={() => null}
      />
    }
    let style = this.state.preview ? {
      border: 0
    } : {}
    let api = this.props.api;
    let { parentSims, owner, preview } = this.state;
    return (
      <Jumbotron className="shadow" style={{ backgroundColor: "white" }}>
        <Formik
          initialValues={this.state.initialValues}
          onSubmit={(values: DescriptionValues, actions: FormikActions<DescriptionValues>) => {
            console.log(values);
            let formdata = new FormData();
            for (const field in values) {
              formdata.append(field, values[field]);
            }
            formdata.append("model_pk", api.modelpk.toString());
            this.props.api.putDescription(formdata).then(data => {
              console.log("success");
              this.setState({ preview: true })
            })
          }}
          validationSchema={Schema}
          render={({ values, handleSubmit }) => (
            <Form>
              {console.log("rendering with", values)}
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
                  <HistoryDropDown history={parentSims} />
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
