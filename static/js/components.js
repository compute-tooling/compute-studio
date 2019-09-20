"use strict";
var __rest = (this && this.__rest) || function (s, e) {
    var t = {};
    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
        t[p] = s[p];
    if (s != null && typeof Object.getOwnPropertySymbols === "function")
        for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
            if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
                t[p[i]] = s[p[i]];
        }
    return t;
};
import * as React from "react";
import * as ReactLoading from "react-loading";
import { FastField, ErrorMessage } from "formik";
import { isEqual, isEmpty } from "lodash/lang";
import { makeID, valForForm } from "./utils";
import { RedMessage, getField, CPIField } from "./fields";
import { Card, Button, OverlayTrigger, Tooltip } from "react-bootstrap";
export var ParamElement = function (_a) {
    var param_data = _a.param_data, checkbox = _a.checkbox, id = _a.id, _b = _a.classes, classes = _b === void 0 ? "row has-statuses col-xs-12" : _b;
    var tooltip = React.createElement("div", null);
    if (param_data.description) {
        tooltip = (React.createElement(OverlayTrigger, { trigger: ["hover", "click"], overlay: React.createElement(Tooltip, { id: id + "-tooltip" }, param_data.description) },
            React.createElement("span", { className: "d-inline-block" },
                React.createElement("label", null,
                    React.createElement("i", { className: "fas fa-info-circle" })))));
    }
    return (React.createElement("div", { className: classes },
        React.createElement("label", { id: id },
            param_data.title,
            " ",
            tooltip,
            " ",
            !!checkbox ? checkbox : null)));
};
export var SectionHeader = function (_a) {
    var title = _a.title, titleSize = _a.titleSize, titleClass = _a.titleClass, label = _a.label, _b = _a.openDefault, openDefault = _b === void 0 ? true : _b;
    var _c = React.useState(openDefault), open = _c[0], setOpen = _c[1];
    return (React.createElement("h1", { style: { fontSize: titleSize }, className: titleClass ? titleClass : "" },
        title,
        React.createElement("div", { className: "float-right" },
            React.createElement("button", { className: "btn collapse-button", type: "button", "data-toggle": "collapse", "data-target": "#" + makeID(title) + "-collapse-" + label, "aria-expanded": "false", "aria-controls": makeID(title) + "-collapse-" + label, style: { marginLeft: "20px" }, onClick: function (e) { return setOpen(!open); } },
                React.createElement("i", { className: "far fa-" + (open ? "minus" : "plus") + "-square", style: { size: "5px" } })))));
};
export var LoadingElement = function () {
    return (React.createElement("div", { className: "row" },
        React.createElement("div", { className: "col-sm-4" },
            React.createElement("ul", { className: "list-unstyled components sticky-top scroll-y" },
                React.createElement("li", null,
                    React.createElement("div", { className: "card card-body card-outer" },
                        React.createElement("div", { className: "d-flex justify-content-center" },
                            React.createElement(ReactLoading, { type: "spokes", color: "#2b2c2d" })))))),
        React.createElement("div", { className: "col-sm-8" },
            React.createElement("div", { className: "card card-body card-outer" },
                React.createElement("div", { className: "d-flex justify-content-center" },
                    React.createElement(ReactLoading, { type: "spokes", color: "#2b2c2d" }))))));
};
export var MetaParameters = React.memo(function (_a) {
    var meta_parameters = _a.meta_parameters, values = _a.values, touched = _a.touched, resetInitialValues = _a.resetInitialValues;
    var isTouched = "meta_parameters" in touched;
    return (React.createElement("div", { className: "card card-body card-outer" },
        React.createElement("div", { className: "form-group" },
            React.createElement("ul", { className: "list-unstyled components" },
                Object.entries(meta_parameters).map(function (mp_item, ix) {
                    var paramName = "" + mp_item[0];
                    var fieldName = "meta_parameters." + paramName;
                    return (React.createElement("li", { key: fieldName, className: "mb-3 mt-1" },
                        React.createElement(ParamElement, { param_data: meta_parameters[paramName], id: fieldName, classes: "" }),
                        getField(fieldName, mp_item[1], valForForm(mp_item[1].value[0].value)),
                        React.createElement(ErrorMessage, { name: fieldName, render: function (msg) { return React.createElement(RedMessage, { msg: msg }); } })));
                }),
                React.createElement("li", null, isTouched ? (React.createElement("p", { className: "form-text text-muted" }, "Click Reset to update the default values of the parameters.")) : (React.createElement("div", null))))),
        React.createElement("button", { name: "reset", className: "btn btn-block btn-outline-dark mt-3", onClick: function (e) {
                e.preventDefault();
                resetInitialValues(values);
            } }, "Reset")));
}, function (prevProps, nextProps) {
    return isEqual(prevProps.values, nextProps.values);
});
var ValueComponent = function (_a) {
    var fieldName = _a.fieldName, placeholder = _a.placeholder, colClass = _a.colClass, data = _a.data, isTouched = _a.isTouched, extend = _a.extend, label = _a.label;
    var style = isTouched ? { backgroundColor: "rgba(102, 175, 233, 0.2)" } : {};
    return (React.createElement("div", { className: colClass, key: makeID(fieldName) },
        label ? React.createElement("small", { style: { padding: 0 } }, label) : null,
        getField(fieldName, data, placeholder, style, extend),
        isTouched ? (React.createElement("small", { className: "ml-2", style: { color: "#869191" } },
            "Default: ",
            placeholder)) : null,
        React.createElement(ErrorMessage, { name: fieldName, render: function (msg) { return React.createElement(RedMessage, { msg: msg }); } })));
};
var Value = React.memo(ValueComponent);
export var Param = React.memo(function (_a) {
    var param = _a.param, msect = _a.msect, data = _a.data, values = _a.values, extend = _a.extend, meta_parameters = _a.meta_parameters;
    if (Object.keys(data.form_fields).length == 1) {
        var colClass = "col-6";
    }
    else if (data.type === "bool" ||
        (!!data.validators && data.validators.choice)) {
        var colClass = "col-md-auto";
    }
    else {
        var colClass = "col";
    }
    if ("checkbox" in data) {
        var checkbox = (React.createElement(FastField, { name: "adjustment." + msect + "." + param + ".checkbox", placeholder: data.checkbox, component: CPIField }));
    }
    else {
        var checkbox = null;
    }
    var paramElement = (React.createElement(ParamElement, { param_data: data, checkbox: checkbox, id: "adjustment." + msect + "." + param }));
    return (React.createElement("div", { className: "container mb-3", style: { padding: "left 0" }, key: param },
        paramElement,
        React.createElement("div", { className: "form-row has-statuses", style: { marginLeft: "-20px" } }, Object.entries(data.form_fields).map(function (form_field, ix) {
            var labels = form_field[0];
            var vo = data.value[ix];
            var commaSepLabs = Object.entries(vo)
                .filter(function (item) { return item[0] != "value" && !(item[0] in meta_parameters); })
                .map(function (item) { return item[1]; }).join(",");
            var fieldName = "adjustment." + msect + "." + param + "." + labels;
            var placeholder = valForForm(form_field[1]);
            var isTouched = false;
            if (labels in values) {
                isTouched = Array.isArray(values[labels])
                    ? values[labels].length > 0
                    : !!values[labels];
            }
            return (React.createElement(Value, { key: fieldName, fieldName: fieldName, placeholder: placeholder, colClass: colClass, data: data, isTouched: isTouched, extend: extend, label: commaSepLabs }));
        }))));
}, function (prevProps, nextProps) {
    return isEqual(prevProps.values, nextProps.values);
});
var Section2 = React.memo(function (_a) {
    var section_2 = _a.section_2, param_list = _a.param_list, msect = _a.msect, model_parameters = _a.model_parameters, values = _a.values, extend = _a.extend, meta_parameters = _a.meta_parameters;
    var section_2_id = makeID(section_2);
    return (React.createElement("div", { key: section_2_id, className: "mb-2" },
        React.createElement("h3", { className: "mb-1" }, section_2),
        param_list.map(function (param) {
            return (React.createElement(Param, { key: param + "-component", param: param, msect: msect, data: model_parameters[msect][param], values: values[param], extend: extend, meta_parameters: meta_parameters }));
        })));
}, function (prevProps, nextProps) {
    for (var _i = 0, _a = prevProps.param_list; _i < _a.length; _i++) {
        var param = _a[_i];
        if (!isEqual(prevProps.values[param], nextProps.values[param])) {
            return false;
        }
    }
    return true;
});
var Section1 = React.memo(function (_a) {
    var section_1 = _a.section_1, section_2_dict = _a.section_2_dict, msect = _a.msect, model_parameters = _a.model_parameters, values = _a.values, extend = _a.extend, meta_parameters = _a.meta_parameters;
    var section_1_id = makeID(section_1);
    return (React.createElement("div", { className: "inputs-block", id: section_1_id, key: section_1_id },
        React.createElement("div", { className: "card card-body card-outer mb-3 shadow-sm", style: { padding: "1rem" } },
            React.createElement(SectionHeader, { title: section_1, titleSize: "2.5rem", label: "section-1" }),
            React.createElement("div", { className: "collapse show collapse-plus-minus", id: makeID(section_1) + "-collapse-section-1" },
                React.createElement("div", { className: "card card-body card-inner mb-3", style: { padding: "0rem" } }, Object.entries(section_2_dict).map(function (param_list_item, ix) {
                    var section_2 = param_list_item[0];
                    var param_list = param_list_item[1];
                    return (React.createElement(Section2, { key: makeID(section_2) + "-component", section_2: section_2, param_list: param_list, msect: msect, model_parameters: model_parameters, values: values, extend: extend, meta_parameters: meta_parameters }));
                }))))));
}, function (prevProps, nextProps) {
    for (var _i = 0, _a = Object.entries(prevProps.section_2_dict); _i < _a.length; _i++) {
        var _b = _a[_i], section2 = _b[0], paramList = _b[1];
        for (var _c = 0, paramList_1 = paramList; _c < paramList_1.length; _c++) {
            var param = paramList_1[_c];
            if (!isEqual(prevProps.values[param], nextProps.values[param])) {
                return false;
            }
        }
    }
    return true;
});
export var MajorSection = React.memo(function (_a) {
    var msect = _a.msect, section_1_dict = _a.section_1_dict, meta_parameters = _a.meta_parameters, model_parameters = _a.model_parameters, props = __rest(_a, ["msect", "section_1_dict", "meta_parameters", "model_parameters"]);
    return (React.createElement("div", { className: "card card-body card-outer", key: msect, id: makeID(msect) },
        React.createElement(SectionHeader, { title: msect, titleSize: "2.9rem", label: "major" }),
        React.createElement("hr", { className: "mb-1", style: { borderTop: "0" } }),
        React.createElement("div", { className: "collapse show collapse-plus-minus", id: makeID(msect) + "-collapse-major" },
            React.createElement("div", { className: "card card-body card-inner", style: { padding: "0rem" } }, Object.entries(section_1_dict).map(function (section_2_item, ix) {
                var section_1 = section_2_item[0];
                var section_2_dict = section_2_item[1];
                return (React.createElement(Section1, { key: makeID(section_1) + "-component", section_1: section_1, section_2_dict: section_2_dict, msect: msect, model_parameters: model_parameters, values: props.values.adjustment[msect], extend: props.extend, meta_parameters: meta_parameters }));
            })))));
}, function (prevProps, nextProps) {
    return isEqual(prevProps.values.adjustment[prevProps.msect], nextProps.values.adjustment[prevProps.msect]);
});
export var SectionHeaderList = function (_a) {
    var sects = _a.sects;
    return (React.createElement("div", { className: "card card-body card-outer" }, Object.entries(sects).map(function (_a, ix) {
        var msect = _a[0], section1 = _a[1];
        return (React.createElement("div", { className: "card card-body card-inner mb-1 mr-1", key: msect + "-header-card" },
            React.createElement("div", { className: "list-group" },
                React.createElement("a", { className: "list-group-item list-group-item-action mt-0", href: "#" + makeID(msect), key: "#" + makeID(msect) + "-msect-panel", style: {
                        border: "0px",
                        padding: "0rem",
                        color: "inherit"
                    } },
                    React.createElement("h3", { style: { color: "inherit" } }, msect)),
                Object.entries(section1).map(function (_a, ix) {
                    var section1Title = _a[0], section2Params = _a[1];
                    return (React.createElement("a", { className: "list-group-item list-group-item-action", href: "#" + makeID(section1Title), key: "#" + makeID(section1Title) + "-section1-panel", style: {
                            padding: ".3rem 0rem",
                            border: "0px",
                            color: "inherit"
                        } }, section1Title));
                }))));
    })));
};
export var Preview = React.memo(function (_a) {
    var values = _a.values, schema = _a.schema, tbLabelSchema = _a.tbLabelSchema, transformfunc = _a.transformfunc, extend = _a.extend;
    var _b = React.useState({}), preview = _b[0], setPreview = _b[1];
    var parseValues = function () {
        try {
            return transformfunc(values, schema, tbLabelSchema, extend);
        }
        catch (error) {
            return ["Something went wrong while creating the preview.", ""];
        }
    };
    var onClick = function (e) {
        e.preventDefault();
        var _a = parseValues(), meta_parameters = _a[0], model_parameters = _a[1];
        setPreview({
            meta_parameters: meta_parameters,
            adjustment: model_parameters
        });
    };
    return (React.createElement(Card, { className: "card-outer" },
        React.createElement(Card, { className: "card-body card-inner mt-1 mb-1" },
            React.createElement(SectionHeader, { title: "Preview", titleSize: "2.0rem", titleClass: "font-italic", label: "preview", openDefault: false }),
            React.createElement("div", { className: "collapse collapse-plus-minus", id: "Preview-collapse-preview" },
                React.createElement("pre", null,
                    React.createElement("code", null, JSON.stringify(preview, null, 4))),
                React.createElement(Button, { variant: "outline-success", className: "col-3", onClick: onClick }, "Refresh")))));
}, function (prevProps, nextProps) {
    return isEqual(prevProps.values, nextProps.values);
});
export var ErrorCard = function (_a) {
    var errorMsg = _a.errorMsg, errors = _a.errors, _b = _a.model_parameters, model_parameters = _b === void 0 ? null : _b;
    var getTitle = function (msect, paramName) {
        if (!!model_parameters &&
            msect in model_parameters &&
            paramName in model_parameters[msect]) {
            return [true, model_parameters[msect][paramName].title];
        }
        else {
            return [false, paramName];
        }
    };
    return (React.createElement(Card, { className: "card-outer" },
        React.createElement(Card.Body, null,
            React.createElement("div", { className: "alert alert-danger" }, errorMsg),
            Object.entries(errors).map(function (_a, ix) {
                var msect = _a[0], errors = _a[1];
                return !isEmpty(errors.errors) ? (React.createElement("div", { key: msect + "-error", className: "alert alert-danger" },
                    React.createElement("h5", null, msect),
                    Object.entries(errors.errors).map(function (_a, ix) {
                        var paramName = _a[0], msgs = _a[1];
                        var _b = getTitle(msect, paramName), exists = _b[0], title = _b[1];
                        return (React.createElement("div", { key: msect + "-" + paramName + "-error" },
                            React.createElement("p", null,
                                React.createElement("b", null, title + ":")),
                            React.createElement("ul", { className: "list-unstyled" },
                                React.createElement("li", { className: "ml-2" },
                                    React.createElement("ul", null,
                                        msgs.map(function (msg, ix) { return React.createElement("li", { key: "msg-" + ix }, msg); }),
                                        " ",
                                        exists ? (React.createElement("li", { className: "list-unstyled" },
                                            React.createElement("a", { href: "#adjustment." + msect + "." + paramName }, "[link]"))) : null)))));
                    }))) : (React.createElement("div", { key: msect + "-error" }));
            }))));
};
//# sourceMappingURL=components.js.map