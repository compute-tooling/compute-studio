import { Field, ErrorMessage } from "formik";
import React = require("react");
import { SpecialRequests } from ".";
import { inputStyle } from "../constants";
import { Message } from "./Message";

const AdvancedFields: React.FC<{}> = ({}) => {
  return (
    <div>
      <details className="my-2">
        <summary>
          <span className="h6">Advanced Configuration</span>
        </summary>
        <div className="mt-1">
          <p className="lead">Resource Requirements</p>
          <div className="my-3" />
          <div className="mt-1 mb-1">
            <label>CPUs required:</label>
            <p className="mt-1 mb-1">
              <Field
                className="form-control w-50rem"
                type="number"
                step="0.1"
                name="cpu"
                style={inputStyle}
              />
              <ErrorMessage name="cpu" render={msg => <Message msg={msg} />} />
            </p>
          </div>
          <div className="mt-1 mb-1">
            <label>Memory (GB) required:</label>
            <p className="mt-1 mb-1">
              <Field
                className="form-control w-50rem"
                type="number"
                step="0.1"
                name="memory"
                style={inputStyle}
              />
              <ErrorMessage name="memory" render={msg => <Message msg={msg} />} />
            </p>
          </div>
        </div>
        <SpecialRequests />
      </details>
    </div>
  );
};

export { AdvancedFields };
