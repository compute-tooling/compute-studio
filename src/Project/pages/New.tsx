import { Step } from "bokehjs";
import { ErrorMessage, Field, Form, FormikProps } from "formik";
import React = require("react");
import { Project, AccessStatus } from "../../types";
import { techGuideLinks, techTitles } from "../constants";
import { ProjectValues } from "../types";
import { PublicPrivateRadio } from "./PublicPrivate";
import { PythonParamTools } from "./PythonParamTools";
import { ReadmeField } from "./Readme";
import { SourceCodeFields } from "./SourceCode";
import { TechSelect } from "./TechSelect";
import { VizWithServer } from "./VizWithServer";
import { Message } from "../components";

const NewProjectForm: React.FC<{
  props: FormikProps<ProjectValues>;
  project?: Project;
  accessStatus: AccessStatus;
  step: Step;
}> = ({ props, project, accessStatus, step }) => (
  <Form>
    {step === (("create" as unknown) as Step) && (
      <>
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
              // style={inputStyle}
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
                // style={inputStyle}
              />
              <ErrorMessage name="repo_tag" render={msg => <Message msg={msg} />} />
            </p>
          </div>
        </div>

      </>
    )}

    <div className="mt-5">
      <button className="btn inline-block btn-success" type="submit">
        <strong>{step === (("create" as unknown) as Step) ? "Create app" : "Connect app"}</strong>
      </button>
    </div>

    {!project && (
      <p className="mt-3">Next, you will learn how to connect your app based on your technology.</p>
    )}
  </Form>
);

export { NewProjectForm };
