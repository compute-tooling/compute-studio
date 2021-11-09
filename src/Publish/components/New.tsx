import { Step } from "bokehjs";
import { ErrorMessage, Field, Form, FormikProps } from "formik";
import React = require("react");
import { Col, Row } from "react-bootstrap";
import { Message } from ".";
import { Project, AccessStatus } from "../../types";
import { inputStyle, techGuideLinks, techTitles } from "../constants";
import { ProjectValues } from "../types";
import { PublicPrivateRadio } from "./PublicPrivate";
import { PythonParamTools } from "./PythonParamTools";
import { TechSelect } from "./TechSelect";
import { VizWithServer } from "./VizWithServer";

const NewProjectForm: React.FC<{
  props: FormikProps<ProjectValues>;
  project?: Project;
}> = ({ props, project }) => (
  <>
    <>
      <Row className="w-100 justify-content-between">
        <Col className="col-9">
          <label>
            <b>Repo URL:</b> Link to the project's code repository
          </label>
          <div className="mt-1 mb-1">
            <Field
              className="form-control w-50rem"
              type="url"
              name="repo_url"
              placeholder="https://..."
              style={inputStyle}
              onBlur={() => {
                const { repo_url, title } = props.values || {};
                if (repo_url && !title) {
                  const pieces = repo_url.split("/");
                  const title = pieces[pieces.length - 1].replace("/", "");
                  props.setFieldValue("title", title);
                }
              }}
            />
            <ErrorMessage name="repo_url" render={msg => <Message msg={msg} />} />
          </div>
        </Col>
        <Col className="col-3">
          <label>
            <b>Title</b>
          </label>
          <div className="mt-1 mb-1">
            <Field
              className="form-control w-50rem"
              type="text"
              name="title"
              placeholder="My awesome project"
              style={inputStyle}
              onChange={e => {
                e.target.value = e.target.value.replace(/[^a-zA-Z0-9]+/g, "-");
                props.setFieldValue("title", e.target.value);
              }}
            />
          </div>
        </Col>
      </Row>
      <Row className="w-100 pt-4">
        <Col className="col-6">
          <label>
            <b>Repo Tag:</b> Your project will be deployed from here
          </label>
          <div className="mt-1 mb-1">
            <Field
              className="form-control w-50rem"
              type="text"
              name="repo_tag"
              placeholder="Link to the model's code repository"
              style={inputStyle}
            />
            <ErrorMessage name="repo_tag" render={msg => <Message msg={msg} />} />
          </div>
        </Col>
      </Row>
      <div className="mt-4">
        <PublicPrivateRadio props={props} project={project} />
      </div>
      <TechSelect props={props} project={project} />
      {props.values?.tech && (
        <>
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
        </>
      )}
    </>
    <div className="mt-5">
      <button
        className="btn inline-block btn-success"
        type="submit"
        onClick={e => {
          props.submitForm();
        }}
      >
        <strong>{!!project ? "Create app" : "Update app" }</strong>
      </button>
    </div>
  </>
);

export { NewProjectForm };
