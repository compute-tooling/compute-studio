"use strict";

import ReactDOM from "react-dom";
import React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import axios from "axios";
import { Formik, Field, FastField, Form, ErrorMessage } from "formik";
import * as Yup from "yup";
import { Message } from "./fields";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const domContainer = document.querySelector("#inputs-container");
const requiredMessage = "This field is required.";

var Schema = Yup.object().shape({});

const initialValues = {};

function makeID(title) {
  return title.replace(" ", "-");
}

function yupType(type) {
  if (type == "int") {
    return Yup.number().integer();
  } else if (type == "float") {
    return Yup.number();
  } else if (type == "bool") {
    return Yup.bool();
  } else if (type == "date") {
    return Yup.date();
  } else {
    return Yup.string();
  }
}

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

const SectionHeader = (...props) => {
  let title = props[0].title;
  let size = props[0].size;
  let label = props[0].label;
  return (
    <h1 style={{ fontSize: { size } }}>
      {title}
      <div className="float-right">
        <button
          className="btn collapse-button"
          type="button"
          data-toggle="collapse"
          data-target={`#${makeID(title)}-collapse-${label}`}
          aria-expanded="false"
          aria-controls={`${makeID(title)}-collapse-${label}`}
          style={{ marginLeft: "20px" }}
        >
          <i className="far fa-minus-square" style={{ size: "5px" }} />
        </button>
      </div>
    </h1>
  );
};

class InputsForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      initialValues: this.props.initialValues,
      sects: false,
      model_parameters: false
    };
  }

  componentDidMount() {
    if (this.props.fetchInitialValues) {
      this.props.fetchInitialValues().then(data => {
        var initialValues = {};
        var sects = {};
        var section_1 = "";
        var section_2 = "";
        var yupSchema = Yup.object();
        for (const [msect, params] of Object.entries(data.model_parameters)) {
          sects[[msect]] = {};
          for (const [param, param_data] of Object.entries(params)) {
            param_data["form_fields"] = {};
            // Group by major section, section_1 and section_2.
            // console.log("param", param, param_data, section_1, section_2);
            if ("section_1" in param_data) {
              section_1 = param_data.section_1;
            } else {
              section_1 = "";
            }
            if ("section_2" in param_data) {
              section_2 = param_data.section_2;
            } else {
              section_2 = "";
            }
            // console.log(section_1, section_2);
            if (!(section_1 in sects[[msect]])) {
              sects[[msect]][[section_1]] = {};
            }
            if (!(section_2 in sects[[msect]][[section_1]])) {
              sects[[msect]][[section_1]][[section_2]] = [];
            }
            sects[[msect]][[section_1]][[section_2]].push(param);
            // console.log(param);
            // console.log("getting yupObj", param_data.type);
            var yupObj = yupType(param_data.type);
            // console.log("yup", yupObj);
            if ("validators" in param_data && param_data.type != "bool") {
              if ("range" in param_data.validators) {
                var min_val = null;
                var max_val = null;
                if ("min" in param_data.validators.range) {
                  min_val = param_data.validators.range.min;
                  // console.log("minval", min_val);
                  if (!(min_val in params)) {
                    yupObj = yupObj.min(min_val);
                  }
                }
                if ("max" in param_data.validators.range) {
                  max_val = param_data.validators.range.max;
                  if (!(max_val in params)) {
                    yupObj = yupObj.max(max_val);
                  }
                }
                // console.log("yupObj", yupObj, min_val, max_val);
              }
            }
            // console.log("success w creation");

            // Define form_fields from value objects.
            for (const vals of param_data.value) {
              var s = [];
              for (const [label, label_val] of Object.entries(vals).sort()) {
                if (label == "value") {
                  continue;
                }
                s.push(`${label}__${label_val}`);
              }
              if (s.length == 0) {
                s.push("nolabels");
              }
              var field_name = `${param}.${s.join("___")}`;
              initialValues[field_name] = "";
              param_data.form_fields[field_name] = vals.value;
              // yupShape[field_name] = yupObj;
              yupSchema.shape({ [field_name]: yupObj });
            }
          }
        }
        console.log("data set");
        // console.log("sects");
        // console.log(sects);
        // this.state.sects = sects;
        // this.state.model_parameters = data.model_parameters;
        // this.state.schema = yupSchema;
        var schema = Yup.object().shape({
          "CPI_offset.year__2019": Yup.number().min(-0.01)
        });
        // this.state.schema = Yup.object().shape(yupShape);
        console.log("schema created", schema);
        console.log(initialValues);
        // this.state.initialValues = initialValues;
        this.setState({
          initialValues: initialValues,
          sects: sects,
          model_parameters: data.model_parameters,
          schema: schema
        });
      });
    }
  }

  render() {
    if (!this.state.model_parameters || !this.state.initialValues) {
      return <p> loading.... </p>;
    }
    console.log("done loading");
    let model_parameters = this.state.model_parameters;
    let initialValues = this.state.initialValues;
    let schema = this.state.schema;
    console.log("initialValues");
    console.log(initialValues);
    console.log(model_parameters);
    return (
      <div>
        <Formik
          initialValues={initialValues}
          validationSchema={schema}
          onSubmit={(values, actions) => {
            var formdata = new FormData();
            var adjustment = {};
            for (var field in values) {
              var voList = [];
              for (const [voStr, val] of Object.entries(values[field])) {
                var vo = {};
                if (!val) {
                  continue;
                }
                if (voStr == "nolabels") {
                  vo["value"] = val;
                } else {
                  var labelsSplit = voStr.split("___");
                  for (const label of labelsSplit) {
                    var labelSplit = label.split("__");
                    vo[labelSplit[0]] = labelSplit[1];
                  }
                  vo["value"] = val;
                }
                voList.push(vo);
              }
              adjustment[field] = voList;
            }
            formdata.append("adjustment", JSON.stringify(adjustment));
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
                  {Object.entries(this.state.sects).map(function(
                    msect_item,
                    ix
                  ) {
                    // msect --> section_1: dict(dict) --> section_2: dict(list)
                    // console.log(this.state);
                    // let model_parameters = this.state.model_parameters;
                    let msect = msect_item[0];
                    let section_1_dict = msect_item[1];
                    return (
                      <div className="card card-body card-outer" key={msect}>
                        <SectionHeader
                          title={msect}
                          size="2.9rem"
                          label="major"
                        />
                        <hr className="mb-3" style={{ borderTop: "0" }} />
                        <div
                          className="collapse show collapse-plus-minus"
                          id={`${makeID(msect)}-collapse-major`}
                        >
                          <div
                            className="card card-body card-inner"
                            style={{ padding: "0rem" }}
                          >
                            {Object.entries(section_1_dict).map(function(
                              section_2_item,
                              ix
                            ) {
                              let section_1 = section_2_item[0];
                              let section_1_id = section_1.replace(" ", "-");
                              let section_2_dict = section_2_item[1];
                              return (
                                <div
                                  className="inputs-block"
                                  id={section_1_id}
                                  key={section_1_id}
                                >
                                  <div
                                    className="card card-body card-outer mb-3 shadow-sm"
                                    style={{ padding: "1rem" }}
                                  >
                                    <SectionHeader
                                      title={section_1}
                                      size={"1rem"}
                                      label="section-1"
                                    />
                                    <div
                                      className="collapse show collapse-plus-minus"
                                      id={`${makeID(
                                        section_1
                                      )}-collapse-section-1`}
                                    >
                                      <div
                                        className="card card-body card-inner mb-3"
                                        style={{ padding: "0rem" }}
                                      >
                                        {Object.entries(section_2_dict).map(
                                          function(param_list_item, ix) {
                                            let section_2 = param_list_item[0];
                                            let param_list = param_list_item[1];
                                            return (
                                              <div key={section_2}>
                                                <h3>{section_2}</h3>
                                                {param_list.map(function(
                                                  param
                                                ) {
                                                  let data =
                                                    model_parameters[[msect]][
                                                      [param]
                                                    ];
                                                  if (
                                                    Object.keys(
                                                      data.form_fields
                                                    ).length == 1
                                                  ) {
                                                    var colClass = "col-6";
                                                  } else {
                                                    var colClass = "col";
                                                  }
                                                  var param_element = (
                                                    <ParamElement
                                                      param_data={data}
                                                    />
                                                  );
                                                  return (
                                                    <div
                                                      className="container"
                                                      style={{
                                                        padding: "left 0"
                                                      }}
                                                      key={param}
                                                    >
                                                      {param_element}
                                                      <div
                                                        className="form-row has-statuses"
                                                        style={{
                                                          marginLeft: "-20px"
                                                        }}
                                                      >
                                                        {Object.entries(
                                                          data.form_fields
                                                        ).map(function(
                                                          form_field,
                                                          ix
                                                        ) {
                                                          return (
                                                            <div
                                                              className={
                                                                colClass
                                                              }
                                                              key={
                                                                form_field[0]
                                                              }
                                                            >
                                                              <Field
                                                                className="form-control"
                                                                name={
                                                                  form_field[0]
                                                                }
                                                                placeholder={
                                                                  form_field[1]
                                                                }
                                                                // type={typeMap[data.type]}
                                                              />
                                                              <ErrorMessage
                                                                name={
                                                                  form_field[0]
                                                                }
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
                                          }
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  {/* <div className="card card-body card-outer">
                    <pre>
                      <code>
                        {JSON.stringify(this.state.initialValues, null, 4)}
                      </code>
                    </pre>
                  </div> */}
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
    // TODO post as json instead of form data.
    console.log("posting...");
    console.log(data);
    return axios
      .post(`/${username}/${app_name}/api/v1/`, data)
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
