"use strict";

import React from "react";
import isEqual from "react";
import ReactLoading from "react-loading";
import { Field, FastField, ErrorMessage } from "formik";

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

export const MetaParameters = React.memo(
  ({ meta_parameters, values }) => {
    console.log("meta params re-render");
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
    console.log(prevProps, nextProps);
    return shallowEqual(prevProps.values, nextProps.values);
  }
);

const ValueComponent = ({ fieldName, placeholder, propsValue, colClass }) => {
  console.log("rendering component", fieldName);
  return (
    <div className={colClass} key={makeID(fieldName)}>
      <FastField
        value={propsValue}
        className="form-control"
        name={fieldName}
        placeholder={placeholder}
      />
      <ErrorMessage name={fieldName} render={msg => <RedMessage msg={msg} />} />
    </div>
  );
};

const Value = React.memo(ValueComponent);

export const Param = ({ param, msect, data, values }) => {
  // console.log("re-rendering", param);
  // let data = model_parameters[msect][[param]];
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
          let value = values[labels];
          // console.log("value", value);
          return (
            <Value
              key={fieldName}
              fieldName={fieldName}
              placeholder={placeholder}
              value={value}
              colClass={colClass}
            />
          );
        })}
      </div>
    </div>
  );
};

// export class Param extends React.Component {
//   constructor(props){
//     super(props);
//     this.state = {
//       param: this.props.param,
//       msect: this.props.msect,
//       data: this.props.data,
//       values: this.props.values,
//       formikProps: this.props.formikProps,
//     }
//   }

//   render() {
//     let data = this.state.data;
//     let param = this.state.param;
//     return (
//       <div className="container" style={{ padding: "left 0" }} key={param}>
//       {paramElement}
//       <div className="form-row has-statuses" style={{ marginLeft: "-20px" }}>
//         {Object.entries(data.form_fields).map(function(form_field, ix) {
//           let labels = form_field[0];
//           let fieldName = `adjustment.${msect}.${param}.${labels}`;
//           let placeholder = valForForm(form_field[1]);
//           let value = values[labels];
//           // console.log("value", value);
//           return (
//             <Value
//               key={fieldName}
//               fieldName={fieldName}
//               placeholder={placeholder}
//               value={value}
//               colClass={colClass}
//             />
//           );
//         })}
//       </div>
//     </div>
//     )
//   }
// }

export const Section2 = ({
  section_2,
  param_list,
  msect,
  model_parameters,
  values
}) => {
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
};

export const Section1 = ({
  section_1,
  section_2_dict,
  msect,
  model_parameters,
  ...props
}) => {
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
                  values={props.values.adjustment[msect]}
                />
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export const MajorSection = ({
  msect,
  section_1_dict,
  model_parameters,
  ...props
}) => {
  return (
    <div className="card card-body card-outer" key={msect}>
      <SectionHeader title={msect} size="2.9rem" label="major" />
      <hr className="mb-3" style={{ borderTop: "0" }} />
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
                {...props}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};
