import { ErrorMessage, Field, FormikProps } from "formik";
import React = require("react");
import { Col, Dropdown, Row } from "react-bootstrap";
import { Message } from ".";
import { Project, Tech } from "../../types";
import { newTechEmail } from "../constants";
import { ProjectValues } from "../types";

const TechSelect: React.FC<{ project: Project; props: FormikProps<ProjectValues> }> = ({
  project,
  props,
}) => (
  <Row className="w-100 justify-content-left">
    <Col className="col-auto">
      <Field name="tech">
        {({ field, meta }) => (
          <TechSelectDropdown
            selectedTech={props.values.tech || !!project ? props.values.tech : null}
            onSelectTech={sel => {
              TechSelect;
              props.setFieldValue("tech", sel);
            }}
          />
        )}
      </Field>
      <ErrorMessage name="tech" render={msg => <Message msg={msg} />} />
    </Col>
  </Row>
);

const TechSelectDropdown: React.FC<{
  selectedTech: Tech | null;
  onSelectTech: (tech: Tech) => void;
}> = ({ selectedTech, onSelectTech }) => {
  const techChoices: Array<Tech> = ["python-paramtools", "bokeh", "dash", "streamlit"];
  return (
    <Dropdown>
      <Dropdown.Toggle variant="outline-primary" id="dropdown-basic" className="w-100">
        {selectedTech ? (
          <span>
            Tech: <strong className="px-3">{selectedTech}</strong>
          </span>
        ) : (
          <strong>Specify technology</strong>
        )}
      </Dropdown.Toggle>
      <Dropdown.Menu>
        {techChoices.map((tech, ix) => (
          <Dropdown.Item
            key={ix}
            href="#"
            className={`w-100 ${selectedTech === tech && "bg-primary"}`}
            onClick={() => onSelectTech(tech)}
          >
            <strong>{tech}</strong>
          </Dropdown.Item>
        ))}
        <Dropdown.Item key="another" href={newTechEmail} className="w-100">
          <strong>Request Another</strong>
        </Dropdown.Item>
      </Dropdown.Menu>
    </Dropdown>
  );
};

export { TechSelect, TechSelectDropdown };
