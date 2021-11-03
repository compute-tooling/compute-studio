import { ProjectValues } from "./types";

const initialValues: ProjectValues = {
  title: "",
  description: "",
  oneliner: "",
  repo_url: "",
  repo_tag: "master",
  cpu: 1,
  memory: 2,
  exp_task_time: 0,
  listed: true,
  tech: null,
  callable_name: "",
  is_public: true,
  social_image_link: null,
  embed_background_color: "white",
  use_iframe_resizer: false,
};

export { initialValues };
