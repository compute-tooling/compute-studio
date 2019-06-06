import hljs from "highlight.js/lib/highlight";
import python from "highlight.js/lib/languages/python";
import json from "highlight.js/lib/languages/json";
hljs.registerLanguage("python", python);
hljs.registerLanguage("json", json);

import "highlight.js/styles/default.css";
import React from "react";
import { Field } from "formik";

var Remarkable = require("remarkable");

hljs.initHighlightingOnLoad();

const inputStyle = {
  width: "50rem"
};

var md = new Remarkable({
  highlight: function (str, lang) {
    if ((lang && hljs.getLanguage(lang)) || true) {
      try {
        return hljs.highlight(lang, str).value;
      } catch (err) { }
    }

    try {
      return hljs.highlightAuto(str).value;
    } catch (err) { }
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

function checkboxChange(e, onChange) {
  e.target.value = !e.target.value;
  onChange(e)
}

export const CheckboxField = ({ field, form: { touched, errors }, ...props }) => {
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
}

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
  <small className={`form-text text-muted ${props}`}>{msg}</small>
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
