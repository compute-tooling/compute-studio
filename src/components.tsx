import * as React from "react";

import { OverlayTrigger, Tooltip, Card } from "react-bootstrap";

export const Tip: React.FC<{
  id: string;
  tip: string;
  children: JSX.Element;
  placement?: "top" | "bottom";
}> = ({ id, tip, children, placement = "top" }) => (
  <OverlayTrigger
    placement={placement}
    delay={{ show: 400, hide: 400 }}
    overlay={props => (
      <Tooltip id={id} {...props}>
        {tip}
      </Tooltip>
    )}
  >
    {children}
  </OverlayTrigger>
);

export const FocusableCard: React.FC<{
  children: JSX.Element;
  className?: string;
  onClick?: (event: React.MouseEvent<HTMLDivElement, MouseEvent>) => void;
  style?: React.CSSProperties;
}> = ({ children, className, onClick, style }) => {
  const [focus, setFocus] = React.useState(false);

  let baseStyle: React.CSSProperties = { borderRadius: "2px" };
  if (style) baseStyle = { ...baseStyle, ...style };
  if (focus) baseStyle = { ...baseStyle, backgroundColor: "rgb(245, 248, 250)", cursor: "pointer" };

  return (
    <Card
      onMouseEnter={() => {
        setFocus(true);
      }}
      onMouseLeave={() => {
        setFocus(false);
      }}
      style={baseStyle}
      className={className}
      onClick={onClick}
    >
      {children}
    </Card>
  );
};
