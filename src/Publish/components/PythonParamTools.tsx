import { Field, ErrorMessage } from "formik";
import React = require("react");
import { Message } from ".";
import { inputStyle } from "../constants";

const PythonParamTools: React.FC<{}> = ({}) => {
  return (
    <div>
      <div className="my-3" />
      <div className="mt-1 mb-1">
        <label>
          <b>Expected job time:</b> Time in seconds for simulation to complete
        </label>
        <p className="mt-1 mb-1">
          <Field
            className="form-control w-50rem"
            type="number"
            name="exp_task_time"
            style={inputStyle}
          />
          <ErrorMessage name="exp_task_time" render={msg => <Message msg={msg} />} />
        </p>
      </div>
    </div>
  );
};

export { PythonParamTools };
