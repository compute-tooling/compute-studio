import { Field, ErrorMessage } from "formik";
import React = require("react");
import { Message } from ".";
import { inputStyle } from "../constants";

const SourceCodeFields: React.FC<{}> = ({}) => (
  <div>
    <label>
      <b>Repo URL</b>
    </label>
    <p className="mt-1 mb-1">
      <Field
        className="form-control w-50rem"
        type="url"
        name="repo_url"
        placeholder="Link to the model's code repository"
        style={inputStyle}
      />
      <ErrorMessage name="repo_url" render={msg => <Message msg={msg} />} />
    </p>
    <div className="mt-1 mb-1">
      <label>
        <b>Repo Tag:</b> Your project will be deployed from here
      </label>
      <p className="mt-1 mb-1">
        <Field
          className="form-control w-50rem"
          type="text"
          name="repo_tag"
          placeholder="Link to the model's code repository"
          style={inputStyle}
        />
        <ErrorMessage name="repo_tag" render={msg => <Message msg={msg} />} />
      </p>
    </div>
  </div>
);

export { SourceCodeFields };
