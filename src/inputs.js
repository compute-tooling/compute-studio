"use strict";

import ReactDOM from "react-dom";
import React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import axios from "axios";
import { Formik, Field, Form, ErrorMessage } from "formik";
import * as Yup from "yup";
import {
  TextField,
  TextAreaField,
  CodeSnippetField,
  ServerSizeField,
  Message
} from "./fields";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const domContainer = document.querySelector("#inputs-container");
const requiredMessage = "This field is required.";
const typeMap = {
  int: "number",
  float: "number",
  bool: "string"
};

var Schema = Yup.object().shape({});

const initialValues = {};

const ParamElement = (...props) => {
  var param_data = props[0].param_data;
  var tooltip = <div />;
  if (param_data.description) {
    tooltip = (
      <label
        className="input-tooltip"
        data-toggle="tooltip"
        data-placement="top"
        title={param_data.description}
      >
        {" "}
        <i className="fas fa-info-circle" />
      </label>
    );
  }
  return (
    // <div className="container" style={{ padding: "left 0" }}>
    <div className="row has-statuses col-xs-12">
      <label>
        {param_data.title} {tooltip}
      </label>
    </div>
    // </div>
  );
};

class InputsForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      initialValues: this.props.initialValues
    };
  }

  componentDidMount() {
    if (this.props.fetchInitialValues) {
      this.props.fetchInitialValues().then(data => {
        var initialValues = {};
        for (const [msect, params] of Object.entries(data.model_parameters)) {
          for (const [param, param_data] of Object.entries(params)) {
            param_data["form_fields"] = {};
            for (const vals of param_data.value) {
              var s = [];
              for (const [label, label_val] of Object.entries(vals).sort()) {
                if (label == "value") {
                  continue;
                }
                s.push(`${label}__${label_val}`);
              }
              var field_name = `${param}.${s.join(".")}`;
              initialValues[field_name] = "";
              param_data.form_fields[field_name] = vals.value;
              // console.log(param, field_name, param_data.form_fields);
            }
          }
        }
        // console.log(initialValues);
        console.log(data.model_parameters.policy.STD);
        this.setState({ initialValues: data.model_parameters });
      });
    }
  }

  render() {
    if (!this.state.initialValues) {
      return <p> loading.... </p>;
    }
    // console.log(this.state.initialValues);
    return (
      <div>
        <Formik
          initialValues={this.state.initialValues}
          onSubmit={(values, actions) => {
            console.log(values, actions);
            var formdata = new FormData();
            for (var field in values) {
              formdata.append([field], values[field]);
            }
            this.props
              .doSubmit(formdata)
              .then(response => {
                actions.setSubmitting(false);
              })
              .catch(error => {
                console.log("error", error);
                console.log(error.response.data);
                actions.setSubmitting(false);
                if (error.response.status == 400) {
                  actions.setStatus(error.response.data);
                } else if (error.response.status == 401) {
                  actions.setStatus({
                    auth: "You must be logged in to publish a model."
                  });
                }
              });
          }}
          validationSchema={Schema}
          render={({ onChange, status, errors }) => (
            <Form>
              <div className="row">
                <div className="col-4">
                  <ul className="list-unstyled components sticky-top scroll-y">
                    <li>
                      <div className="card card-body card-outer">
                        <p>Hello world!</p>
                        <button
                          type="submit"
                          name="reset"
                          value="true"
                          className="btn btn-block btn-outline-dark"
                        >
                          Reset
                        </button>
                      </div>
                    </li>
                    <li>
                      <div className="card card-body card-outer">
                        <button
                          type="submit"
                          className="btn btn-block btn-success"
                        >
                          <b>Run</b>
                        </button>
                      </div>
                    </li>
                  </ul>
                </div>
                <div className="col-8">
                  {Object.entries(this.state.initialValues).map(function(
                    item,
                    ix
                  ) {
                    let msect = item[0];
                    let params = item[1];
                    // console.log("msect");
                    // console.log(item);
                    // console.log(msect);
                    // console.log(params);

                    return (
                      <div className="card card-body card-outer">
                        <p>{msect}</p>
                        {Object.entries(params).map(function(param, ix) {
                          var name = param[0];
                          var data = param[1];
                          if (Object.keys(data.form_fields).length == 1) {
                            var colClass = "col-6";
                          } else {
                            var colClass = "col";
                          }
                          var param_element = (
                            <ParamElement param_data={data} />
                          );
                          return (
                            <div>
                              {param_element}
                              <div
                                className="form-row has-statuses"
                                style={{ marginLeft: "-20px" }}
                              >
                                {Object.entries(data.form_fields).map(function(
                                  form_field,
                                  ix
                                ) {
                                  return (
                                    <div className={colClass}>
                                      <Field
                                        className="form-control"
                                        name={form_field[0]}
                                        placeholder={form_field[1]}
                                        type={typeMap[data.type]}
                                      />
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })}
                  ;
                  <div className="card card-body card-outer">
                    <pre>
                      <code>
                        {JSON.stringify(this.state.initialValues, null, 4)}
                      </code>
                    </pre>
                  </div>
                </div>
              </div>
            </Form>
          )}
        />
      </div>
    );
  }
}

class InputsApp extends React.Component {
  constructor(props) {
    super(props);
    this.doSubmit = this.doSubmit.bind(this);
    this.fetchInitialValues = this.fetchInitialValues.bind(this);
  }

  fetchInitialValues() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    return axios
      .get(`/${username}/${app_name}/api/v1/inputs/`)
      .then(function(response) {
        console.log(response);
        return response.data;
      })
      .catch(function(error) {
        console.log(error);
      });
  }

  doSubmit(data) {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    return axios
      .put(`/${username}/${app_name}/api/v1/`, data)
      .then(function(response) {
        console.log(response);
        window.location.replace("/");
      });
  }

  render() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    const id = `${username}/${app_name}`;
    return (
      <InputsForm
        fetchInitialValues={this.fetchInitialValues}
        initialValues={null}
        submitType="Create"
        doSubmit={this.doSubmit}
      />
    );
  }
}

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route exact path="/:username/:app_name/" component={InputsApp} />
    </Switch>
  </BrowserRouter>,
  domContainer
);
