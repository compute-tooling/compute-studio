import hljs from "highlight.js/lib/highlight";
import python from "highlight.js/lib/languages/python";
import json from "highlight.js/lib/languages/json";
hljs.registerLanguage("python", python);
hljs.registerLanguage("json", json);

import "highlight.js/styles/default.css";
import React from "react";
import Select from "react-select";
import { Button } from "react-bootstrap";
import { FastField } from "formik";

var Remarkable = require("remarkable");

hljs.initHighlightingOnLoad();

const inputStyle = {
  width: "50rem"
};

var md = new Remarkable({
  highlight: function(str, lang) {
    if ((lang && hljs.getLanguage(lang)) || true) {
      try {
        return hljs.highlight(lang, str).value;
      } catch (err) {}
    }

    try {
      return hljs.highlightAuto(str).value;
    } catch (err) {}
    return ""; // use external default escaping
  }
});

function markdownElement(markdownText) {
  // Box is not displayed if markdownText is an empty string.
  if (!markdownText) {
    markdownText = "&#8203;"; // space character
  }
  const marked = {
    __html: md.render(markdownText)
  };
  return (
    <div className="markdown-wrapper mt-2 mb-2">
      <div
        dangerouslySetInnerHTML={marked} // needs to be sanitized somehow.
        className="card publish markdown"
        style={inputStyle}
      />
    </div>
  );
}

function titleChange(e, onChange) {
  if (e.target.name == "title") {
    e.target.value = e.target.value.replace(/[^a-zA-Z0-9]+/g, "-");
  }
  onChange(e);
}

export const TextField = ({ field, form: { touched, errors }, ...props }) => {
  if (props.preview) {
    var element = markdownElement(field.value);
  } else {
    var element = (
      <input
        className="form-control"
        {...field}
        {...props}
        preview=""
        style={inputStyle}
        onChange={e => titleChange(e, field.onChange)}
      />
    );
  }
  return (
    <div>
      <label>
        <b>{props.label}:</b>
        {element}
      </label>
    </div>
  );
};

function checkboxChange(e, onChange, placeholder = null) {
  let value =
    e.target.value != null && e.target.value !== ""
      ? e.target.value
      : placeholder;
  if (typeof value === "boolean") {
    e.target.value = !value;
  } else {
    e.target.value = value === "true" ? false : true;
  }
  onChange(e);
}

export const CheckboxField = ({
  field,
  form: { touched, errors },
  ...props
}) => {
  return (
    <div>
      <label>
        <b>{props.label}</b>
        {props.description ? props.description : ""}
        <input
          className="form-check mt-1"
          type="checkbox"
          {...field}
          {...props}
          checked={field.value}
          onChange={e => checkboxChange(e, field.onChange)}
        />
      </label>
    </div>
  );
};

export const CPIField = ({ field, form: { touched, errors }, ...props }) => {
  let fader = props.placeholder ? "" : "fader";
  if (field.value != null) {
    fader = field.value === "true" ? "" : "fader";
  }
  let className = `btn btn-checkbox ${fader}`;
  return (
    <Button
      className={className}
      {...field}
      {...props}
      placeholder={props.placeholder.toString()}
      key={`${field.name}-button`}
      type="checkbox"
      value={field.value}
      onClick={e => {
        e.preventDefault(); // Don't submit form!
        checkboxChange(e, field.onChange, props.placeholder);
      }}
    >
      CPI{" "}
    </Button>
  );
};

export const TextAreaField = ({
  field,
  form: { touched, errors },
  ...props
}) => {
  if (props.preview) {
    var element = markdownElement(field.value);
  } else {
    var element = (
      <textarea
        className="form-control"
        {...field}
        {...props}
        preview=""
        style={inputStyle}
        onChange={e => titleChange(e, field.onChange)}
      />
    );
  }
  return (
    <div>
      <label>
        <b>{props.label}:</b>
        {element}
      </label>
    </div>
  );
};

export const Message = ({ msg, props }) => (
  <small className={`form-text text-muted`}>{msg}</small>
);

export const RedMessage = ({ msg, props }) => (
  <p
    className={`form-text font-weight-bold`}
    style={{ color: "#dc3545", fontSize: "80%" }}
  >
    {msg}
  </p>
);

export const CodeSnippetField = ({
  field,
  form: { touched, errors },
  ...props
}) => {
  if (props.preview) {
    const ticks = "```";
    const markdownText = `${ticks}${props.language}\n${field.value}\n${ticks}`;
    var element = markdownElement(markdownText);
  } else {
    var element = (
      <textarea
        className="form-control"
        {...field}
        {...props}
        preview=""
        style={inputStyle}
      />
    );
  }
  return (
    <div>
      <label>
        <b>{props.label + ":"}</b> {props.description}
        {element}
      </label>
    </div>
  );
};

export const ServerSizeField = ({
  field,
  form: { touched, errors },
  ...props
}) => {
  return (
    <div>
      <label>
        <b>Server size: </b>Choose the server size that best meets the
        requirements of this app
      </label>
      <p>
        <select name="server_size" onChange={field.onChange}>
          <option multiple={true} value={[4, 2]}>
            4 GB 2 vCPUs
          </option>
          <option multiple={true} value={[8, 2]}>
            8 GB 2 vCPUs
          </option>
          <option multiple={true} value={[16, 4]}>
            16 GB 4 vCPUs
          </option>
          <option multiple={true} value={[32, 8]}>
            32 GB 8 vCPUs
          </option>
        </select>
      </p>
    </div>
  );
};

export const SelectField = ({ field, form, ...props }) => {
  const handleChange = option => {
    if (Array.isArray(option)) {
      var value = option.map(op => op.value);
    } else {
      var value = option.value;
    }
    form.setFieldValue(field.name, value);
    form.setFieldTouched(field.name, true);
  };
  let style = props.style;
  return (
    <Select
      isMulti={!!props.isMulti ? props.isMulti : false}
      options={props.options}
      name={field.name}
      value={
        props.options
          ? props.options.find(option => option.value === field.value)
          : ""
      }
      placeholder={props.placeholder}
      onChange={handleChange}
      onBlur={field.onBlur}
      styles={{ control: styles => ({ ...styles, ...style }) }}
      hideSelectedOptions={false}
    />
  );
};

export function getField(
  fieldName,
  data,
  placeholder,
  style = {},
  isMulti = false
) {
  const makeOptions = choices => {
    let opts = choices.map(choice => {
      return { label: choice.toString(), value: choice };
    });
    if (isMulti) {
      opts.push({ label: "*", value: "*" });
      opts.push({ label: "<", value: "<" });
    }
    return opts;
  };

  if (data.type == "bool") {
    return (
      <FastField
        name={fieldName}
        component={SelectField}
        options={makeOptions([true, false])}
        isMulti={isMulti}
        placeholder={placeholder}
        style={style}
      />
    );
  } else if (
    data.validators &&
    data.validators.choice &&
    data.validators.choice.choices
  ) {
    return (
      <FastField
        name={fieldName}
        component={SelectField}
        options={makeOptions(data.validators.choice.choices)}
        isMulti={isMulti}
        placeholder={placeholder}
        style={style}
      />
    );
  } else {
    return (
      <FastField
        className="form-control"
        name={fieldName}
        placeholder={placeholder}
        style={style}
      />
    );
  }
}
