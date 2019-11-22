"use strict";

import * as React from "react";
import { Card, Jumbotron, Row, Col, Dropdown } from "react-bootstrap";
import ReactLoading from "react-loading";
import * as yup from "yup";
import { SimAPIData, RemoteOutputs, SimDescription } from "./types";
import { FormikActions, Formik, ErrorMessage, Field, Form } from "formik";
import { markdownElement, Message, TextAreaField } from "./fields";
import moment = require("moment");

interface DescriptionProps {
  fetchRemoteOutputs: () => Promise<SimAPIData<RemoteOutputs>>;
  putDescription: (data: FormData) => Promise<SimAPIData<RemoteOutputs>>;
  username: string;
  appname: string;
  modelPk: number;
}

interface DescriptionValues {
  title: string,
  readme: string,
}


let Schema = yup.object().shape({
  title: yup.string(),
  readme: yup.string(),
});


type DescriptionState = Readonly<{
  initialValues: DescriptionValues
  owner: string;
  lastModified: Date;
  preview: boolean;
  parentSims?: Array<SimDescription>;
}>;


const HistoryDropDown: React.FC<{ history: Array<SimDescription> }> = ({ history }) => {

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
      lastModified: null,
    };
    this.togglePreview = this.togglePreview.bind(this);
  }

  componentDidMount() {
    // fetch title, description, version
    this.props.fetchRemoteOutputs().then(data => {
      console.log("got data", data);
      this.setState({
        initialValues: {
          title: data.title,
          readme: data.readme,
        },
        owner: data.owner,
        parentSims: data.parent_sims,
        lastModified: data.last_modified,
      });
    });
  }

  togglePreview() {
    event.preventDefault();
    this.setState({ preview: !this.state.preview });
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
    let lastModified = moment(this.state.lastModified).format(
      "MMMM Do YYYY, h:mm:ss a"
    );
    let style = this.state.preview ? { border: 0 } : {}
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
            formdata.append("model_pk", this.props.modelPk.toString());
            this.props.putDescription(formdata).then(data => {
              console.log("success");
              this.setState({ preview: true, lastModified: data.last_modified })
            })
          }}
          validationSchema={Schema}
          render={({ status, values }) => (
            <Form>
              {console.log("rendering with", values)}
              <Row className="mt-1 mb-1 justify-content-start">
                <Col className="col-5">
                  <Field name="title">
                    {({
                      field, // { name, value, onChange, onBlur }
                      form: { touched, errors }, // also values, setXXXX, handleXXXX, dirty, isValid, status, etc.
                      meta,
                    }) => (
                        this.state.preview ?
                          <Card style={style} onClick={() => this.setState({ preview: false })}>
                            <h1>{field.value}</h1>
                          </Card> :
                          <Card style={{ border: 0 }}>
                            <input type="text" placeholder="Untitled Simulation" {...field} className="form-cotnrol" />
                          </Card>
                      )}
                  </Field>
                  <ErrorMessage
                    name="title"
                    render={msg => <Message msg={msg} />}
                  />
                </Col>
                <Col className="col-1 offset-md-2">
                  <HistoryDropDown history={this.state.parentSims} />
                </Col>
              </Row>
              <Row className="justify-content-start">
                <Col className="col-4">
                  <Card style={{ border: 0 }}>
                    <h5 className="mt-1">by {this.state.owner}</h5>
                  </Card>
                </Col>
              </Row>
              <Row className="mt-1 mb-1 justify-content-start">
                <Col className="col-9">
                  <hr className="my-3" />
                </Col>
              </Row>
              <Row className="mt-1 mb-1 justify-content-start">
                <Col className="col-9">
                  <Field
                    type="text"
                    name="readme"
                    component={TextAreaField}
                    placeholder="Readme"
                    label="README"
                    preview={this.state.preview}
                    exitPreview={() => this.setState({ preview: false })}
                    style={style}
                  />
                  <ErrorMessage
                    name="readme"
                    render={msg => <Message msg={msg} />}
                  />
                </Col>
              </Row>
              <Row className="justify-content-start">
                <Col className="col-3">
                  <button
                    className="btn inline-block btn-outline-primary mr-2"
                    onClick={this.togglePreview}
                  >
                    {this.state.preview ? "Edit" : "Preview"}
                  </button>
                  <button className="btn inline-block btn-success ml-2" type="submit">
                    Save
                  </button>
                </Col>
              </Row>
              <Row className="mt-2">
                <Col>
                  <p className="text-muted">Last modified: {lastModified}</p>
                </Col>
              </Row>
            </Form>
          )}
        />
      </Jumbotron>
    );
  }
}
