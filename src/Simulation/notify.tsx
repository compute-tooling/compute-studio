import * as React from "react";

export const NotifyOnCompletion: React.FC<{
  notify: boolean;
  setNotify: (notify: boolean) => void;
}> = ({ notify, setNotify }) => {
  console.log(notify);
  const toggleNotify = () => {
    setNotify(!notify);
  };
  return (
    // alignment on run model dialog window.
    <p className="mt-2 mb-1">
      <input
        name="notify"
        className="form-check mr-2"
        type="checkbox"
        checked={notify}
        onChange={toggleNotify}
        style={{ display: "inline" }}
      />
      Email me when ready
    </p>
  );
};
