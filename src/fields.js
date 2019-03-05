import hljs from "highlight.js";
import "highlight.js/styles/default.css";
import React from "react";

var sanitizeHtml = require("sanitize-html");
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
    __html: sanitizeHtml(md.render(markdownText))
  };
  return (
    <div className="markdown-wrapper">
      <div
        dangerouslySetInnerHTML={marked}
        className="content card publish markdown"
        style={inputStyle}
      />
    </div>
  );
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

export const Message = ({ msg }) => (
  <small className="form-text text-muted">{msg}</small>
);

export const DescriptionField = ({
  field,
  form: { touched, errors },
  ...props
}) => {
  const charsLeft = 1000 - field.value.length;
  if (props.preview) {
    var element = markdownElement(field.value);
  } else {
    var element = (
      <textarea
        className="form-control description"
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
        <b>App overview:</b>
        {element}
      </label>
      <small className="align-bottom" style={{ padding: "2px" }}>
        {charsLeft}
      </small>
    </div>
  );
};

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
      <label>Choose the server size</label>
      <select name="server_size" onChange={field.onChange}>
        <option multiple={true} value={[4, 2]}>
          4 GB 2 vCPUs
        </option>
        <option multiple={true} value={[8, 4]}>
          8 GB 4 vCPUs
        </option>
        <option multiple={true} value={[16, 8]}>
          16 GB 8 vCPUs
        </option>
        <option multiple={true} value={[32, 16]}>
          32 GB 16 vCPUs
        </option>
        <option multiple={true} value={[64, 32]}>
          64 GB 32 vCPUs
        </option>
      </select>
    </div>
  );
};
