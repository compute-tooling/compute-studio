import { Field, FormikProps } from "formik";
import React = require("react");
import { Row, Col } from "react-bootstrap";
import { Tip } from "../../components";
import { AccessStatus, Project } from "../../types";
import { ProjectValues } from "../types";
import { ReadmeField } from "./Readme";

export const AboutAppFields: React.FC<{
  accessStatus: AccessStatus;
  props: FormikProps<ProjectValues>;
  project: Project;
  showReadme?: boolean;
}> = ({ accessStatus, props, project, showReadme }) => {
  return (
    <>
      <div>
        {!project && (
          <Field name="title">
            {({ field, meta }) => (
              <label>
                {" "}
                <strong>Title</strong>
                <Row className="justify-content-md-left">
                  {accessStatus.username && (
                    <>
                      <Col className="flex-grow-0 align-self-center">
                        <h5 className="lead font-weight-bold">{accessStatus.username}</h5>
                      </Col>
                      <Col className="flex-grow-0 align-self-center">
                        <p className="lead pt-2">/</p>
                      </Col>
                    </>
                  )}
                  <Col className="flex-grow-0 align-self-center">
                    <input
                      type="text"
                      {...field}
                      onChange={e => {
                        e.target.value = e.target.value.replace(/[^a-zA-Z0-9]+/g, "-");
                        field.onChange(e);
                      }}
                    />
                    {meta.touched && meta.error && <div className="text-danger">{meta.error}</div>}
                  </Col>
                </Row>
              </label>
            )}
          </Field>
        )}
      </div>
      <div className="my-2">
        <label>
          <strong>Description</strong>
          <span className="text-muted ml-1">(optional)</span>
        </label>
        <Field name="oneliner">
          {({ field, meta }) => (
            <Row className="w-100">
              <Col>
                <input type="text" className="w-100" {...field} />
                {meta.touched && meta.error && <div className="text-danger">{meta.error}</div>}
              </Col>
            </Row>
          )}
        </Field>
      </div>
      {showReadme && <ReadmeField />}

      {showReadme && (
        <div className="mt-4 mb-2">
          <label>
            <strong>Social Image URL</strong>
            <span className="ml-2">
              <Tip
                id="social-image-info"
                tip="This will be used when sharing your app on social media."
              >
                <i className="fas fa-info-circle"></i>
              </Tip>
            </span>
          </label>
          <Field name="social_image_link">
            {({ field, meta }) => (
              <Row className="w-100">
                <Col>
                  <input type="url" className="w-100" {...field} />
                  {meta.touched && meta.error && <div className="text-danger">{meta.error}</div>}
                </Col>
              </Row>
            )}
          </Field>
        </div>
      )}
    </>
  );
};
