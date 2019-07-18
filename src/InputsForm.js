"use strict";

import * as Yup from "yup";
import React from "react";
import { Formik, Field, FastField, Form, ErrorMessage } from "formik";

import { RedMessage } from "./fields";
import { ParamElement, SectionHeader, LoadingElement } from "./components";
import { LoadingModal, RunModal } from "./modal";
import { tbLabelSchema, yupValidator } from "./ParamTools";
import { makeID, valForForm } from "./utils";

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
                    vo = tbLabelSchema.cast(vo)
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
                console.log("success");
                actions.setSubmitting(false);
                console.log(response.data.pk);
                actions.setStatus({
                  status: "PENDING",
                  inputs_pk: response.data.pk,
                  api_url: response.data.api_url,
                });
              })
              .catch(error => {
                console.log("error", error);
              });
          }}
          render={({ handleSubmit, onChange, status, errors }) => (
            <Form>
              {status && status.status === "PENDING" ? (
                <LoadingModal inputs_url={status.api_url} />
              ) : <div></div>}

              <div className="row">
                <div className="col-4">
                  <ul className="list-unstyled components sticky-top scroll-y">
                    <li>
                      <div className="card card-body card-outer">
                        <div className="inputs-block">
                          <ul className="list-unstyled components">
                            {Object.entries(meta_parameters).map(function (
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
                      <RunModal handleSubmit={handleSubmit} />
                    </li>
                  </ul>
                </div>
                <div className="col-8">
                  {Object.entries(this.state.sects).map(function (
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
                            {Object.entries(section_1_dict).map(function (
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
                                          function (param_list_item, ix) {
                                            let section_2 = param_list_item[0];
                                            let param_list = param_list_item[1];
                                            return (
                                              <div key={section_2}>
                                                <h3>{section_2}</h3>
                                                {param_list.map(function (
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
                                                        ).map(function (
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


export { InputsForm }