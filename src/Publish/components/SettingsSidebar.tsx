import React = require("react");
import { Card, ListGroup } from "react-bootstrap";
import { Project } from "../../types";
import { ProjectSettingsSection } from "../types";

const SettingsSidebar: React.FC<{ project: Project; section: ProjectSettingsSection }> = ({
  project,
  section,
}) => (
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
          <span className={section === "environment" && "font-weight-bold"}>Environment</span>
        </a>
      </ListGroup.Item>
      <ListGroup.Item>
        <a href={`/${project.owner}/${project.title}/settings/access/`}>
          <span className={section === "access" && "font-weight-bold"}>Access</span>
        </a>
      </ListGroup.Item>
      <ListGroup.Item>
        <a href={`/${project.owner}/${project.title}/builds/`}>
          <span className={section === "build-history" && "font-weight-bold"}>Builds</span>
        </a>
      </ListGroup.Item>
    </ListGroup>
  </Card>
);

export { SettingsSidebar };
