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
          <Card>
            <Card.Header>Settings</Card.Header>
            <ListGroup variant="flush">
              <ListGroup.Item>
                <a href={`/${project.owner}/${project.title}/settings/about/`}>
                  <span className={section === "about" && "font-weight-bold"}>About</span>
                </a>
              </ListGroup.Item>
              <ListGroup.Item>
                <a href={`/${project.owner}/${project.title}/settings/configure/`}>
                  <span className={section === "configure" && "font-weight-bold"}>Configure</span>
                </a>
              </ListGroup.Item>
              <ListGroup.Item>
                <a href={`/${project.owner}/${project.title}/settings/environment/`}>
                  <span className={section === "environment" && "font-weight-bold"}>
                    Environment
                  </span>
                </a>
              </ListGroup.Item>
              <ListGroup.Item>
                <a href={`/${project.owner}/${project.title}/settings/access/`}>
                  <span className={section === "access" && "font-weight-bold"}>Access</span>
                </a>
              </ListGroup.Item>
            </ListGroup>
          </Card>
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
