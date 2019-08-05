"use strict";

import React from "react";
import ReactLoading from "react-loading";
import { FastField, ErrorMessage, setNestedObjectValues } from "formik";
import { isEqual, isEmpty } from "lodash/lang";

import { makeID, valForForm } from "./utils";
import { RedMessage, getField, CPIField } from "./fields";
import { Card, Button } from "react-bootstrap";

export const ParamElement = ({ param_data, checkbox, id }) => {
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
      <label id={id}>
        {param_data.title} {tooltip} {!!checkbox ? checkbox : null}
      </label>
    </div>
  );
};

export const SectionHeader = ({ title, size, label, openDefault = true }) => {
  const [open, setOpen] = React.useState(openDefault);
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
          onClick={e => setOpen(!open)}
        >
          <i
            className={`far fa-${open ? "minus" : "plus"}-square`}
            style={{ size: "5px" }}
          />
        </button>
      </div>
    </h1>
  );
};

export const LoadingElement = () => {
  return (
    <div className="row">
      <div className="col-sm-4">
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
      <div className="col-sm-8">
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
  ({ meta_parameters, values, touched, resetInitialValues }) => {
    let isTouched = "meta_parameters" in touched;
    return (
      <div className="card card-body card-outer">
        <div className="inputs-block">
          <ul className="list-unstyled components">
            {Object.entries(meta_parameters).map(function(mp_item, ix) {
              let paramName = `${mp_item[0]}`;
              let fieldName = `meta_parameters.${paramName}`;
              return (
                <li key={fieldName}>
                  <ParamElement
                    param_data={meta_parameters[paramName]}
                    id={fieldName}
                  />
                  {getField(
                    fieldName,
                    mp_item[1],
                    valForForm(mp_item[1].value[0].value)
                  )}
                  <ErrorMessage
                    name={fieldName}
                    render={msg => <RedMessage msg={msg} />}
                  />
                </li>
              );
            })}
            <li>
              {isTouched ? (
                <p className="form-text text-muted">
                  Click Reset to update the default values of the parameters.
                </p>
              ) : (
                <div />
              )}
            </li>
          </ul>
        </div>
        <button
          name="reset"
          className="btn btn-block btn-outline-dark mt-3"
          onClick={e => {
            e.preventDefault();
            resetInitialValues(values);
          }}
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

const ValueComponent = ({
  fieldName,
  placeholder,
  colClass,
  data,
  isTouched
}) => {
  let style = isTouched ? { backgroundColor: "rgba(102, 175, 233, 0.2)" } : {};
  return (
    <div className={colClass} key={makeID(fieldName)}>
      {getField(fieldName, data, placeholder, style, true)}
      {isTouched ? (
        <small className="ml-2" style={{ color: "#869191" }}>
          Default: {placeholder}
        </small>
      ) : null}
      <ErrorMessage name={fieldName} render={msg => <RedMessage msg={msg} />} />
    </div>
  );
};

const Value = React.memo(ValueComponent);

export const Param = React.memo(
  ({ param, msect, data, values }) => {
    if (Object.keys(data.form_fields).length == 1) {
      var colClass = "col-6";
    } else if (
      data.type === "bool" ||
      (!!data.validators && data.validators.choice)
    ) {
      var colClass = "col-md-auto";
    } else {
      var colClass = "col";
    }
    if ("checkbox" in data) {
      var checkbox = (
        <FastField
          name={`adjustment.${msect}.${param}.checkbox`}
          placeholder={data.checkbox}
          component={CPIField}
        />
      );
    } else {
      var checkbox = null;
    }
    var paramElement = (
      <ParamElement
        param_data={data}
        checkbox={checkbox}
        id={`adjustment.${msect}.${param}`}
      />
    );
    return (
      <div className="container" style={{ padding: "left 0" }} key={param}>
        {paramElement}
        <div className="form-row has-statuses" style={{ marginLeft: "-20px" }}>
          {Object.entries(data.form_fields).map(function(form_field, ix) {
            let labels = form_field[0];
            let fieldName = `adjustment.${msect}.${param}.${labels}`;
            let placeholder = valForForm(form_field[1]);
            let isTouched = false;
            if (labels in values) {
              isTouched = Array.isArray(values[labels])
                ? values[labels].length > 0
                : !!values[labels];
            }
            return (
              <Value
                key={fieldName}
                fieldName={fieldName}
                placeholder={placeholder}
                colClass={colClass}
                data={data}
                isTouched={isTouched}
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

export const Preview = React.memo(
  ({ values, schema, tbLabelSchema, transformfunc, extend }) => {
    const [preview, setPreview] = React.useState({});
    const parseValues = () => {
      try {
        return transformfunc(values, schema, tbLabelSchema, extend);
      } catch (error) {
        return ["Something went wrong while creating the preview.", ""];
      }
    };
    const onClick = e => {
      e.preventDefault();
      const [meta_parameters, model_parameters] = parseValues();
      setPreview({
        meta_parameters: meta_parameters,
        model_parameters: model_parameters
      });
    };
    return (
      <Card className="card-outer">
        <Card className="card-body card-inner mt-1 mb-1">
          <SectionHeader
            title="Preview"
            size="2.9rem"
            label="preview"
            openDefault={false}
          />
          <div
            className="collapse collapse-plus-minus"
            id="Preview-collapse-preview"
          >
            <pre>
              <code>{JSON.stringify(preview, null, 4)}</code>
            </pre>
            <Button
              variant="outline-success"
              className="col-3"
              onClick={onClick}
            >
              Refresh
            </Button>
          </div>
        </Card>
      </Card>
    );
  },
  (prevProps, nextProps) => {
    return isEqual(prevProps.values, nextProps.values);
  }
);

export const ErrorCard = ({ errors, model_parameters = null }) => {
  const errorMsg =
    "Some fields have errors. These must be fixed " +
    "before the simulation can be submitted.";
  const getTitle = (msect, paramName) => {
    if (
      !!model_parameters &&
      msect in model_parameters &&
      paramName in model_parameters[msect]
    ) {
      return model_parameters[msect][paramName].title;
    } else {
      return paramName;
    }
  };
  return (
    <Card className="card-outer">
      <Card.Body>
        <div className="alert alert-danger">
          <p>{errorMsg}</p>
        </div>
        {Object.entries(errors).map(([msect, errors], ix) => {
          return !isEmpty(errors.errors) ? (
            <div key={`${msect}-error`} className="alert alert-danger">
              <h4>{msect}</h4>
              {Object.entries(errors.errors).map(([paramName, msg], ix) => {
                return (
                  <div key={`${msect}-${paramName}-error`}>
                    <p>{`${getTitle(msect, paramName)}:`}</p>
                    <ul className="list-unstyled">
                      <li className="ml-2">
                        {msg}{" "}
                        <a href={`#adjustment.${msect}.${paramName}`}>[link]</a>
                      </li>
                    </ul>
                  </div>
                );
              })}
            </div>
          ) : (
            <div key={`${msect}-error`} />
          );
        })}
      </Card.Body>
    </Card>
  );
};
