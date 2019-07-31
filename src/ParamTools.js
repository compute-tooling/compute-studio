import * as yup from "yup";
import { parseFromOps, parseToOps } from "./ops";
import { isEmpty } from "lodash/lang";

const integerMsg = "Must be an integer.";
const floatMsg = "Must be a floating point number.";
const dateMsg = "Must be a date.";
const boolMsg = "Must be a boolean value.";
const minMsg = "Must be greater than or equal to ${min}";
const maxMsg = "Must be less than or equal to ${max}";
const oneOfMsg = "Must be one of the following values: ${values}";
const reverseOpMsg =
  "'<' can only be used as the first index and must be followed by one or more values.";

function transform(value, originalValue) {
  if (typeof originalValue === "string") {
    let trimmed = originalValue.trim();
    if (trimmed === "") {
      return null;
    } else if (trimmed === "*" || trimmed === "<") {
      return trimmed;
    }
  }
  return value;
}

function transformArray(value, originalValue) {
  if (Array.isArray(originalValue)) return originalValue;

  if (!(typeof originalValue === "string")) {
    return [originalValue];
  }
  return originalValue.split(",");
}

function testReverseOp(value) {
  if (!value || (Array.isArray(value) && value.lenghth === 0)) return true;

  const wildCardIndex = value.indexOf("<");
  // reverseOp can only be used as first index.
  if (wildCardIndex > 0) {
    return false;
  }
  // if used, must be followed by one or more values.
  if (wildCardIndex === 0 && value.length === 1) {
    return false;
  }
  // cannot be used more than once.
  if (wildCardIndex >= 0 && value.indexOf("<", wildCardIndex + 1) !== -1) {
    return false;
  }
  return true;
}

yup.number.prototype._typeCheck = function(value) {
  if (value instanceof Number) value = value.valueOf();

  return (
    (typeof value === "string" && (value === "*" || value === "<")) ||
    (typeof value === "number" && !isNaN(value))
  );
};

yup.bool.prototype._typeCheck = function(value) {
  if (value instanceof Boolean) value = value.valueOf();
  return (
    (typeof value === "string" && (value === "*" || value === "<")) ||
    typeof value === "boolean"
  );
};

const minObj = min => {
  return {
    message: minMsg,
    name: "contrib.min",
    exclusive: true,
    params: { min },
    test: value =>
      value == null || value === "*" || value === "<" || value >= min
  };
};

const maxObj = max => {
  return {
    message: maxMsg,
    name: "contrib.max",
    exclusive: true,
    params: { max },
    test: value =>
      value == null || value === "*" || value === "<" || value <= max
  };
};

const reverseObj = {
  message: reverseOpMsg,
  name: "reverseOpValidator",
  exclusive: true,
  params: {},
  test: testReverseOp
};

const integerObj = {
  message: integerMsg,
  name: "contrib.integer",
  exclusive: true,
  params: {},
  test: value =>
    value == null || value === "*" || value === "<" || Number.isInteger(value)
};

export function yupType(type) {
  if (type == "int") {
    return yup
      .number()
      .typeError(integerMsg)
      .nullable()
      .transform(transform)
      .test(integerObj);
  } else if (type == "float") {
    return yup
      .number()
      .typeError(floatMsg)
      .nullable()
      .transform(transform);
  } else if (type == "bool") {
    return yup
      .bool()
      .typeError(boolMsg)
      .nullable()
      .transform(transform);
  } else if (type == "date") {
    return yup
      .date(dateMsg)
      .typeError(dateMsg)
      .nullable()
      .transform(tranform);
  } else {
    return yup.string();
  }
}

export function yupValidator(params, param_data, extend = false) {
  const ensureExtend = obj => {
    if (extend) {
      return yup
        .array()
        .of(obj)
        .transform(transformArray)
        .compact(v => v == null || v === "")
        .test(reverseObj);
    } else {
      return obj;
    }
  };

  let yupObj = yupType(param_data.type);
  if (!("validators" in param_data) || param_data.type == "bool") {
    return ensureExtend(yupObj);
  }
  if ("range" in param_data.validators) {
    var min_val = null;
    var max_val = null;
    if ("min" in param_data.validators.range) {
      min_val = param_data.validators.range.min;
      if (!(min_val in params)) {
        yupObj = yupObj.test(minObj(min_val));
      }
    }
    if ("max" in param_data.validators.range) {
      max_val = param_data.validators.range.max;
      if (!(max_val in params)) {
        yupObj = yupObj.test(maxObj(max_val));
      }
    }
  }
  if ("choice" in param_data.validators) {
    yupObj = yupObj.oneOf(param_data.validators.choice.choices, oneOfMsg);
  }

  return ensureExtend(yupObj);
}

function select(valueObjects, labels) {
  ret = [];
  for (vo of valueObjects) {
    matches = [];
    for (const [labelName, labelValue] of Object.entries(labels)) {
      if (labelName in vo) {
        match = vo[labelName] === labelValue;
      }
    }
    if (matches.some(val => val)) {
      ret.push(vo);
    }
  }
  return ret;
}

function labelsToString(valueObject) {
  let s = [];
  for (const [label, label_val] of Object.entries(valueObject).sort()) {
    if (label === "value") {
      continue;
    }
    s.push(`${label}__${label_val}`);
  }
  if (s.length == 0) {
    s.push("nolabels");
  }
  return `${s.join("___")}`;
}

export function convertToFormik(data) {
  var initialValues = { adjustment: {}, meta_parameters: {} };
  var sects = {};
  var section_1 = "";
  var section_2 = "";
  var adjShape = {};
  console.log("data", data);
  const extend = "label_to_extend" in data ? data.label_to_extend : false;
  const hasInitialValues = "userInputs" in data;
  let [meta_parameters, adjustment] = [{}, {}];
  if (hasInitialValues) {
    adjustment = data.userInputs.adjustment;
    meta_parameters = data.userInputs.meta_parameters;
  }
  for (const [msect, params] of Object.entries(data.model_parameters)) {
    var msectShape = {};
    sects[msect] = {};
    initialValues.adjustment[msect] = {};
    let editValues = {};
    if (hasInitialValues && msect in adjustment) {
      for (const [param, param_data] of Object.entries(adjustment[msect])) {
        if (extend) {
          var value = parseToOps(param_data, data.meta_parameters);
        } else {
          var value = param_data.value;
        }
        editValues[param] = param_data.map(vo => {
          let fieldName = labelsToString(vo);
          return { [fieldName]: value };
        });
        console.log(param, editValues[param]);
      }
    }
    console.log("editValues", editValues);
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

      var yupObj = yupValidator(params, param_data, extend);

      // Define form_fields from value objects.
      initialValues.adjustment[msect][param] = {};
      var paramYupShape = {};

      for (const vals of param_data.value) {
        let fieldName = labelsToString(vals);
        if (param in editValues) {
          console.log(fieldName);
          console.log(editValues[param]);
        }
        if (
          !isEmpty(editValues) &&
          param in editValues &&
          fieldName in editValues[param]
        ) {
          console.log(
            "edit val",
            param,
            fieldName,
            editValues[param][fieldName]
          );
          var value = editValues[param][fieldName];
        } else {
          var value = vals.value;
        }
        // TODO: match with edit value when supplied.
        initialValues.adjustment[msect][param][fieldName] = "";
        param_data.form_fields[fieldName] = value;
        paramYupShape[fieldName] = yupObj;
      }

      if ("checkbox" in param_data) {
        paramYupShape["checkbox"] = yup.bool().nullable();
        initialValues.adjustment[msect][param]["checkbox"] = null;
      }

      msectShape[param] = yup.object().shape(paramYupShape);
    }

    adjShape[msect] = yup.object().shape(msectShape);
  }
  let mpShape = {};
  for (const [mp_name, mp_data] of Object.entries(data.meta_parameters)) {
    let yupObj = yupValidator(data.meta_parameters, mp_data);
    let mpVal = mp_data.value[0].value;
    mpShape[mp_name] = yupObj;
    initialValues["meta_parameters"][mp_name] = yupObj.cast(
      mp_name in meta_parameters ? meta_parameters[mp_name] : mpVal
    );
  }
  console.log("with metaparameters", initialValues);
  var schema = yup.object().shape({
    adjustment: yup.object().shape(adjShape),
    meta_parameters: yup.object().shape(mpShape)
  });
  console.log("returning...");
  return [
    initialValues,
    sects,
    data.model_parameters,
    data.meta_parameters,
    schema
  ];
}

export function formikToJSON(values, schema, labelSchema, extend = false) {
  let data = schema.cast(values);
  var meta_parameters = {};
  var adjustment = {};

  for (const [mp_name, mp_val] of Object.entries(data.meta_parameters)) {
    meta_parameters[mp_name] = mp_val;
  }

  for (const [msect, params] of Object.entries(data.adjustment)) {
    adjustment[msect] = {};
    for (const [paramName, paramData] of Object.entries(params)) {
      var voList = [];
      for (const [voStr, val] of Object.entries(paramData)) {
        var vo = {};
        if (
          val == null ||
          (typeof val === "string" && !val) ||
          (Array.isArray(val) && !val.length)
        ) {
          continue;
        }
        if (voStr === "checkbox") {
          adjustment[msect][`${paramName}_checkbox`] = [{ value: val }];
          continue;
        }
        if (voStr == "nolabels") {
          vo["value"] = val;
          voList.push(vo);
        } else {
          var labelsSplit = voStr.split("___");
          for (const label of labelsSplit) {
            var labelSplit = label.split("__");
            if (label in meta_parameters) {
              vo[labelSplit[0]] = meta_parameters[labelSplit[0]];
            } else {
              vo[labelSplit[0]] = labelSplit[1];
            }
          }
          vo = labelSchema.cast(vo);
          vo["value"] = val;
          console.log(extend);
          if (extend) {
            voList.push(...parseFromOps(vo));
          } else {
            voList.push(vo);
          }
        }
      }
      if (voList.length > 0) {
        adjustment[msect][paramName] = voList;
      }
    }
  }

  return [meta_parameters, adjustment];
}
