"use strict";

import * as React from "react";
import ReactLoading from "react-loading";
import { FastField, ErrorMessage, FormikTouched } from "formik";
import { isEqual, isEmpty } from "lodash/lang";
import * as yup from "yup";

import { makeID, valForForm } from "./utils";
import { RedMessage, getField, CPIField } from "./fields";
import {
  ParamToolsParam,
  ParamToolsConfig,
  InitialValues,
  APIData,
  Sects
} from "./types";
import { Card, Button, OverlayTrigger, Tooltip } from "react-bootstrap";

export const ParamElement: React.FC<{
  param_data: ParamToolsParam;
  checkbox?: React.Component;
  id: string;
  classes?: string;
}> = ({ param_data, checkbox, id, classes = "row has-statuses col-xs-12" }) => {
  let tooltip = <div />;
  if (param_data.description) {
    tooltip = (
      <OverlayTrigger
        trigger={["hover", "click"]}
        overlay={
          <Tooltip id={`${id}-tooltip`}>{param_data.description}</Tooltip>
        }
      >
        <span className="d-inline-block">
          <label>
            <i className="fas fa-info-circle" />
          </label>
        </span>
      </OverlayTrigger>
    );
  }
  return (
    <div className={classes}>
      <label id={id}>
        {param_data.title} {tooltip} {!!checkbox ? checkbox : null}
      </label>
    </div>
  );
};

export const SectionHeader: React.FC<{
  title: string;
  titleSize: string;
  titleClass?: string;
  label: string;
  openDefault?: boolean;
}> = ({ title, titleSize, titleClass, label, openDefault = true }) => {
  const [open, setOpen] = React.useState(openDefault);
  return (
    <h1
      style={{ fontSize: titleSize }}
      className={titleClass ? titleClass : ""}
    >
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
          <i className={`far fa-${open ? "minus" : "plus"}-square`} />
        </button>
      </div>
    </h1>
  );
};

export const LoadingElement: React.FC<{}> = () => {
  const loading = <ReactLoading type="spokes" color="#2b2c2d" />;
  return (
    <div className="row">
      <div className="col-sm-4">
        <ul className="list-unstyled components sticky-top scroll-y">
          <li>
            <div className="card card-body card-outer">
              <div className="d-flex justify-content-center">{loading}</div>
            </div>
          </li>
        </ul>
      </div>
      <div className="col-sm-8">
        <div className="card card-body card-outer">
          <div className="d-flex justify-content-center">{loading}</div>
        </div>
      </div>
    </div>
  );
};

const MetaParametersComponent: React.FC<{
  meta_parameters: APIData["meta_parameters"];
  values: InitialValues["meta_parameters"];
  touched: FormikTouched<InitialValues>;
  resetInitialValues: (metaParameters: { [metaParam: string]: any }) => any;
}> = ({ meta_parameters, values, touched, resetInitialValues }) => {
  let isTouched = "meta_parameters" in touched;
  return (
    <div className="card card-body card-outer">
      <div className="form-group">
        <ul className="list-unstyled components">
          {Object.entries(meta_parameters).map(function(mp_item, ix) {
            let paramName = `${mp_item[0]}`;
            let fieldName = `meta_parameters.${paramName}`;
            return (
              <li key={fieldName} className="mb-3 mt-1">
                <ParamElement
                  param_data={meta_parameters[paramName]}
                  id={fieldName}
                  classes=""
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
};

export const MetaParameters = React.memo(
  MetaParametersComponent,
  (prevProps, nextProps) => {
    return isEqual(prevProps.values, nextProps.values);
  }
);

const ValueComponent: React.FC<{
  fieldName: string;
  placeholder: string;
  colClass: string;
  data: ParamToolsParam;
  isTouched: boolean;
  extend: boolean;
  label: string;
}> = ({ fieldName, placeholder, colClass, data, isTouched, extend, label }) => {
  let style = isTouched ? { backgroundColor: "rgba(102, 175, 233, 0.2)" } : {};
  return (
    <div className={colClass} key={makeID(fieldName)}>
      {label ? <small style={{ padding: 0 }}>{label}</small> : null}
      {getField(fieldName, data, placeholder, style, extend)}
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

const ParamComponent: React.FC<{
  param: string;
  msect: string;
  data: ParamToolsParam;
  values: InitialValues["adjustment"]["msect"]["paramName"];
  extend: boolean;
  meta_parameters: ParamToolsConfig;
}> = ({ param, msect, data, values, extend, meta_parameters }) => {
  let checkbox;
  let colClass;
  if (Object.keys(data.form_fields).length == 1) {
    colClass = "col-6";
  } else if (
    data.type === "bool" ||
    (!!data.validators && data.validators.choice)
  ) {
    colClass = "col-md-auto";
  } else {
    colClass = "col";
  }
  if ("checkbox" in data || "indexed" in data) {
    let checkbox = (
      <FastField
        name={`adjustment.${msect}.${param}.checkbox`}
        placeholder={data.checkbox}
        component={CPIField}
      />
    );
  } else {
    checkbox = null;
  }
  let paramElement = (
    <ParamElement
      param_data={data}
      checkbox={checkbox}
      id={`adjustment.${msect}.${param}`}
    />
  );
  return (
    <div className="container mb-3" style={{ padding: "left 0" }} key={param}>
      {paramElement}
      <div className="form-row has-statuses" style={{ marginLeft: "-20px" }}>
        {Object.entries(data.form_fields).map(function(form_field, ix) {
          let labels = form_field[0];
          let vo = data.value[ix];
          let commaSepLabs = Object.entries(vo)
            .filter(item => item[0] != "value" && !(item[0] in meta_parameters))
            .map(item => item[1])
            .join(",");
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
              extend={extend}
              label={commaSepLabs}
            />
          );
        })}
      </div>
    </div>
  );
};

export const Param = React.memo(ParamComponent, (prevProps, nextProps) => {
  return isEqual(prevProps.values, nextProps.values);
});

const Section2Component: React.FC<{
  section_2: string;
  param_list: Array<string>;
  msect: string;
  model_parameters: APIData["model_parameters"];
  values: InitialValues["adjustment"]["msect"];
  extend: boolean;
  meta_parameters: APIData["meta_parameters"];
}> = ({
  section_2,
  param_list,
  msect,
  model_parameters,
  values,
  extend,
  meta_parameters
}) => {
  let section_2_id = makeID(section_2);
  return (
    <div key={section_2_id} className="mb-2">
      <h3 className="mb-1">{section_2}</h3>
      {param_list.map(function(param) {
        return (
          <Param
            key={`${param}-component`}
            param={param}
            msect={msect}
            data={model_parameters[msect][param]}
            values={values[param]}
            extend={extend}
            meta_parameters={meta_parameters}
          />
        );
      })}
    </div>
  );
};

const Section2 = React.memo(Section2Component, (prevProps, nextProps) => {
  for (const param of prevProps.param_list) {
    if (!isEqual(prevProps.values[param], nextProps.values[param])) {
      return false;
    }
  }
  return true;
});

const Section1Component: React.FC<{
  section_1: string;
  section_2_dict: { [section_2: string]: Array<string> };
  msect: string;
  model_parameters: APIData["model_parameters"];
  values: InitialValues["adjustment"]["msect"];
  extend: boolean;
  meta_parameters: APIData["meta_parameters"];
}> = ({
  section_1,
  section_2_dict,
  msect,
  model_parameters,
  values,
  extend,
  meta_parameters
}) => {
  let section_1_id = makeID(section_1);
  return (
    <div className="inputs-block" id={section_1_id} key={section_1_id}>
      <div
        className="card card-body card-outer mb-3 shadow-sm"
        style={{ padding: "1rem" }}
      >
        <SectionHeader
          title={section_1}
          titleSize={"2.5rem"}
          label="section-1"
        />
        <div
          className="collapse show collapse-plus-minus"
          id={`${makeID(section_1)}-collapse-section-1`}
        >
          <div
            className="card card-body card-inner mb-3"
            style={{ padding: "0rem" }}
          >
            {Object.entries(section_2_dict).map(function(param_list_item, ix) {
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
                  extend={extend}
                  meta_parameters={meta_parameters}
                />
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

const Section1 = React.memo(Section1Component, (prevProps, nextProps) => {
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
});

const MajorSectionComponent: React.FC<{
  msect: string;
  section_1_dict: {
    [section_1: string]: { [section_2: string]: Array<string> };
  };
  meta_parameters: APIData["meta_parameters"];
  model_parameters: APIData["model_parameters"];
  values: InitialValues;
  extend: boolean;
}> = ({
  msect,
  section_1_dict,
  meta_parameters,
  model_parameters,
  values,
  extend
}) => {
  return (
    <div className="card card-body card-outer" key={msect} id={makeID(msect)}>
      <SectionHeader title={msect} titleSize="2.9rem" label="major" />
      <hr className="mb-1" style={{ borderTop: "0" }} />
      <div
        className="collapse show collapse-plus-minus"
        id={`${makeID(msect)}-collapse-major`}
      >
        <div className="card card-body card-inner" style={{ padding: "0rem" }}>
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
                values={values.adjustment[msect]}
                extend={extend}
                meta_parameters={meta_parameters}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};

export const MajorSection = React.memo(
  MajorSectionComponent,
  (prevProps, nextProps) => {
    return isEqual(
      prevProps.values.adjustment[prevProps.msect],
      nextProps.values.adjustment[prevProps.msect]
    );
  }
);

export const SectionHeaderList: React.FC<{ sects: Sects }> = ({ sects }) => {
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

export const PreviewComponent: React.FC<{
  values: InitialValues;
  schema: yup.Schema<any>;
  tbLabelSchema: yup.Schema<any>;
  transformfunc: any;
  extend: boolean;
}> = ({ values, schema, tbLabelSchema, transformfunc, extend }) => {
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
      adjustment: model_parameters
    });
  };
  return (
    <Card className="card-outer">
      <Card className="card-body card-inner mt-1 mb-1">
        <SectionHeader
          title="Preview"
          titleSize="2.0rem"
          titleClass="font-italic"
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
          <Button variant="outline-success" className="col-3" onClick={onClick}>
            Refresh
          </Button>
        </div>
      </Card>
    </Card>
  );
};

export const Preview = React.memo(PreviewComponent, (prevProps, nextProps) => {
  return isEqual(prevProps.values, nextProps.values);
});

export const ErrorCard: React.FC<{
  errorMsg: JSX.Element;
  errors: {
    [sect: string]: {
      errors: { [paramName: string]: Array<string> };
    };
  };
  model_parameters: APIData["model_parameters"];
}> = ({ errorMsg, errors, model_parameters = null }) => {
  const getTitle = (sect, paramName) => {
    if (
      !!model_parameters &&
      sect in model_parameters &&
      paramName in model_parameters[sect]
    ) {
      return [true, model_parameters[sect][paramName].title];
    } else {
      return [false, paramName];
    }
  };
  return (
    <Card className="card-outer">
      <Card.Body>
        <div className="alert alert-danger">{errorMsg}</div>
        {Object.entries(errors).map(([sect, sect_errors]) => {
          return !isEmpty(sect_errors.errors) ? (
            <div key={`${sect}-error`} className="alert alert-danger">
              <h5>{sect}</h5>
              {Object.entries(sect_errors.errors).map(([paramName, msgs]) => {
                let [exists, title] = getTitle(sect, paramName);
                if (!Array.isArray(msgs)) {
                  msgs = [msgs];
                }
                return (
                  <div key={`${sect}-${paramName}-error`}>
                    <p>
                      <b>{`${title}:`}</b>
                    </p>
                    <ul className="list-unstyled">
                      <li className="ml-2">
                        <ul>
                          {msgs.map((msg, ix) => (
                            <li key={`msg-${ix}`}>{msg}</li>
                          ))}{" "}
                          {exists ? (
                            <li className="list-unstyled">
                              <a href={`#adjustment.${sect}.${paramName}`}>
                                [link]
                              </a>
                            </li>
                          ) : null}
                        </ul>
                      </li>
                    </ul>
                  </div>
                );
              })}
            </div>
          ) : (
            <div key={`${sect}-error`} />
          );
        })}
      </Card.Body>
    </Card>
  );
};
