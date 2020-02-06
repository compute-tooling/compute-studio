import * as React from "react";

import { OverlayTrigger, Tooltip } from "react-bootstrap";

export const Tip: React.FC<{ tip: string; children: JSX.Element }> = ({ tip, children }) => (
  <OverlayTrigger
    placement="top"
    delay={{ show: 400, hide: 400 }}
    overlay={props => (
      <Tooltip {...props} show={props.show.toString()}>
        {tip}
      </Tooltip>
    )}
  >
    {children}
  </OverlayTrigger>
);
