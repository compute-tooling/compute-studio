import * as React from "react";

const SpecialRequests: React.FC<{}> = () => (
  <div>
    <p>
      You may contact the Compute Studio admin at
      <a href="mailto:hank@compute.studio"> hank@compute.studio</a> to discuss:
    </p>
    <ul>
      <li>giving collaborators write-access to this app's publish details.</li>
      <li>special accomodations that need to be made for this model.</li>
      <li>any questions or feedback about the publish process.</li>
    </ul>
  </div>
);

export { SpecialRequests };
