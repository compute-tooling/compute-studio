import { Field, FormikProps } from "formik";
import React = require("react");
import { PublicPrivateRadio } from ".";
import { CheckboxField } from "../../fields";
import { Project } from "../../types";
import { ProjectValues } from "../types";

const Access: React.FC<{ props: FormikProps<ProjectValues>; project: Project }> = ({
  props,
  project,
}) => (
  <>
    <div className="mb-2">
      <PublicPrivateRadio props={props} project={project} />
    </div>
    {props.values.is_public && project.status === "running" && (
      <p className="my-2">
        <label>
          <Field
            component={CheckboxField}
            label="Listed: "
            description="Include this app in the public list of apps"
            name="listed"
            className="mt-1 d-inline-block mr-2"
          />
          <strong>Listed:</strong>
          <span className="ml-1">Include this app in the public list of apps.</span>
        </label>
      </p>
    )}
  </>
);

export { Access };
