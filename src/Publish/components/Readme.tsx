import { Field } from "formik";
import React = require("react");
import { Row, Col } from "react-bootstrap";
import { Tip } from "../../components";

const ReadmeField: React.FC<{}> = ({}) => (
  <div className="mt-3 mb-1">
    <label>
      <strong>README</strong>{" "}
      <Tip id="readme-markdown-icon" tip="Supports Markdown." placement="top">
        <a href="https://hackmd.io/new" target="_blank">
          <i className="fab fa-markdown mr-3" style={{ opacity: 0.8 }}></i>
        </a>
      </Tip>
    </label>
    <Field name="description">
      {({ field, meta }) => (
        <Row className="w-100">
          <Col>
            <textarea type="text" className="w-100" rows="10" {...field} />
            {meta.touched && meta.error && <div className="text-danger">{meta.error}</div>}
          </Col>
        </Row>
      )}
    </Field>
  </div>
);

export { ReadmeField };
