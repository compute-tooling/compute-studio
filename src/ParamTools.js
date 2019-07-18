

import * as Yup from "yup";


// need to require schema in model_parameters!
export const tbLabelSchema = Yup.object().shape({
  year: Yup.number(),
  MARS: Yup.string(),
  idedtype: Yup.string(),
  EIC: Yup.string(),
  data_source: Yup.string(),
});


export function yupType(type) {
  if (type == "int") {
    return Yup.number()
      .integer()
      .nullable()
      .transform(value => (!value ? null : value));
  } else if (type == "float") {
    return Yup.number()
      .nullable()
      .transform(value => (!value ? null : value));
  } else if (type == "bool") {
    return Yup.bool().nullable()
      .transform(value => (!value ? null : value));
  } else if (type == "date") {
    return Yup.date();
  } else {
    return Yup.string();
  }
}

const minMsg = "Must be greater than or equal to ${min}";
const maxMsg = "Must be less than or equal to ${max}";
const oneOfMsg = "Must be one of the following values: ${values}";

export function yupValidator(params, param_data) {
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
