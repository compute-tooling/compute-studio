import * as React from "react";

import { OverlayTrigger, Tooltip } from "react-bootstrap";

export const Tip: React.FC<{
  tip: string;
  children: JSX.Element;
  placement?: "top" | "bottom";
}> = ({ tip, children, placement = "top" }) => (
  <OverlayTrigger
    placement={placement}
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
