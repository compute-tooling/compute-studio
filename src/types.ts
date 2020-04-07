export interface ValueObject {
  value: number | string | Date | Array<number | string | Date>;
  [key: string]: any;
}

export interface FormValueObject {
  value: Array<any>;
  [key: string]: any;
}

export interface Range {
  min: any;
  max: any;
}

export interface Choice {
  choices: Array<any>;
}

export interface DateRange {
  min: Date;
  max: Date;
}

export interface Validators {
  range?: Range;
  choice?: Choice;
  date_range?: DateRange;
}

export interface ParamToolsParam {
  title: string;
  description: string;
  notes?: string;
  section_1?: string;
  section_2?: string;
  type: "int" | "float" | "bool" | "date";
  number_dims?: number;
  value: Array<ValueObject>;
  validators: Validators;
  form_fields?: any;
  indexable?: boolean;
  checkbox?: boolean;
}

export interface Labels {
  type: "int" | "float" | "bool" | "date";
  validators: Validators;
}

export interface Operators {
  array_first?: boolean;
  label_to_extend?: string;
  uses_extend_func?: boolean;
}

export interface AdditionalMembers {
  [key: string]: { [key: string]: any };
}

export interface Schema {
  labels: Labels;
  operators: Operators;
  additional_members: AdditionalMembers;
}

export interface ParamToolsConfig {
  [paramName: string]: ParamToolsParam;
}

export interface InitialValues {
  adjustment: {
    [msect: string]: {
      [paramName: string]: {
        [voStr: string]: any;
      };
    };
  };
  meta_parameters: { [mpName: string]: any };
}

export interface Sects {
  [msect: string]: {
    [section_1: string]: { [section_2: string]: Array<string> };
  };
}

export interface RemoteOutput {
  id: string;
  screenshot: string;
  title: string;
  media_type:
    | "bokeh"
    | "table"
    | "CSV"
    | "PNG"
    | "JPEG"
    | "MP3"
    | "MP4"
    | "HDF5"
    | "PDF"
    | "Markdown"
    | "Text";
}

export interface Output extends RemoteOutput {
  data: any;
}

export interface TableOutput extends RemoteOutput {
  data: string;
}

export interface BokehLegacyOutput extends RemoteOutput {
  data: { html: string; javascript: string };
}

export interface BokehOutput extends RemoteOutput {
  data: { target_id: string; root_id: string; doc: string };
}

export interface DescriptionValues {
  title: string;
  readme: { [key: string]: any }[] | Node[];
  is_public: boolean;
  author: {
    add: { username: string; msg?: string };
    remove: { username: string };
  };
  access: {
    read: { grant: { username: string; msg?: string }; remove: { username: string } };
  };
}

// Interfaces below correspond to interfaces defined in:
// webapp/apps/comp/serializers.py
// cs_storage/validate.py

export interface RemoteOutputs {
  outputs: {
    renderable: {
      ziplocation: string;
      outputs: Array<RemoteOutput>;
    };
    downloadable: {
      ziplocation: string;
      outputs: Array<RemoteOutput>;
    };
  };
  version: "v0" | "v1";
}

export interface Outputs {
  renderable: Array<Output | TableOutput | BokehOutput>;
  downloadable: Array<Output | TableOutput | BokehOutput>;
}

export type Role = null | "read" | "write" | "admin";

export interface AccessStatus {
  user_status: "inactive" | "customer" | "profile" | "anon";
  username: string;
  api_url: string;
  is_sponsored?: boolean;
  sponsor_message?: string;
  can_run?: boolean;
  server_cost?: number;
  exp_cost?: number;
  exp_time?: number;
  plan: { name: "free" | "plus" | "pro" | "team" };
}

export interface Project {
  title: string;
  owner: string;
  oneliner: string;
  description: string;
  has_write_access: boolean;
  repo_url: string;
  server_size: [string, string];
  sim_count: number;
  status: "live" | "pending" | "updating";
  exp_task_time: number;
  server_cost: string;
  listed: boolean;
  user_count?: number;
  version?: string;
}

export interface MiniSimulation {
  api_url: string;
  creation_date: Date;
  gui_url: string;
  role?: Role;
  is_public: boolean;
  model_pk: number;
  model_version: string;
  notify_on_completion: boolean;
  owner: string;
  project: string;
  readme: string;
  status: "FAIL" | "WORKER_FAILURE" | "PENDING" | "SUCCESS" | "STARTED";
  title: string;
}

export interface InputsDetail {
  adjustment: { [msect: string]: { [paramName: string]: Array<ValueObject> } };
  api_url: string;
  client: string;
  custom_adjustment: any;
  errors_warnings: { [msect: string]: { errors: { [paramName: string]: Array<string> } } };
  gui_url: string;
  job_id: string;
  meta_parameters: { [paramName: string]: Array<ValueObject> | ValueObject["value"] };
  parent_model_pk: number;
  sim: MiniSimulation;
  status: "FAIL" | "WORKER_FAILURE" | "PENDING" | "SUCCESS" | "STARTED";
  role?: Role;
  traceback: string;
}

export interface Inputs {
  model_parameters: { [msect: string]: ParamToolsConfig };
  meta_parameters: ParamToolsConfig;
  label_to_extend?: string;
  extend?: boolean;
  detail?: InputsDetail;
}

export interface Simulation<T> {
  api_url: string;
  authors: string[];
  creation_date: Date;
  eta: number;
  exp_comp_datetime: Date;
  gui_url: string;
  is_public: boolean;
  role?: boolean;
  model_pk: number;
  model_version: string;
  notify_on_completion: boolean;
  original_eta: number;
  outputs: T;
  outputs_version: string;
  owner: string;
  parent_sims: Array<MiniSimulation>;
  pending_permissions: Array<{
    grant_url: string;
    profile: string;
    permission_name: "add_author";
    is_expired: boolean;
  }>;
  access?: Array<{ username: string; is_owner: boolean; role: Role }>;
  project: Project;
  readme: Node[];
  run_time: number;
  status: "FAIL" | "WORKER_FAILURE" | "PENDING" | "SUCCESS" | "STARTED";
  title: string;
  traceback: string;
}
