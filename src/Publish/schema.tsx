import { requiredMessage } from "./constants";

var yup = require("yup");

var Schema = yup.object().shape({
  title: yup.string().required(requiredMessage),
  oneliner: yup.string(),
  repo_url: yup.string().url(),
  cpu: yup
    .number()
    .min(1, "CPU must be greater than ${min}.")
    .max(7, "CPU must be less than ${max}."),
  memory: yup
    .number()
    .min(2, "Memory must be greater than ${min}.")
    .max(24, "Memory must be less than ${max}."),
  exp_task_time: yup.number().min(0, "Expected task time must be greater than ${min}."),
  listed: yup.boolean().required(requiredMessage),
  tech: yup.string().required(requiredMessage),
  callable_name: yup.string(),
  is_public: yup.boolean(),
  social_image_link: yup.string().url(),
  use_iframe_resizer: yup.boolean(),
});

export { Schema };
