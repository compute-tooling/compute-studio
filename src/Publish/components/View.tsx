import React = require("react");
import { Jumbotron, Row, Col } from "react-bootstrap";
import ReactMarkdown = require("react-markdown");
import { Project, AccessStatus } from "../../types";
import { techLinks, techTitles } from "../constants";
import { AppTitle } from "./Title";

const ViewProject: React.FC<{
  project: Project;
  accessStatus: AccessStatus;
}> = ({ project, accessStatus }) => {
  const id = `${project.owner}/${project.title}`;
  const goto = project.tech === "python-paramtools" ? `/${id}/new/` : `/${id}/viz/`;
  const image = node => (
    <div className="container-fluid">
      <img className="h-100 w-100" src={node.src} alt={node.alt} style={{ objectFit: "cover" }} />
    </div>
  );
  return (
    <Jumbotron className="shadow" style={{ backgroundColor: "white" }}>
      <Row className="justify-content-between mb-2">
        <Col className="col-auto align-self-center">
          <AppTitle project={project} />
        </Col>
        {accessStatus.can_write_project && (
          <Col className="col-auto align-self-center">
            <a
              className="btn btn-outline-primary"
              href={`/${project.owner}/${project.title}/settings/`}
            >
              <i className="fa fa-cog mr-2"></i>Settings
            </a>
          </Col>
        )}
      </Row>
      <p className="lead">{project.oneliner}</p>
      <hr className="my-4" />
      <ReactMarkdown source={project.description} escapeHtml={false} renderers={{ image: image }} />
      <Row className="justify-content-between mt-5">
        <Col className="col-auto align-self-center">
          {project.status === "running" ? (
            <a className="btn btn-success" href={goto}>
              <strong>Go to App</strong>
            </a>
          ) : project.status === "staging" ? (
            <strong>Our team is preparing your app to be published.</strong>
          ) : (
            <a className="btn btn-success" href={`/${project.owner}/${project.title}/settings/`}>
              <strong>Connect App</strong>
            </a>
          )}
        </Col>
        <Col className="col-auto align-self-center">
          {project.tech && (
            <p>
              Built with{" "}
              <a href={techLinks[project.tech]}>
                <strong>{techTitles[project.tech]}</strong>
              </a>
              .
            </p>
          )}
        </Col>
      </Row>
    </Jumbotron>
  );
};

export { ViewProject };
