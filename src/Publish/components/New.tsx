import { Step } from "bokehjs";
import { Form, FormikProps } from "formik";
import React = require("react");
import { AboutAppFields } from ".";
import { Project, AccessStatus } from "../../types";
import { techGuideLinks, techTitles } from "../constants";
import { ProjectValues } from "../types";
import { PublicPrivateRadio } from "./PublicPrivate";
import { PythonParamTools } from "./PythonParamTools";
import { ReadmeField } from "./Readme";
import { SourceCodeFields } from "./SourceCode";
import { TechSelect } from "./TechSelect";
import { VizWithServer } from "./VizWithServer";

const NewProjectForm: React.FC<{
  props: FormikProps<ProjectValues>;
  project?: Project;
  accessStatus: AccessStatus;
  step: Step;
}> = ({ props, project, accessStatus, step }) => (
  <Form>
    {step === (("create" as unknown) as Step) && (
      <>
        <AboutAppFields
          accessStatus={accessStatus}
          props={props}
          project={project}
          showReadme={false}
        />
        <div className="mt-4">
          <PublicPrivateRadio props={props} project={project} />
        </div>
        <TechSelect props={props} project={project} />
      </>
    )}
    {project && !((["running", "staging"] as unknown) as Step[]).includes(step) && (
      <>
        <ReadmeField />
        <div className="py-4">
          <h5>Connect app:</h5>
          <TechSelect props={props} project={project} />
        </div>
        <div className="py-2">
          <i>
            Go to the{" "}
            <a href={`${techGuideLinks[props.values.tech]}`} target="_blank">
              {techTitles[props.values.tech]} guide
            </a>{" "}
            for more information.
          </i>
        </div>
        {props.values.tech === "python-paramtools" && <PythonParamTools />}
        {["bokeh", "dash", "streamlit"].includes(props.values.tech) && (
          <VizWithServer tech={props.values.tech} />
        )}
        <div className="py-4">
          <SourceCodeFields />
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
