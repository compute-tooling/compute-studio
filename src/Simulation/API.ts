import axios from "axios";

import {
  Simulation,
  Outputs,
  RemoteOutputs,
  Inputs,
  AccessStatus,
  InputsDetail,
  MiniSimulation,
  Role,
} from "../types";

export default class API {
  owner: string;
  title: string;
  modelpk: string;

  constructor(owner: string, title: string, modelpk?: string) {
    this.owner = owner;
    this.title = title;
    this.modelpk = modelpk;
  }

  getOutputs(): Promise<Simulation<Outputs>> {
    return axios.get(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/`).then(resp => {
      let data: Simulation<Outputs> = resp.data;
      return data;
    });
  }

  getRemoteOutputs(): Promise<Simulation<RemoteOutputs>> {
    return axios.get(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/remote/`).then(resp => {
      let data: Simulation<RemoteOutputs> = resp.data;
      return data;
    });
  }

  putDescription(data: FormData): Promise<MiniSimulation> {
    return axios.put(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/`, data).then(resp => {
      let data: MiniSimulation = resp.data;
      return data;
    });
  }

  async getInputsDetail(): Promise<InputsDetail> {
    if (!this.modelpk) return;
    const resp = await axios.get(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/edit/`);
    return resp.data;
  }

  async getInputs(meta_parameters?: InputsDetail["meta_parameters"]): Promise<Inputs> {
    let resp;
    if (!!meta_parameters) {
      resp = await axios.post(`/${this.owner}/${this.title}/api/v1/inputs/`, meta_parameters);
    } else {
      resp = await axios.get(`/${this.owner}/${this.title}/api/v1/inputs/`);
    }
    if (resp.status === 202) {
      return new Promise(resolve => {
        setTimeout(async () => resolve(await this.getInputs(meta_parameters)), 2000);
      });
    } else {
      return resp.data;
    }
  }

  async resetInitialValues(metaParameters: { [metaParam: string]: any }): Promise<Inputs> {
    let resp;
    if (!!metaParameters) {
      resp = await axios.post(`/${this.owner}/${this.title}/api/v1/inputs/`, metaParameters);
    } else {
      resp = await axios.get(`/${this.owner}/${this.title}/api/v1/inputs/`);
    }
    if (resp.status === 202) {
      return new Promise(resolve => {
        setTimeout(async () => resolve(await this.getInputs(metaParameters)), 2000);
      });
    } else {
      return resp.data;
    }
  }

  getAccessStatus(): Promise<AccessStatus> {
    return axios.get(`/users/status/${this.owner}/${this.title}/`).then(resp => resp.data);
  }

  postAdjustment(url: string, data: FormData): Promise<InputsDetail> {
    return axios.post(url, data).then(function (response) {
      return response.data;
    });
  }

  forkSimulation(): Promise<MiniSimulation> {
    return axios
      .post(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/fork/`)
      .then(response => response.data);
  }

  createNewSimulation(): Promise<{ inputs: InputsDetail; sim: Simulation<RemoteOutputs> }> {
    return axios.post(`/${this.owner}/${this.title}/api/v1/new/`).then(response => response.data);
  }

  queryUsers(username: string): Promise<Array<{ username: string }>> {
    return axios.get(`/users/autocomplete?username=${username}`).then(resp => resp.data);
  }

  addAuthors(data: { authors: Array<{ username: string; msg?: string }> }): Promise<{}> {
    return axios
      .put(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/authors/`, data)
      .then(response => response.data);
  }

  deleteAuthor(author: string): Promise<{}> {
    return axios.delete(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/authors/${author}/`);
  }

  putAccess(data: Array<{ username: string; role: Role; msg?: string }>): Promise<{}> {
    return axios
      .put(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/access/`, data)
      .then(() => ({}));
  }
}
