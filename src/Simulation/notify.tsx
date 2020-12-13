import * as React from "react";

export const CheckboxWidget: React.FC<{
  message: string | JSX.Element;
  value: boolean;
  setValue: (value: boolean) => void;
  disabled?: boolean;
}> = ({ message, value, setValue, disabled }) => {
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
        disabled={disabled}
      />
      {message}
    </p>
  );
};
