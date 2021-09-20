import { FormikProps } from "formik";
import React = require("react");
import { Project } from "../../types";
import { ProjectValues } from "../types";

const PublicPrivateRadio: React.FC<{ props: FormikProps<ProjectValues>; project?: Project }> = ({
  props,
  project,
}) => (
  <>
    <p>
      <label>
        <input
          id="make-public"
          name="is_public"
          type="radio"
          checked={props.values.is_public}
          onChange={() => props.setFieldValue("is_public", true)}
        />
        <span className="ml-1">
          <strong>Public:</strong> Anyone on the internet can see and use this app.{" "}
          {project?.status !== "running" &&
            "You will be given an option later to make it discoverable."}
        </span>
      </label>
    </p>
    <p>
      <label>
        <input
          id="make-private"
          name="is_public"
          type="radio"
          checked={!props.values.is_public}
          onChange={() => props.setFieldValue("is_public", false)}
        />
        <span className="ml-1">
          <strong>Private:</strong> You choose who can see and use this app.
        </span>
      </label>
    </p>
  </>
);

export { PublicPrivateRadio };
