import API from "./API";
import { AccessStatus, Project, Tech } from "../types";

type Step = "create" | "configure" | "advanced" | "staging" | "access";

type ProjectSettingsSection = "about" | "configure" | "environment" | "access" | "build-history";

interface ProjectValues {
  title: string;
  description: string | null;
  oneliner: string;
  repo_url: string;
  repo_tag: string;
  cpu: number;
  memory: number;
  exp_task_time: number;
  listed: boolean;
  tech: Tech | null;
  callable_name: string;
  is_public: boolean;
  social_image_link: string;
  embed_background_color: string;
  use_iframe_resizer: boolean;
}

interface PublishProps {
  initialValues: ProjectValues;
  project?: Project;
  accessStatus: AccessStatus;
  resetAccessStatus: () => void;
  api: API;
  edit?: boolean;
  section?: ProjectSettingsSection;
}

type PublishState = Readonly<{
  initialValues: ProjectValues;
}>;

interface Match {
  params: { username: string; app_name: string; vizTitle?: string; build_id?: number };
}

export { Step, ProjectSettingsSection, ProjectValues, PublishProps, PublishState, Match };
