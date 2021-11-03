import { ErrorMessage, Field, FormikProps } from "formik";
import React = require("react");
import { Row, Col } from "react-bootstrap";
import { Tip } from "../../components";
import { AccessStatus, Project } from "../../types";
import { inputStyle } from "../constants";
import { ProjectValues } from "../types";
import { ReadmeField } from "./Readme";

export const AboutAppFields: React.FC<{}> = ({}) => {
  return (
    <>
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
      <ReadmeField />

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
    </>
  );
};
