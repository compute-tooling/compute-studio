"use strict";

import ReactDOM from "react-dom";
import React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import axios from "axios";
import { Formik, Field, FastField, Form, ErrorMessage } from "formik";
import * as Yup from "yup";
import { RedMessage } from "./fields";
import ReactLoading from "react-loading";

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
    return Yup.number()
      .integer()
      .nullable()
      .transform(value => value === "" || value);
  } else if (type == "float") {
    return Yup.number()
      .nullable()
      .transform(value => (!value ? null : value));
  } else if (type == "bool") {
    return Yup.bool();
  } else if (type == "date") {
    return Yup.date();
  } else {
    return Yup.string();
  }
}

const minMsg = "Must be greater than or equal to ${min}";
const maxMsg = "Must be less than or equal to ${max}";
const oneOfMsg = "Must be one of the following values: ${values}";

function yupValidator(params, param_data) {
  let yupObj = yupType(param_data.type);
  if (!("validators" in param_data) || param_data.type == "bool") {
    return yupObj;
  }
  if ("range" in param_data.validators) {
    var min_val = null;
    var max_val = null;
    if ("min" in param_data.validators.range) {
      min_val = param_data.validators.range.min;
      if (!(min_val in params)) {
        yupObj = yupObj.min(min_val, minMsg);
      }
    }
    if ("max" in param_data.validators.range) {
      max_val = param_data.validators.range.max;
      if (!(max_val in params)) {
        yupObj = yupObj.max(max_val, maxMsg);
      }
    }
  }
  if ("choice" in param_data.validators) {
    yupObj = yupObj.oneOf(param_data.validators.choice.choices, oneOfMsg);
  }
  return yupObj;
}

function valForForm(val) {
  if (typeof val === "boolean") {
    return val ? "True" : "False";
  } else {
    return val;
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

const LoadingElement = () => {
  return (
    <div className="row">
      <div className="col-4">
        <ul className="list-unstyled components sticky-top scroll-y">
          <li>
            <div className="card card-body card-outer">
              <div className="d-flex justify-content-center">
                <ReactLoading type="spokes" color="#2b2c2d" />
              </div>
            </div>
          </li>
        </ul>
      </div>
      <div className="col-8">
        <div className="card card-body card-outer">
          <div className="d-flex justify-content-center">
            <ReactLoading type="spokes" color="#2b2c2d" />
          </div>
        </div>
      </div>
    </div>
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
        var initialValues = { adjustment: {}, meta_parameters: {} };
        var sects = {};
        var section_1 = "";
        var section_2 = "";
        var adjShape = {};
        for (const [msect, params] of Object.entries(data.model_parameters)) {
          var msectShape = {};
          sects[msect] = {};
          initialValues.adjustment[msect] = {};
          for (const [param, param_data] of Object.entries(params)) {
            param_data["form_fields"] = {};
            // Group by major section, section_1 and section_2.
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
            if (!(section_1 in sects[msect])) {
              sects[msect][section_1] = {};
            }
            if (!(section_2 in sects[msect][section_1])) {
              sects[msect][section_1][section_2] = [];
            }
            sects[msect][section_1][section_2].push(param);

            var yupObj = yupValidator(params, param_data);

            // Define form_fields from value objects.
            initialValues.adjustment[msect][param] = {};
            var paramYupShape = {};
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
              var field_name = `${s.join("___")}`;
              initialValues.adjustment[msect][param][field_name] = "";
              param_data.form_fields[field_name] = vals.value;
              paramYupShape[field_name] = yupObj;
            }
            msectShape[param] = Yup.object().shape(paramYupShape);
          }
          adjShape[msect] = Yup.object().shape(msectShape);
        }
        var mpShape = {};
        for (const [mp_name, mp_data] of Object.entries(data.meta_parameters)) {
          var yupObj = yupValidator(data.meta_parameters, mp_data);
          mpShape[mp_name] = yupObj;
          initialValues["meta_parameters"][mp_name] = mp_data.value[0].value;
        }

        var schema = {
          adjustment: Yup.object().shape(adjShape),
          meta_parameters: Yup.object().shape(mpShape)
        };

        this.setState({
          initialValues: initialValues,
          sects: sects,
          model_parameters: data.model_parameters,
          meta_parameters: data.meta_parameters,
          schema: Yup.object().shape(schema)
        });
      });
    }
  }

  render() {
    if (!this.state.model_parameters || !this.state.initialValues) {
      return <LoadingElement />;
    }
    console.log("rendering");
    let meta_parameters = this.state.meta_parameters;
    let model_parameters = this.state.model_parameters;
    let initialValues = this.state.initialValues;
    let schema = this.state.schema;
    return (
      <div>
        <Formik
          initialValues={initialValues}
          validationSchema={schema}
          validateOnChange={false}
          validateOnBlur={true}
          onSubmit={(values, actions) => {
            let data = this.state.schema.cast(values);
            var formdata = new FormData();
            var adjustment = {};
            var meta_parameters = {};
            for (const [msect, params] of Object.entries(data.adjustment)) {
              adjustment[msect] = {};
              for (const [paramName, paramData] of Object.entries(params)) {
                var voList = [];
                for (const [voStr, val] of Object.entries(paramData)) {
                  console.log(paramName, val, !val);
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
                if (voList.length > 0) {
                  adjustment[msect][paramName] = voList;
                }
              }
            }
            for (const [mp_name, mp_val] of Object.entries(
              data.meta_parameters
            )) {
              meta_parameters[mp_name] = mp_val;
            }
            console.log("submitting");
            console.log(adjustment);
            console.log(meta_parameters);
            formdata.append("adjustment", JSON.stringify(adjustment));
            formdata.append("meta_parameters", JSON.stringify(meta_parameters));
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
                        <div className="inputs-block">
                          <ul className="list-unstyled components">
                            {Object.entries(meta_parameters).map(function(
                              mp_item,
                              ix
                            ) {
                              let field_name = `meta_parameters.${mp_item[0]}`;
                              return (
                                <li key={field_name}>
                                  <ParamElement
                                    param_data={meta_parameters[mp_item[0]]}
                                  />
                                  <Field
                                    name={field_name}
                                    placeholder={valForForm(
                                      mp_item[1].value[0].value
                                    )}
                                  />
                                  <ErrorMessage
                                    name={field_name}
                                    render={msg => <RedMessage msg={msg} />}
                                  />
                                </li>
                              );
                            })}
                            <li>
                              <p className="form-text text-muted">
                                Click Reset to update the default values of the
                                parameters.
                              </p>
                            </li>
                          </ul>
                        </div>
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
                    // msect --> section_1: dict(dict) --> section_2: dict(dict)
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
                                                    model_parameters[msect][
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
                                                          let field_name = `adjustment.${msect}.${param}.${
                                                            form_field[0]
                                                          }`;
                                                          return (
                                                            <div
                                                              className={
                                                                colClass
                                                              }
                                                              key={field_name}
                                                            >
                                                              <FastField
                                                                className="form-control"
                                                                name={
                                                                  field_name
                                                                }
                                                                placeholder={valForForm(
                                                                  form_field[1]
                                                                )}
                                                                // type={typeMap[data.type]}
                                                              />
                                                              <ErrorMessage
                                                                name={
                                                                  field_name
                                                                }
                                                                render={msg => (
                                                                  <RedMessage
                                                                    msg={msg}
                                                                  />
                                                                )}
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
        // window.location.replace("/");
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
