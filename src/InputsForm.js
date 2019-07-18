"use strict";

import * as Yup from "yup";
import React from "react";
import { Formik, Field, FastField, Form, ErrorMessage } from "formik";

import { RedMessage } from "./fields";
import { ParamElement, SectionHeader, LoadingElement } from "./components";
import { LoadingModal, RunModal } from "./modal";
import { formikToJSON, convertToFormik } from "./ParamTools";
import { makeID, valForForm } from "./utils";


// need to require schema in model_parameters!
const tbLabelSchema = Yup.object().shape({
  year: Yup.number(),
  MARS: Yup.string(),
  idedtype: Yup.string(),
  EIC: Yup.string(),
  data_source: Yup.string(),
});


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
        const [initialValues, sects, model_parameters, meta_parameters, schema] = convertToFormik(data);
        this.setState({
          initialValues: initialValues,
          sects: sects,
          model_parameters: model_parameters,
          meta_parameters: meta_parameters,
          schema: schema
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
            const [meta_parameters, adjustment] = formikToJSON(values, this.state.schema, tbLabelSchema);
            console.log("submitting");
            console.log(adjustment);
            console.log(meta_parameters);
            let formdata = new FormData();
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