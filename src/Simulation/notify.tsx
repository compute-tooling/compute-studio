import * as React from "react";

export const CheckboxWidget: React.FC<{
  message: string;
  value: boolean;
  setValue: (value: boolean) => void;
}> = ({ message, value, setValue }) => {
  return (
    // alignment on run model dialog window.
    <p className="mt-2 mb-1">
      <input
        name="notify"
        className="form-check mr-2"
        type="checkbox"
        checked={value}
        onChange={() => setValue(!value)}
        style={{ display: "inline" }}
      />
      {message}
    </p>
  );
};
