"use strict";

import React from "react";
import ReactLoading from "react-loading";
import { Field, FastField, ErrorMessage } from "formik";
import { isEqual } from "lodash/lang";

import { makeID, valForForm, shallowEqual } from "./utils";
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
    <div className="row has-statuses col-xs-12">
      <label>
        {param_data.title} {tooltip}
      </label>
    </div>
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

export const MetaParameters = React.memo(
  ({ meta_parameters, values }) => {
    return (
      <div className="card card-body card-outer">
        <div className="inputs-block">
          <ul className="list-unstyled components">
            {Object.entries(meta_parameters).map(function(mp_item, ix) {
              let paramName = `${mp_item[0]}`;
              let fieldName = `meta_parameters.${paramName}`;
              return (
                <li key={fieldName}>
                  <ParamElement param_data={meta_parameters[paramName]} />
                  <FastField
                    value={values[paramName]}
                    name={fieldName}
                    placeholder={valForForm(mp_item[1].value[0].value)}
                  />
                  <ErrorMessage
                    name={fieldName}
                    render={msg => <RedMessage msg={msg} />}
                  />
                </li>
              );
            })}
            <li>
              <p className="form-text text-muted">
                Click Reset to update the default values of the parameters.
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
  },
  (prevProps, nextProps) => {
    return isEqual(prevProps.values, nextProps.values);
  }
);

const ValueComponent = ({ fieldName, placeholder, colClass, data }) => {
  if (data.type == "bool") {
    var el = (
      <FastField component="select" name={fieldName}>
        <option value={true}>true</option>
        <option value={false}>false</option>
      </FastField>
    );
  } else if (data.validators && data.choice && data.choice.choices) {
    var el = (
      <FastField component="select" name={fieldName}>
        {data.choice.choices.map(choice => {
          <option value={choice}>{choice}</option>;
        })}
      </FastField>
    );
  } else {
    var el = (
      <FastField
        className="form-control"
        name={fieldName}
        placeholder={placeholder}
      />
    );
  }
  return (
    <div className={colClass} key={makeID(fieldName)}>
      {el}
      <ErrorMessage name={fieldName} render={msg => <RedMessage msg={msg} />} />
    </div>
  );
};

const Value = React.memo(ValueComponent);

export const Param = React.memo(
  ({ param, msect, data, values }) => {
    if (Object.keys(data.form_fields).length == 1) {
      var colClass = "col-6";
    } else {
      var colClass = "col";
    }
    var paramElement = <ParamElement param_data={data} />;

    return (
      <div className="container" style={{ padding: "left 0" }} key={param}>
        {paramElement}
        <div className="form-row has-statuses" style={{ marginLeft: "-20px" }}>
          {Object.entries(data.form_fields).map(function(form_field, ix) {
            let labels = form_field[0];
            let fieldName = `adjustment.${msect}.${param}.${labels}`;
            let placeholder = valForForm(form_field[1]);
            return (
              <Value
                key={fieldName}
                fieldName={fieldName}
                placeholder={placeholder}
                colClass={colClass}
                data={data}
              />
            );
          })}
        </div>
      </div>
    );
  },
  (prevProps, nextProps) => {
    return isEqual(prevProps.values, nextProps.values);
  }
);

const Section2 = React.memo(
  ({ section_2, param_list, msect, model_parameters, values }) => {
    let section_2_id = makeID(section_2);
    return (
      <div key={section_2_id}>
        <h3>{section_2}</h3>
        {param_list.map(function(param) {
          return (
            <Param
              key={`${param}-component`}
              param={param}
              msect={msect}
              data={model_parameters[msect][param]}
              values={values[param]}
              // {...props}
            />
          );
        })}
      </div>
    );
  },
  (prevProps, nextProps) => {
    for (const param of prevProps.param_list) {
      if (!isEqual(prevProps.values[param], nextProps.values[param])) {
        return false;
      }
    }
    return true;
  }
);

const Section1 = React.memo(
  ({ section_1, section_2_dict, msect, model_parameters, values }) => {
    let section_1_id = makeID(section_1);
    return (
      <div className="inputs-block" id={section_1_id} key={section_1_id}>
        <div
          className="card card-body card-outer mb-3 shadow-sm"
          style={{ padding: "1rem" }}
        >
          <SectionHeader title={section_1} size={"1rem"} label="section-1" />
          <div
            className="collapse show collapse-plus-minus"
            id={`${makeID(section_1)}-collapse-section-1`}
          >
            <div
              className="card card-body card-inner mb-3"
              style={{ padding: "0rem" }}
            >
              {Object.entries(section_2_dict).map(function(
                param_list_item,
                ix
              ) {
                let section_2 = param_list_item[0];
                let param_list = param_list_item[1];
                return (
                  <Section2
                    key={`${makeID(section_2)}-component`}
                    section_2={section_2}
                    param_list={param_list}
                    msect={msect}
                    model_parameters={model_parameters}
                    values={values}
                  />
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  },
  (prevProps, nextProps) => {
    for (const [section2, paramList] of Object.entries(
      prevProps.section_2_dict
    )) {
      for (const param of paramList) {
        if (!isEqual(prevProps.values[param], nextProps.values[param])) {
          return false;
        }
      }
    }
    return true;
  }
);

export const MajorSection = React.memo(
  ({ msect, section_1_dict, model_parameters, ...props }) => {
    return (
      <div className="card card-body card-outer" key={msect}>
        <SectionHeader title={msect} size="2.9rem" label="major" />
        <hr className="mb-3" style={{ borderTop: "0" }} />
        <div
          className="collapse show collapse-plus-minus"
          id={`${makeID(msect)}-collapse-major`}
        >
          <div
            className="card card-body card-inner"
            style={{ padding: "0rem" }}
          >
            {Object.entries(section_1_dict).map(function(section_2_item, ix) {
              let section_1 = section_2_item[0];
              let section_2_dict = section_2_item[1];
              return (
                <Section1
                  key={`${makeID(section_1)}-component`}
                  section_1={section_1}
                  section_2_dict={section_2_dict}
                  msect={msect}
                  model_parameters={model_parameters}
                  values={props.values.adjustment[msect]}
                />
              );
            })}
          </div>
        </div>
      </div>
    );
  },
  (prevProps, nextProps) => {
    return isEqual(
      prevProps.values.adjustment[prevProps.msect],
      nextProps.values.adjustment[prevProps.msect]
    );
  }
);

export const SectionHeaderList = ({ sects }) => {
  return (
    <div className="card card-body card-outer">
      {Object.entries(sects).map(([msect, section1], ix) => {
        return (
          <div
            className="card card-body card-inner mb-1 mr-1"
            key={`${msect}-header-card`}
          >
            <div className="list-group">
              <a
                className="list-group-item list-group-item-action mt-0"
                href={`#${makeID(msect)}`}
                key={`#${makeID(msect)}-msect-panel`}
                style={{
                  border: "0px",
                  padding: "0rem",
                  color: "inherit"
                }}
              >
                <h3 style={{ color: "inherit" }}>{msect}</h3>
              </a>
              {Object.entries(section1).map(
                ([section1Title, section2Params], ix) => {
                  return (
                    <a
                      className="list-group-item list-group-item-action"
                      href={`#${makeID(section1Title)}`}
                      key={`#${makeID(section1Title)}-section1-panel`}
                      style={{
                        padding: ".3rem 0rem",
                        border: "0px",
                        color: "inherit"
                      }}
                    >
                      {section1Title}
                    </a>
                  );
                }
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
