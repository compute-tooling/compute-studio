import * as React from "react";

export const Message = ({ msg }) => (
  <p className={`form-text font-weight-bold`} style={{ color: "#dc3545", fontSize: "80%" }}>
    {msg}
  </p>
);
