"use strict";

import React from "react";
import ReactLoading from "react-loading";
import { Field, FastField, ErrorMessage } from "formik";

import { makeID, valForForm } from "./utils";
import { RedMessage } from "./fields";

export const ParamElement = ({ param_data }) => {
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

export const SectionHeader = ({ title, size, label }) => {
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

export const LoadingElement = () => {
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

export const MetaParameters = ({ meta_parameters, ...props }) => {
  return (
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
  );
}

export const MajorSection = ({ msect, section_1_dict, model_parameters, ...props }) => {

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
    </div>);
}
