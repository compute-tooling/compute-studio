import * as yup from "yup";
import { parseFromOps, parseToOps } from "./ops";
import { isEmpty } from "lodash/lang";
import { union, difference } from "lodash/array";

import {
  ValueObject,
  ParamToolsConfig,
  ParamToolsParam,
  FormValueObject,
  InputsDetail,
  InitialValues,
  Sects,
  Inputs,
  Schema
} from "../types";

const integerMsg: string = "Must be an integer.";
const floatMsg: string = "Must be a floating point number.";
const dateMsg: string = "Must be a date.";
const boolMsg: string = "Must be a boolean value.";
const minMsg: string = "Must be greater than or equal to ${min}";
const maxMsg: string = "Must be less than or equal to ${max}";
const oneOfMsg: string = "Must be one of the following values: ${values}";
const reverseOpMsg: string =
  "'<' can only be used as the first index and must be followed by one or more values.";

function transform(value: any, originalValue: any) {
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

function transformArray(value: any, originalValue: any): Array<any> {
  if (Array.isArray(originalValue)) return originalValue;

  if (!(typeof originalValue === "string")) {
    return [originalValue];
  }
  return originalValue.split(",");
}

function testReverseOp(value: any): boolean {
  if (!value || (Array.isArray(value) && value.length === 0)) return true;

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

yup.number.prototype._typeCheck = function(value: any): boolean {
  if (value instanceof Number) value = value.valueOf();

  return (
    (typeof value === "string" && (value === "*" || value === "<")) ||
    (typeof value === "number" && !isNaN(value))
  );
};

yup.bool.prototype._typeCheck = function(value) {
  if (value instanceof Boolean) value = value.valueOf();
  return (
    (typeof value === "string" && (value === "*" || value === "<")) || typeof value === "boolean"
  );
};

const minObj = min => {
  return {
    message: minMsg,
    name: "contrib.min",
    exclusive: true,
    params: { min },
    test: value => value == null || value === "*" || value === "<" || value >= min
  };
};

const maxObj = max => {
  return {
    message: maxMsg,
    name: "contrib.max",
    exclusive: true,
    params: { max },
    test: (value: any): boolean => value == null || value === "*" || value === "<" || value <= max
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
  test: value => value == null || value === "*" || value === "<" || Number.isInteger(value)
};

export function yupType(
  type: "int" | "float" | "bool" | "date" | "string"
): yup.Schema<number> | yup.Schema<boolean> | yup.Schema<Date> | yup.Schema<string> {
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
      .date()
      .typeError(dateMsg)
      .nullable()
      .transform(transform);
  } else {
    return yup.string();
  }
}

export function yupValidator(
  params: ParamToolsConfig,
  param_data: ParamToolsParam,
  extend: boolean = false
):
  | yup.Schema<number | boolean | Date | string>
  | yup.ArraySchema<number | boolean | Date | string>
  | yup.ArraySchema<(number | boolean | Date | string)[]> {
  const ensureExtend = obj => {
    if (extend) {
      return yup
        .array()
        .of(obj)
        .transform(transformArray)
        .compact(v => v == null || v === "")
        .test(reverseObj) as yup.Schema<any> | yup.ArraySchema<any>;
    } else {
      return obj as yup.Schema<any> | yup.ArraySchema<any>;
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
        let minValTest = minObj(min_val);
        // @ts-ignore
        yupObj = yupObj.test(minValTest);
      }
    }
    if ("max" in param_data.validators.range) {
      max_val = param_data.validators.range.max;
      if (!(max_val in params)) {
        let maxValTest = maxObj(max_val);
        //@ts-ignore
        yupObj = yupObj.test(maxValTest);
      }
    }
  }
  if ("choice" in param_data.validators) {
    yupObj = yupObj.oneOf(union(param_data.validators.choice.choices, [null, ""]), oneOfMsg);
  }
  if (param_data.number_dims === 1) {
    return yup
      .array()
      .of<number | boolean | Date | string>(yupObj)
      .nullable()
      .compact(v => v == null || v === "");
  } else if (param_data.number_dims === 2) {
    let subArray = yup
      .array()
      .of<number | boolean | Date | string>(yupObj)
      .transform((val, oval) => {
        if (typeof oval === "object") {
          return Object.keys(oval).map(key => oval[key]);
        } else {
          return oval;
        }
      })
      .min(param_data.value[0].value[0].length)
      .max(param_data.value[0].value[0].length);
    return yup
      .array()
      .of(subArray)
      .nullable()
      .compact(v => v == null || v === [""]);
  } else {
    return ensureExtend(yupObj);
  }
}

function select(valueObjects: Array<ValueObject>, labels: { [key: string]: any }) {
  let ret = [];
  if (isEmpty(labels)) {
    return valueObjects;
  }
  for (const vo of valueObjects) {
    let matches = [];
    for (const [labelName, labelValue] of Object.entries(labels)) {
      if (labelName in vo) {
        matches.push(vo[labelName] === labelValue);
      }
    }
    if (matches.every(val => val)) {
      ret.push(vo);
    }
  }
  return ret;
}

function labelsToString(valueObject: ValueObject): string {
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

export function convertToFormik(
  data: Inputs
): [
  InitialValues,
  Sects,
  Inputs,
  { adjustment: yup.Schema<any>; meta_parameters: yup.Schema<any> },
  Array<string>
] {
  if ("schema" in data.meta_parameters) {
    delete data.meta_parameters["schema"];
  }

  let initialValues: InitialValues = { adjustment: {}, meta_parameters: {} };
  let sects: Sects = {};
  let section_1: string;
  let section_2: string;
  let adjShape: { [msect: string]: yup.Schema<any> } = {};
  // TODO: move these into formal spec!
  const extend: boolean = "extend" in data ? data.extend : false;
  let label_to_extend: string = "label_to_extend" in data ? data.label_to_extend : "year";
  // end TODO
  const hasInitialValues: boolean = "detail" in data;
  let adjustment: InputsDetail["adjustment"] = {};
  let meta_parameters: InputsDetail["meta_parameters"] = {};
  let unknownParams = [];
  if (hasInitialValues) {
    adjustment = data.detail.adjustment;
    meta_parameters = data.detail.meta_parameters;
  }
  for (const [msect, params] of Object.entries(data.model_parameters)) {
    let ptSchema = (params.schema as unknown) as Schema;
    var msectShape = {};
    sects[msect] = {};
    initialValues.adjustment[msect] = {};
    if (!(msect in adjustment)) {
      adjustment[msect] = {};
    }
    if (hasInitialValues && msect in adjustment) {
      // Checkbox params are added to unkownParams and are removed in the
      // checkbox logic block later.
      unknownParams = union(
        unknownParams,
        difference(Object.keys(adjustment[msect]), Object.keys(params))
      );
    }
    for (const [param, param_data] of Object.entries(params)) {
      if (param === "schema") {
        continue;
      }
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

      var yupObj = yupValidator(params, param_data, extend && label_to_extend in ptSchema.labels);

      // Define form_fields from value objects.
      initialValues.adjustment[msect][param] = {};
      var paramYupShape = {};

      for (const vals of param_data.value) {
        let fieldName = labelsToString(vals);
        let placeholder = vals.value;
        let initialValue: string | Array<any> = "";
        if (hasInitialValues && param in adjustment[msect]) {
          let labels = {};
          for (const [label, labelValue] of Object.entries(vals)) {
            if (label != "value" && label != label_to_extend) {
              labels[label] = labelValue;
            }
          }
          let matches = select(adjustment[msect][param], labels);
          // only handle ops if the label_to_extend is used by the parameter section.
          if (extend && label_to_extend in ptSchema.labels) {
            initialValue = parseToOps(matches, meta_parameters, label_to_extend);
          } else {
            initialValue = matches.map((vo, ix) => vo.value);
            initialValue = initialValue && initialValue[0];
          }
        }
        initialValues.adjustment[msect][param][fieldName] = initialValue;
        param_data.form_fields[fieldName] = placeholder;
        paramYupShape[fieldName] = yupObj;
      }

      if ("checkbox" in param_data) {
        let initialValue = null;
        if (hasInitialValues && `${param}_checkbox` in adjustment[msect]) {
          // checkbox params are added to unknownParams and it is cheaper
          // to remove them as they come up here.
          unknownParams = unknownParams.filter(
            unknownParam => unknownParam !== `${param}_checkbox`
          );
          initialValue = adjustment[msect][`${param}_checkbox`][0].value;
        }
        paramYupShape["checkbox"] = yup.bool().nullable();
        initialValues.adjustment[msect][param]["checkbox"] = initialValue;
      }

      msectShape[param] = yup.object().shape(paramYupShape);
    }

    adjShape[msect] = yup.object().shape(msectShape);
  }
  let mpShape: { [mpName: string]: yup.Schema<any> } = {};
  for (const [mp_name, mp_data] of Object.entries(data.meta_parameters)) {
    let yupObj = yupValidator(data.meta_parameters, mp_data);
    let mpVal = mp_data.value[0].value;
    mpShape[mp_name] = yupObj;
    if (meta_parameters && mp_name in meta_parameters) {
      if (
        Array.isArray(meta_parameters[mp_name]) &&
        (meta_parameters[mp_name] as Array<ValueObject>).length >= 1 &&
        "value" in meta_parameters[mp_name][0]
      ) {
        mpVal = meta_parameters[mp_name][0].value;
      } else {
        mpVal = meta_parameters[mp_name] as ValueObject["value"];
      }
    }
    initialValues["meta_parameters"][mp_name] = yupObj.cast(mpVal);
  }
  let schema = {
    adjustment: yup.object().shape(adjShape),
    meta_parameters: yup.object().shape(mpShape)
  };
  return [initialValues, sects, data, schema, unknownParams];
}

export interface FormData {
  adjustment: {
    [msect: string]: {
      [paramName: string]: {
        [voStr: string]: any;
      };
    };
  };
  meta_parameters: { [key: string]: Array<any> };
}

export function formikToJSON(
  values: { [key: string]: any },
  schema: yup.Schema<any>,
  labelSchema: yup.Schema<any>,
  extend: boolean = false,
  label_to_extend: string,
  model_parameters: Inputs["model_parameters"]
) {
  let data: FormData = schema.cast(values);
  var meta_parameters: { [key: string]: any } = {};
  var adjustment: { [key: string]: { [key: string]: Array<ValueObject> } } = {};

  for (const [mp_name, mp_val] of Object.entries(data.meta_parameters)) {
    meta_parameters[mp_name] = mp_val;
  }
  for (const [msect, params] of Object.entries(data.adjustment)) {
    const ptSchema = (model_parameters[msect].schema as unknown) as Schema;
    adjustment[msect] = {};
    for (const [paramName, paramData] of Object.entries(params)) {
      var voList: Array<ValueObject> = [];
      for (const [voStr, val] of Object.entries(paramData)) {
        var vo: FormValueObject = { value: [] };
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
          // if in extend mode, all parameters are casted up a dimension and need to be
          // brought down if they do not use the label 'label_to_extend'.
          if (extend && label_to_extend in ptSchema.labels && Array.isArray(val) && val.length) {
            vo.value = val[0];
          } else {
            vo.value = val;
          }
          voList.push(vo);
        } else {
          var labelsSplit = voStr.split("___");
          for (const label of labelsSplit) {
            var labelSplit = label.split("__");
            if (labelSplit[0] in meta_parameters) {
              vo[labelSplit[0]] = meta_parameters[labelSplit[0]];
            } else {
              vo[labelSplit[0]] = labelSplit[1];
            }
          }
          vo = labelSchema.cast(vo);
          vo.value = val;
          // only handle ops if the label_to_extend is used by the parameter section.
          if (extend && label_to_extend in ptSchema.labels) {
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
