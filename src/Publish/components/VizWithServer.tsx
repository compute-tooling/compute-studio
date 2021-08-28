import { Field, ErrorMessage } from "formik";
import React = require("react");
import { CheckboxField, Message } from "../../fields";
import { Tech } from "../../types";

const VizWithServer: React.FC<{ tech: Tech }> = ({ tech }) => {
  const title = {
    dash: "Dash",
    bokeh: "Bokeh",
    streamlit: "Streamlit",
  }[tech];
  return (
    <div>
      <div className="my-3" />
      {tech === "dash" && (
        <div className="mt-1 mb-1">
          <label>
            <b>Function Name</b>
          </label>
          <Field name="callable_name">
            {({ field, meta }) => (
              <div>
                <input
                  type="text"
                  className="form-control w-50"
                  {...field}
                  placeholder={`Name of the ${title} server.`}
                  onChange={e => {
                    let val = e.target.value.replace(/[^a-zA-Z0-9]+/g, "_");
                    e.target.value = val;
                    field.onChange(e);
                  }}
                />
                {meta.touched && meta.error && <Message msg={meta.error} />}
              </div>
            )}
          </Field>
          <ErrorMessage name="callable_name" render={msg => <Message msg={msg} />} />
        </div>
      )}
      <div className="mt-1 mb-1">
        <label>
          <b>App Location</b>
        </label>
        <div>
          <Field
            required={tech === "bokeh"}
            name="app_location"
            placeholder="Directory or file containing app."
            className="w-50"
          />
          <ErrorMessage name="app_location" render={msg => <Message msg={msg} />} />
        </div>
      </div>
      <div className="mt-1 mb-1">
        <label>
          <b>Embed Background Color</b>
        </label>
        <div>
          <Field
            required={false}
            name="embed_background_color"
            placeholder="white"
            className="w-50"
          />
          <ErrorMessage name="embed_background_color" render={msg => <Message msg={msg} />} />
        </div>
      </div>
      <p className="mt-3">
        <label>
          <Field
            component={CheckboxField}
            label="Use iframe resizer: "
            description="Use the iframe-resizer library when embedding this project."
            name="use_iframe_resizer"
            className="mt-1 d-inline-block mr-2"
          />
          <strong>Use Iframe Resizer:</strong>
          <span className="ml-1">
            Use the <a href="https://github.com/davidjbradshaw/iframe-resizer">iframe-resizer</a>{" "}
            library when embedding this project.
          </span>
        </label>
      </p>
    </div>
  );
};

export { VizWithServer };
