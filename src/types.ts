import { Interface } from "readline";
import { string } from "prop-types";

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

export interface APIDetail {
  adjustment: { [msect: string]: { [paramName: string]: Array<ValueObject> } };
  meta_parameters: { [paramName: string]: Array<ValueObject> };
}

export interface AccessStatus {
  user_status: "inactive" | "customer" | "profile" | "anon";
  api_url: "string";
  is_sponsored?: boolean;
  can_run?: boolean;
  server_cost?: number;
  exp_cost?: number;
  exp_time?: number;
}

export interface APIData {
  model_parameters: { [msect: string]: ParamToolsConfig };
  meta_parameters: ParamToolsConfig;
  label_to_extend?: string;
  extend?: boolean;
  detail: APIDetail;
  accessStatus?: AccessStatus;
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
  data: { target_id: string; root_id: string, doc: string };
}

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

export interface Project {
  title: string;
  oneliner: string;
  description: string;
  repo_url: string;
  server_size: [string, string];
  exp_task_time: number;
  server_cost: string;
  listed: boolean;
}

export interface SimAPIData<T> {
  traceback?: string;
  creation_date: Date;
  api_url: string;
  gui_url: string;
  eta: number;
  original_eta: number;
  model_pk: number;
  status: "FAIL" | "WORKER_FAILURE" | "PENDING" | "SUCCESS";
  model_version: string;
  run_time: 322;
  exp_comp_datetime: Date;
  owner: number;
  project: Project;
  outputs: T;
}
