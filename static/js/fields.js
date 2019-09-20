var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
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
import hljs from "highlight.js/lib/highlight";
import python from "highlight.js/lib/languages/python";
import json from "highlight.js/lib/languages/json";
hljs.registerLanguage("python", python);
hljs.registerLanguage("json", json);
import "highlight.js/styles/default.css";
import React from "react";
import { Button } from "react-bootstrap";
import { FastField } from "formik";
var Remarkable = require("remarkable");
hljs.initHighlightingOnLoad();
var inputStyle = {
    width: "50rem"
};
var md = new Remarkable({
    highlight: function (str, lang) {
        if ((lang && hljs.getLanguage(lang)) || true) {
            try {
                return hljs.highlight(lang, str).value;
            }
            catch (err) { }
        }
        try {
            return hljs.highlightAuto(str).value;
        }
        catch (err) { }
        return ""; // use external default escaping
    }
});
function markdownElement(markdownText) {
    // Box is not displayed if markdownText is an empty string.
    if (!markdownText) {
        markdownText = "&#8203;"; // space character
    }
    var marked = {
        __html: md.render(markdownText)
    };
    return (React.createElement("div", { className: "markdown-wrapper mt-2 mb-2" },
        React.createElement("div", { dangerouslySetInnerHTML: marked, className: "card publish markdown", style: inputStyle })));
}
function titleChange(e, onChange) {
    if (e.target.name == "title") {
        e.target.value = e.target.value.replace(/[^a-zA-Z0-9]+/g, "-");
    }
    onChange(e);
}
export var TextField = function (_a) {
    var field = _a.field, _b = _a.form, touched = _b.touched, errors = _b.errors, props = __rest(_a, ["field", "form"]);
    if (props.preview) {
        var element = markdownElement(field.value);
    }
    else {
        var element = (React.createElement("input", __assign({ className: "form-control" }, field, props, { preview: "", style: inputStyle, onChange: function (e) { return titleChange(e, field.onChange); } })));
    }
    return (React.createElement("div", null,
        React.createElement("label", null,
            React.createElement("b", null,
                props.label,
                ":"),
            element)));
};
function checkboxChange(e, onChange, placeholder) {
    if (placeholder === void 0) { placeholder = null; }
    var value = e.target.value != null && e.target.value !== ""
        ? e.target.value
        : placeholder;
    if (typeof value === "boolean") {
        e.target.value = !value;
    }
    else {
        e.target.value = value === "true" ? false : true;
    }
    onChange(e);
}
export var CheckboxField = function (_a) {
    var field = _a.field, _b = _a.form, touched = _b.touched, errors = _b.errors, props = __rest(_a, ["field", "form"]);
    return (React.createElement("div", null,
        React.createElement("label", null,
            React.createElement("b", null, props.label),
            props.description ? props.description : "",
            React.createElement("input", __assign({ className: "form-check mt-1", type: "checkbox" }, field, props, { checked: field.value, onChange: function (e) { return checkboxChange(e, field.onChange); } })))));
};
export var CPIField = function (_a) {
    var field = _a.field, _b = _a.form, touched = _b.touched, errors = _b.errors, props = __rest(_a, ["field", "form"]);
    var fader = props.placeholder ? "" : "fader";
    if (field.value != null) {
        fader = field.value.toString() === "true" ? "" : "fader";
    }
    var className = "btn btn-checkbox " + fader;
    return (React.createElement(Button, __assign({ className: className }, field, props, { placeholder: props.placeholder.toString(), key: field.name + "-button", type: "checkbox", value: field.value, onClick: function (e) {
            e.preventDefault(); // Don't submit form!
            checkboxChange(e, field.onChange, props.placeholder);
        } }),
        "CPI",
        " "));
};
export var TextAreaField = function (_a) {
    var field = _a.field, _b = _a.form, touched = _b.touched, errors = _b.errors, props = __rest(_a, ["field", "form"]);
    if (props.preview) {
        var element = markdownElement(field.value);
    }
    else {
        var element = (React.createElement("textarea", __assign({ className: "form-control" }, field, props, { preview: "", style: inputStyle, onChange: function (e) { return titleChange(e, field.onChange); } })));
    }
    return (React.createElement("div", null,
        React.createElement("label", null,
            React.createElement("b", null,
                props.label,
                ":"),
            element)));
};
export var Message = function (_a) {
    var msg = _a.msg, props = _a.props;
    return (React.createElement("small", { className: "form-text text-muted" }, msg));
};
export var RedMessage = function (_a) {
    var msg = _a.msg, props = _a.props;
    return (React.createElement("p", { className: "form-text font-weight-bold", style: { color: "#dc3545", fontSize: "80%" } }, msg));
};
export var CodeSnippetField = function (_a) {
    var field = _a.field, _b = _a.form, touched = _b.touched, errors = _b.errors, props = __rest(_a, ["field", "form"]);
    if (props.preview) {
        var ticks = "```";
        var markdownText = "" + ticks + props.language + "\n" + field.value + "\n" + ticks;
        var element = markdownElement(markdownText);
    }
    else {
        var element = (React.createElement("textarea", __assign({ className: "form-control" }, field, props, { preview: "", style: inputStyle })));
    }
    return (React.createElement("div", null,
        React.createElement("label", null,
            React.createElement("b", null, props.label + ":"),
            " ",
            props.description,
            element)));
};
export var ServerSizeField = function (_a) {
    var field = _a.field, _b = _a.form, touched = _b.touched, errors = _b.errors, props = __rest(_a, ["field", "form"]);
    return (React.createElement("div", null,
        React.createElement("label", null,
            React.createElement("b", null, "Server size: "),
            "Choose the server size that best meets the requirements of this app"),
        React.createElement("p", null,
            React.createElement("select", { name: "server_size", onChange: field.onChange },
                React.createElement("option", { multiple: true, value: [4, 2] }, "4 GB 2 vCPUs"),
                React.createElement("option", { multiple: true, value: [8, 2] }, "8 GB 2 vCPUs"),
                React.createElement("option", { multiple: true, value: [16, 4] }, "16 GB 4 vCPUs"),
                React.createElement("option", { multiple: true, value: [32, 8] }, "32 GB 8 vCPUs")))));
};
export var SelectField = function (_a) {
    var field = _a.field, form = _a.form, props = __rest(_a, ["field", "form"]);
    var initVal;
    if (field.value) {
        initVal = Array.isArray(field.value) ? field.value.join(",") : field.value;
    }
    else {
        initVal = "";
    }
    var _b = React.useState(initVal), value = _b[0], setValue = _b[1];
    var handleBlur = function (e) {
        form.setFieldValue(field.name, e.target.value);
        form.setFieldTouched(field.name, true);
    };
    return (React.createElement(React.Fragment, null,
        React.createElement("input", { className: "form-control", list: "datalist-" + field.name, id: "datalist-" + field.name + "-choice", placeholder: props.placeholder, name: field.name, onChange: function (e) { return setValue(e.target.value); }, onBlur: handleBlur, value: value, style: props.style }),
        React.createElement("datalist", { id: "datalist-" + field.name }, props.options)));
};
export function getField(fieldName, data, placeholder, style, isMulti) {
    if (style === void 0) { style = {}; }
    if (isMulti === void 0) { isMulti = false; }
    var makeOptions = function (choices) {
        var opts = choices.map(function (choice) { return (React.createElement("option", { key: choice.toString(), value: choice }, choice.toString())); });
        return opts;
    };
    var choices;
    if (data.type == "bool") {
        choices = ["true", "false"];
    }
    else if (data.validators &&
        data.validators.choice &&
        data.validators.choice.choices) {
        choices = data.validators.choice.choices;
    }
    if (choices) {
        if (isMulti) {
            return (React.createElement(FastField, { name: fieldName, component: SelectField, options: makeOptions(choices), placeholder: placeholder, style: style }));
        }
        else {
            return (React.createElement(FastField, { name: fieldName, className: "form-control", component: "select", placeholder: placeholder, style: style }, makeOptions(data.validators.choice.choices)));
        }
    }
    else {
        return (React.createElement(FastField, { className: "form-control", name: fieldName, placeholder: placeholder, style: style }));
    }
}
//# sourceMappingURL=fields.js.map