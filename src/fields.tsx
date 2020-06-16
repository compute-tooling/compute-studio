import * as hljs from "highlight.js/lib/highlight";
import * as python from "highlight.js/lib/languages/python";
import * as json from "highlight.js/lib/languages/json";
hljs.registerLanguage("python", python);
hljs.registerLanguage("json", json);

import "highlight.js/styles/default.css";
import * as React from "react";
import { Button, Row, Col } from "react-bootstrap";
import { FastField, FieldProps, FieldArray, Field } from "formik";
import { ParamToolsParam } from "./types";
import { dlv } from "./utils";
import { cloneDeep } from "lodash";

interface CustomFieldProps {
  label: string;
  preview: boolean;
  exitPreview: () => void;
  description?: string;
  allowSpecialChars?: boolean;
  style?: any;
}

var Remarkable = require("remarkable");

hljs.initHighlightingOnLoad();

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

export function markdownElement(markdownText, exitPreview: () => void, style: any = {}) {
  // Box is not displayed if markdownText is an empty string.
  if (!markdownText) {
    markdownText = "&#8203;"; // space character
  }
  const marked = {
    __html: md.render(markdownText)
  };
  return (
    <div className="markdown-wrapper" onClick={exitPreview}>
      <div
        dangerouslySetInnerHTML={marked} // needs to be sanitized somehow.
        className="card publish markdown"
        style={style}
      />
    </div>
  );
}

function titleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, onChange) {
  e.target.value = e.target.value.replace(/[^a-zA-Z0-9]+/g, "-");
  onChange(e);
}

export const TextField = (fieldProps: FieldProps<any> & CustomFieldProps) => {
  const {
    field,
    form: { touched, errors },
    ...props
  } = fieldProps;
  let allowSpecialChars = props.allowSpecialChars !== null ? true : props.allowSpecialChars;
  let style = props.style ? props.style : {};
  if (props.preview) {
    return markdownElement(field.value, props.exitPreview, (style = props.style));
  } else {
    return (
      <input
        className="form-control"
        {...field}
        {...props}
        style={style}
        onChange={e => (allowSpecialChars ? field.onChange(e) : titleChange(e, field.onChange))}
      />
    );
  }
};

function checkboxChange(e: React.ChangeEvent<HTMLInputElement>, onChange, placeholder = null) {
  let value = e.target.value != null && e.target.value !== "" ? e.target.value : placeholder;
  if (typeof value === "boolean") {
    // @ts-ignore
    e.target.value = !value;
  } else {
    // TODO: what is this case
    // @ts-ignore
    e.target.value = value === "true" ? false : true;
  }
  onChange(e);
}

export const CheckboxField = (fieldProps: FieldProps<any> & CustomFieldProps) => {
  const {
    field,
    form: { touched, errors },
    ...props
  } = fieldProps;
  return (
    <input
      className="form-check mt-1"
      type="checkbox"
      {...field}
      {...props}
      checked={field.value}
      onChange={e => checkboxChange(e, field.onChange)}
    />
  );
};

export const CPIField = ({ field, form: { touched, errors }, ...props }) => {
  let fader = props.placeholder ? "" : "fader";
  if (field.value != null) {
    fader = field.value.toString() === "true" ? "" : "fader";
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

export const TextAreaField = ({ field, form: { touched, errors }, ...props }) => {
  let style = props.style ? props.style : {};
  if (props.preview) {
    return markdownElement(field.value, props.exitPreview, style);
  } else {
    return <textarea className="form-control" {...field} {...props} preview="" style={style} />;
  }
};

export const Message = ({ msg }) => <small className={`form-text text-muted`}>{msg}</small>;

export const RedMessage = ({ msg }) => (
  <p className={`form-text font-weight-bold`} style={{ color: "#dc3545", fontSize: "80%" }}>
    {msg}
  </p>
);

export const CodeSnippetField = ({ field, form: { touched, errors }, ...props }) => {
  let style = props.style ? props.style : {};
  if (props.preview) {
    const ticks = "```";
    const markdownText = `${ticks}${props.language}\n${field.value}\n${ticks}`;
    return markdownElement(markdownText, props.exitPreview, style);
  } else {
    return <textarea className="form-control" {...field} {...props} preview="" style={style} />;
  }
};

export const ServerSizeField = ({ field, form: { touched, errors }, ...props }) => {
  return (
    <div>
      <label>
        <b>Server size: </b>Choose the server size that best meets the requirements of this app
      </label>
      <p>
        <select name="server_size" onChange={field.onChange}>
          <option value={["4", "2"]}>4 GB 2 vCPUs</option>
          <option value={["8", "2"]}>8 GB 2 vCPUs</option>
          <option value={["16", "4"]}>16 GB 4 vCPUs</option>
        </select>
      </p>
    </div>
  );
};

export const SelectField = ({ field, form, ...props }) => {
  let initVal;
  if (field.value) {
    initVal = Array.isArray(field.value) ? field.value.join(",") : field.value;
  } else {
    initVal = "";
  }

  const [value, setValue] = React.useState(initVal);

  const handleBlur = e => {
    form.setFieldValue(field.name, e.target.value);
    form.setFieldTouched(field.name, true);
  };

  return (
    <>
      <input
        className="form-control"
        list={`datalist-${field.name}`}
        id={`datalist-${field.name}-choice`}
        placeholder={props.placeholder}
        name={field.name}
        onChange={e => setValue(e.target.value)}
        onBlur={handleBlur}
        value={value}
        style={props.style}
        disabled={props.disabled}
      />
      <datalist id={`datalist-${field.name}`}>{props.options}</datalist>
    </>
  );
};

const oneDimArray = (fieldName, values, data, labelString, placeholder, style, readOnly) => {
  let last;
  let mapAcross;
  if (values.length > 0 && !(values.length === 1 && values[0] === "")) {
    mapAcross = values;
  } else {
    mapAcross = data.form_fields[labelString];
  }
  return (
    <FieldArray
      name={fieldName}
      render={arrayHelpers => (
        <div>
          {mapAcross.map((value, ix) => {
            last = value;
            return (
              <Row key={ix} className="justify-content-start mt-1">
                <Col>
                  <FastField
                    className="form-control"
                    name={`${fieldName}.${ix}`}
                    placeholder={
                      ix <= placeholder.length - 1
                        ? placeholder[ix].toString()
                        : placeholder[placeholder.length - 1].toString()
                    }
                    style={style}
                    disabled={readOnly}
                  />
                </Col>
                <Col>
                  <button
                    className="btn btn-outline-danger btn-sm"
                    type="button"
                    onClick={() => {
                      if (ix === 0) {
                        // fixes gnarly uncontrolled to defined bug.
                        arrayHelpers.form.setFieldValue(fieldName, "");
                        return;
                      }
                      arrayHelpers.remove(ix);
                    }}
                  >
                    <i className="fas fa-minus"></i>
                  </button>
                </Col>
              </Row>
            );
          })}
          <button
            className="btn btn-outline-success btn-sm mt-2"
            type="button"
            onClick={() => {
              arrayHelpers.push(last);
            }}
          >
            <i className="fas fa-plus"></i>
          </button>
        </div>
      )}
    />
  );
};

const twoDimArray = (
  fieldName: string,
  values: any[][],
  data: ParamToolsParam,
  labelString: string | null,
  placeholder: string[][],
  style,
  readOnly: boolean
) => {
  let last;
  let mapAcross;
  if (!values) {
    mapAcross = placeholder;
  } else {
    mapAcross = values;
  }
  return (
    <FieldArray
      name={fieldName}
      render={arrayHelpers => (
        <div>
          {mapAcross.map((value, ix) => {
            last = value;
            return (
              <Row key={ix} className="justify-content-start mt-1">
                <Col className="col-auto">
                  <span className="align-middle">{`${ix + 1}.`}</span>
                </Col>
                {placeholder[0].map((_, xix) => (
                  <Col key={`${fieldName}.${ix}.${xix}`}>
                    <Field
                      // className="form-control"
                      name={`${fieldName}.${ix}.${xix}`}
                      style={style}
                      disabled={readOnly}
                    >
                      {({
                        field, // { name, value, onChange, onBlur }
                        form: { touched }, // also values, setXXXX, handleXXXX, dirty, isValid, status, etc.
                        meta
                      }) => (
                        <div>
                          <input
                            type="text"
                            placeholder={
                              ix <= placeholder.length - 1
                                ? placeholder[ix][xix].toString()
                                : placeholder[placeholder.length - 1][xix].toString()
                            }
                            {...field}
                            className="form-control"
                            onChange={e => {
                              let newValue;
                              if (!values && !dlv(arrayHelpers.form.touched, fieldName)) {
                                newValue = cloneDeep(placeholder);
                              } else {
                                newValue = cloneDeep(values);
                              }
                              newValue[ix][xix] = e.target.value;
                              return arrayHelpers.form.setFieldValue(fieldName, newValue);
                            }}
                          />
                          {/* {meta.touched && meta.error && <div className="error">{meta.error}</div>} */}
                        </div>
                      )}
                    </Field>
                  </Col>
                ))}
                <Col>
                  <button
                    className="btn btn-outline-danger btn-sm"
                    type="button"
                    onClick={() => {
                      if (ix === 0 && !values) {
                        // fixes gnarly uncontrolled to defined bug.
                        let emptyVal = [];
                        for (const ix of placeholder[0]) {
                          emptyVal.push("");
                        }
                        arrayHelpers.form.setFieldValue(fieldName, [emptyVal]);
                        return;
                      }
                      arrayHelpers.remove(ix);
                    }}
                  >
                    <i className="fas fa-minus"></i>
                  </button>
                </Col>
              </Row>
            );
          })}
          <button
            className="btn btn-outline-success btn-sm mt-2"
            type="button"
            onClick={() => {
              if (!values && !dlv(arrayHelpers.form.touched, fieldName)) {
                let newValue = cloneDeep(placeholder);
                newValue.push(cloneDeep(last));
                arrayHelpers.form.setFieldValue(fieldName, newValue, true);
                arrayHelpers.form.setFieldTouched(fieldName, true);
              } else {
                arrayHelpers.push(cloneDeep(last));
              }
            }}
          >
            <i className="fas fa-plus"></i>
          </button>
        </div>
      )}
    />
  );
};

const arrayField = (
  fieldName: string,
  values: any[],
  data: ParamToolsParam,
  labelString: string | null,
  placeholder: string,
  style,
  readOnly: boolean
) => {
  if (data.number_dims === 1) {
    return oneDimArray(fieldName, values, data, labelString, placeholder, style, readOnly);
  } else if (data.number_dims === 2) {
    return twoDimArray(
      fieldName,
      values,
      data,
      labelString,
      (placeholder as unknown) as string[][],
      style,
      readOnly
    );
  }
};

export const getField = (
  fieldName,
  data: ParamToolsParam,
  placeholder,
  readOnly = false,
  style = {},
  isMulti = false,
  values = [],
  labelString: string | null = null
) => {
  const makeOptions = choices => {
    let opts = choices.map(choice => (
      <option key={choice.toString()} value={choice}>
        {choice.toString()}
      </option>
    ));
    return opts;
  };

  let choices;
  if (data.type == "bool") {
    if (placeholder.toString() === "true") {
      choices = ["true", "false"];
    } else {
      choices = ["false", "true"];
    }

  } else if (data.validators && data.validators.choice && data.validators.choice.choices) {
    choices = data.validators.choice.choices;
  }

  if (choices) {
    if (isMulti) {
      return (
        <FastField
          name={fieldName}
          component={SelectField}
          options={makeOptions(choices)}
          placeholder={placeholder.toString()}
          style={style}
          disabled={readOnly}
        />
      );
    } else {
      return (
        <FastField
          name={fieldName}
          className="form-control"
          component="select"
          placeholder={placeholder.toString()}
          style={style}
          disabled={readOnly}
        >
          {makeOptions(choices)}
        </FastField>
      );
    }
  } else if (data.number_dims > 0) {
    return arrayField(fieldName, values, data, labelString, placeholder, style, readOnly);
  } else {
    return (
      <FastField
        className="form-control"
        name={fieldName}
        placeholder={placeholder.toString()}
        style={style}
        disabled={readOnly}
      />
    );
  }
};
