import * as yup from "yup";
import { parseFromOps, parseToOps } from "./ops";
import * as _ from "lodash";
var integerMsg = "Must be an integer.";
var floatMsg = "Must be a floating point number.";
var dateMsg = "Must be a date.";
var boolMsg = "Must be a boolean value.";
var minMsg = "Must be greater than or equal to ${min}";
var maxMsg = "Must be less than or equal to ${max}";
var oneOfMsg = "Must be one of the following values: ${values}";
var reverseOpMsg = "'<' can only be used as the first index and must be followed by one or more values.";
function transform(value, originalValue) {
    if (typeof originalValue === "string") {
        var trimmed = originalValue.trim();
        if (trimmed === "") {
            return null;
        }
        else if (trimmed === "*" || trimmed === "<") {
            return trimmed;
        }
    }
    return value;
}
function transformArray(value, originalValue) {
    if (Array.isArray(originalValue))
        return originalValue;
    if (!(typeof originalValue === "string")) {
        return [originalValue];
    }
    return originalValue.split(",");
}
function testReverseOp(value) {
    if (!value || (Array.isArray(value) && value.lenghth === 0))
        return true;
    var wildCardIndex = value.indexOf("<");
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
yup.number.prototype._typeCheck = function (value) {
    if (value instanceof Number)
        value = value.valueOf();
    return ((typeof value === "string" && (value === "*" || value === "<")) ||
        (typeof value === "number" && !isNaN(value)));
};
yup.bool.prototype._typeCheck = function (value) {
    if (value instanceof Boolean)
        value = value.valueOf();
    return ((typeof value === "string" && (value === "*" || value === "<")) ||
        typeof value === "boolean");
};
var minObj = function (min) {
    return {
        message: minMsg,
        name: "contrib.min",
        exclusive: true,
        params: { min: min },
        test: function (value) {
            return value == null || value === "*" || value === "<" || value >= min;
        }
    };
};
var maxObj = function (max) {
    return {
        message: maxMsg,
        name: "contrib.max",
        exclusive: true,
        params: { max: max },
        test: function (value) {
            return value == null || value === "*" || value === "<" || value <= max;
        }
    };
};
var reverseObj = {
    message: reverseOpMsg,
    name: "reverseOpValidator",
    exclusive: true,
    params: {},
    test: testReverseOp
};
var integerObj = {
    message: integerMsg,
    name: "contrib.integer",
    exclusive: true,
    params: {},
    test: function (value) {
        return value == null || value === "*" || value === "<" || Number.isInteger(value);
    }
};
export function yupType(type) {
    if (type == "int") {
        return yup
            .number()
            .typeError(integerMsg)
            .nullable()
            .transform(transform)
            .test(integerObj);
    }
    else if (type == "float") {
        return yup
            .number()
            .typeError(floatMsg)
            .nullable()
            .transform(transform);
    }
    else if (type == "bool") {
        return yup
            .bool()
            .typeError(boolMsg)
            .nullable()
            .transform(transform);
    }
    else if (type == "date") {
        return yup
            .date(dateMsg)
            .typeError(dateMsg)
            .nullable()
            .transform(transform);
    }
    else {
        return yup.string();
    }
}
export function yupValidator(params, param_data, extend) {
    if (extend === void 0) { extend = false; }
    var ensureExtend = function (obj) {
        if (extend) {
            return yup
                .array()
                .of(obj)
                .transform(transformArray)
                .compact(function (v) { return v == null || v === ""; })
                .test(reverseObj);
        }
        else {
            return obj;
        }
    };
    var yupObj = yupType(param_data.type);
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
        yupObj = yupObj.oneOf(_.union(param_data.validators.choice.choices, [null, ""]), oneOfMsg);
    }
    return ensureExtend(yupObj);
}
function select(valueObjects, labels) {
    var ret = [];
    if (_.isEmpty(labels)) {
        return valueObjects;
    }
    for (var _i = 0, valueObjects_1 = valueObjects; _i < valueObjects_1.length; _i++) {
        var vo = valueObjects_1[_i];
        var matches = [];
        for (var _a = 0, _b = Object.entries(labels); _a < _b.length; _a++) {
            var _c = _b[_a], labelName = _c[0], labelValue = _c[1];
            if (labelName in vo) {
                matches.push(vo[labelName] === labelValue);
            }
        }
        if (matches.every(function (val) { return val; })) {
            ret.push(vo);
        }
    }
    return ret;
}
function labelsToString(valueObject) {
    var s = [];
    for (var _i = 0, _a = Object.entries(valueObject).sort(); _i < _a.length; _i++) {
        var _b = _a[_i], label = _b[0], label_val = _b[1];
        if (label === "value") {
            continue;
        }
        s.push(label + "__" + label_val);
    }
    if (s.length == 0) {
        s.push("nolabels");
    }
    return "" + s.join("___");
}
export function convertToFormik(data) {
    var initialValues = { adjustment: {}, meta_parameters: {} };
    var sects = {};
    var section_1 = "";
    var section_2 = "";
    var adjShape = {};
    // TODO: move these into formal spec!
    var extend = "extend" in data ? data.extend : false;
    var label_to_extend = "label_to_extend" in data ? data.label_to_extend : "year";
    // end TODO
    var hasInitialValues = "detail" in data;
    var _a = [{}, {}], meta_parameters = _a[0], adjustment = _a[1];
    var unknownParams = [];
    if (hasInitialValues) {
        adjustment = data.detail.adjustment;
        meta_parameters = data.detail.meta_parameters;
    }
    for (var _i = 0, _b = Object.entries(data.model_parameters); _i < _b.length; _i++) {
        var _c = _b[_i], msect = _c[0], params = _c[1];
        var msectShape = {};
        sects[msect] = {};
        initialValues.adjustment[msect] = {};
        if (!(msect in adjustment)) {
            adjustment[msect] = {};
        }
        if (hasInitialValues && msect in adjustment) {
            // Checkbox params are added to unkownParams and are removed in the
            // checkbox logic block later.
            unknownParams = _.union(unknownParams, _.difference(Object.keys(adjustment[msect]), Object.keys(params)));
        }
        var _loop_1 = function (param, param_data) {
            param_data["form_fields"] = {};
            // Group by major section, section_1 and section_2.
            if ("section_1" in param_data) {
                section_1 = param_data.section_1;
            }
            else {
                section_1 = "";
            }
            if ("section_2" in param_data) {
                section_2 = param_data.section_2;
            }
            else {
                section_2 = "";
            }
            if (!(section_1 in sects[msect])) {
                sects[msect][section_1] = {};
            }
            if (!(section_2 in sects[msect][section_1])) {
                sects[msect][section_1][section_2] = [];
            }
            sects[msect][section_1][section_2].push(param);
            yupObj = yupValidator(params, param_data, extend);
            // Define form_fields from value objects.
            initialValues.adjustment[msect][param] = {};
            paramYupShape = {};
            for (var _i = 0, _a = param_data.value; _i < _a.length; _i++) {
                var vals = _a[_i];
                var fieldName = labelsToString(vals);
                var placeholder = vals.value.toString();
                var initialValue = "";
                if (hasInitialValues && param in adjustment[msect]) {
                    var labels = {};
                    for (var _b = 0, _c = Object.entries(vals); _b < _c.length; _b++) {
                        var _d = _c[_b], label = _d[0], labelValue = _d[1];
                        if (label != "value" && label != label_to_extend) {
                            labels[label] = labelValue;
                        }
                    }
                    var matches = select(adjustment[msect][param], labels);
                    initialValue = parseToOps(matches, meta_parameters, label_to_extend);
                }
                initialValues.adjustment[msect][param][fieldName] = initialValue;
                param_data.form_fields[fieldName] = placeholder;
                paramYupShape[fieldName] = yupObj;
            }
            if ("checkbox" in param_data) {
                var initialValue = null;
                if (hasInitialValues && param + "_checkbox" in adjustment[msect]) {
                    // checkbox params are added to unknownParams and it is cheaper
                    // to remove them as they come up here.
                    unknownParams = unknownParams.filter(function (unknownParam) { return unknownParam !== param + "_checkbox"; });
                    initialValue = adjustment[msect][param + "_checkbox"][0].value;
                }
                paramYupShape["checkbox"] = yup.bool().nullable();
                initialValues.adjustment[msect][param]["checkbox"] = initialValue;
            }
            msectShape[param] = yup.object().shape(paramYupShape);
        };
        var yupObj, paramYupShape;
        for (var _d = 0, _e = Object.entries(params); _d < _e.length; _d++) {
            var _f = _e[_d], param = _f[0], param_data = _f[1];
            _loop_1(param, param_data);
        }
        adjShape[msect] = yup.object().shape(msectShape);
    }
    var mpShape = {};
    for (var _g = 0, _h = Object.entries(data.meta_parameters); _g < _h.length; _g++) {
        var _j = _h[_g], mp_name = _j[0], mp_data = _j[1];
        var yupObj_1 = yupValidator(data.meta_parameters, mp_data);
        var mpVal = mp_data.value[0].value;
        mpShape[mp_name] = yupObj_1;
        initialValues["meta_parameters"][mp_name] = yupObj_1.cast(mp_name in meta_parameters ? meta_parameters[mp_name] : mpVal);
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
        schema,
        unknownParams
    ];
}
export function formikToJSON(values, schema, labelSchema, extend) {
    if (extend === void 0) { extend = false; }
    var data = schema.cast(values);
    var meta_parameters = {};
    var adjustment = {};
    for (var _i = 0, _a = Object.entries(data.meta_parameters); _i < _a.length; _i++) {
        var _b = _a[_i], mp_name = _b[0], mp_val = _b[1];
        meta_parameters[mp_name] = mp_val;
    }
    for (var _c = 0, _d = Object.entries(data.adjustment); _c < _d.length; _c++) {
        var _e = _d[_c], msect = _e[0], params = _e[1];
        adjustment[msect] = {};
        for (var _f = 0, _g = Object.entries(params); _f < _g.length; _f++) {
            var _h = _g[_f], paramName = _h[0], paramData = _h[1];
            var voList = [];
            for (var _j = 0, _k = Object.entries(paramData); _j < _k.length; _j++) {
                var _l = _k[_j], voStr = _l[0], val = _l[1];
                var vo = {};
                if (val == null ||
                    (typeof val === "string" && !val) ||
                    (Array.isArray(val) && !val.length)) {
                    continue;
                }
                if (voStr === "checkbox") {
                    adjustment[msect][paramName + "_checkbox"] = [{ value: val }];
                    continue;
                }
                if (voStr == "nolabels") {
                    if (extend && Array.isArray(val) && val.length) {
                        val = val[0];
                    }
                    vo["value"] = val;
                    voList.push(vo);
                }
                else {
                    var labelsSplit = voStr.split("___");
                    for (var _m = 0, labelsSplit_1 = labelsSplit; _m < labelsSplit_1.length; _m++) {
                        var label = labelsSplit_1[_m];
                        var labelSplit = label.split("__");
                        if (labelSplit[0] in meta_parameters) {
                            vo[labelSplit[0]] = meta_parameters[labelSplit[0]];
                        }
                        else {
                            vo[labelSplit[0]] = labelSplit[1];
                        }
                    }
                    vo = labelSchema.cast(vo);
                    vo["value"] = val;
                    if (extend) {
                        voList.push.apply(voList, parseFromOps(vo));
                    }
                    else {
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
//# sourceMappingURL=ParamTools.js.map