import React = require("react");
import { Project } from "../../types";

const AppTitle: React.FC<{ project: Project }> = ({ project }) => {
  const isMobile = window.innerWidth < 992;
  const id = `${project.owner}/${project.title}`;
  if (isMobile) {
    return (
      <>
        <p className="font-weight-light primary-text mb-0">
          <a href={`/${project.owner}/`}>{project.owner}</a> /
        </p>
        <a href={`/${id}/`} className="primary-text">
          <p className="lead font-weight-bold">{project.title}</p>
        </a>
      </>
    );
  } else {
    return (
      <>
        <h1 className="display-5">
          <a href={`/${project.owner}/`} className="primary-text">
            <span className="font-weight-light">{project.owner}</span>
          </a>
          <span className="font-weight-light mx-1">/</span>
          <a href={`/${id}/`} className="primary-text">
            <span className="font-weight-bold">{project.title}</span>
          </a>
        </h1>
      </>
    );
  }
};

export { AppTitle };
