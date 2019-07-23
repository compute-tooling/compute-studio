import * as yup from "yup";

const integerMsg = "Must be an integer.";
const floatMsg = "Must be a floating point number.";
const dateMsg = "Must be a date.";
const boolMsg = "Must be a boolean value.";
const minMsg = "Must be greater than or equal to ${min}";
const maxMsg = "Must be less than or equal to ${max}";
const oneOfMsg = "Must be one of the following values: ${values}";

export function yupType(type) {
  if (type == "int") {
    return yup
      .number()
      .integer(integerMsg)
      .typeError(integerMsg)
      .nullable()
      .transform(value => (value === "" ? null : value));
  } else if (type == "float") {
    return yup
      .number()
      .typeError(floatMsg)
      .nullable()
      .transform(value => (value === "" ? null : value));
  } else if (type == "bool") {
    return yup
      .bool()
      .typeError(boolMsg)
      .nullable()
      .transform(value => (value === "" ? null : value));
  } else if (type == "date") {
    return yup
      .date(dateMsg)
      .typeError(dateMsg)
      .nullable()
      .transform(value => (value === "" ? null : value));
  } else {
    return yup.string();
  }
}

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

export function convertToFormik(data) {
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

        // TODO: match with edit value when supplied.
        initialValues.adjustment[msect][param][field_name] = "";
        param_data.form_fields[field_name] = vals.value;
        paramYupShape[field_name] = yupObj;
      }
      msectShape[param] = yup.object().shape(paramYupShape);
    }
    adjShape[msect] = yup.object().shape(msectShape);
  }
  var mpShape = {};
  for (const [mp_name, mp_data] of Object.entries(data.meta_parameters)) {
    var yupObj = yupValidator(data.meta_parameters, mp_data);
    mpShape[mp_name] = yupObj;
    initialValues["meta_parameters"][mp_name] = mp_data.value[0].value;
  }

  var schema = yup.object().shape({
    adjustment: yup.object().shape(adjShape),
    meta_parameters: yup.object().shape(mpShape)
  });

  return [
    initialValues,
    sects,
    data.model_parameters,
    data.meta_parameters,
    schema
  ];
}

export function formikToJSON(values, schema, labelSchema) {
  let data = schema.cast(values);
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
          vo = labelSchema.cast(vo);
          vo["value"] = val;
        }
        voList.push(vo);
      }
      if (voList.length > 0) {
        adjustment[msect][paramName] = voList;
      }
    }
  }
  for (const [mp_name, mp_val] of Object.entries(data.meta_parameters)) {
    meta_parameters[mp_name] = mp_val;
  }

  return [meta_parameters, adjustment];
}
