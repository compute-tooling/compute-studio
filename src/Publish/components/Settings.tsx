import { FormikProps } from "formik";
import React = require("react");
import { Card, Col, Form, ListGroup, Row } from "react-bootstrap";
import {
  AboutAppFields,
  AdvancedFields,
  Access,
  PythonParamTools,
  SourceCodeFields,
  TechSelect,
  VizWithServer,
} from ".";
import { Project, AccessStatus } from "../../types";
import { ProjectValues, ProjectSettingsSection } from "../types";
import { SettingsSidebar } from "./SettingsSidebar";

const ProjectSettings: React.FC<{
  props: FormikProps<ProjectValues>;
  project?: Project;
  accessStatus: AccessStatus;
  section?: ProjectSettingsSection;
}> = ({ props, project, accessStatus, section }) => {
  return (
    <>
      <Row>
        <Col className="col-3">
          <SettingsSidebar project={project} section={section} />
        </Col>
        <Col className="col-9">
          <Form>
            {section === "about" && (
              <AboutAppFields
                accessStatus={accessStatus}
                props={props}
                project={project}
                showReadme={true}
              />
            )}

            {section === "configure" && (
              <>
                <div className="py-2">
                  <TechSelect props={props} project={project} />
                </div>
                {props.values.tech === "python-paramtools" && <PythonParamTools />}
                {["bokeh", "dash", "streamlit"].includes(props.values.tech) && (
                  <VizWithServer tech={props.values.tech} />
                )}
              </>
            )}

            {section === "environment" && (
              <div className="py-2">
                <SourceCodeFields />
                <AdvancedFields />
              </div>
            )}

            {section === "access" && (
              <div className="py-2">
                <Access props={props} project={project} />
              </div>
            )}

            <button
              className="btn inline-block btn-success mt-5"
              type="submit"
              onClick={e => {
                e.preventDefault();
                props.submitForm();
              }}
            >
              <strong>Save changes</strong>
            </button>
          </Form>
        </Col>
      </Row>
    </>
  );
};

export { ProjectSettings };
