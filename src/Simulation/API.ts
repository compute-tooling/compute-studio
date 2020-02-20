import axios from "axios";

import {
  Simulation,
  Outputs,
  RemoteOutputs,
  Inputs,
  AccessStatus,
  InputsDetail,
  MiniSimulation
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

  putDescription(data: FormData): Promise<Simulation<RemoteOutputs>> {
    return axios.put(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/`, data).then(resp => {
      let data: Simulation<RemoteOutputs> = resp.data;
      return data;
    });
  }

  getInputsDetail(): Promise<InputsDetail> {
    if (!this.modelpk) return;
    return axios
      .get(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/edit/`)
      .then(resp => resp.data);
  }

  getInitialValues(): Promise<Inputs> {
    let data: Inputs;
    if (!this.modelpk) {
      return axios.get(`/${this.owner}/${this.title}/api/v1/inputs/`).then(inputsResp => {
        data = inputsResp.data;
        return data;
      });
    } else {
      return axios
        .get(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/edit/`)
        .then(detailResp => {
          return axios
            .post(`/${this.owner}/${this.title}/api/v1/inputs/`, {
              meta_parameters: detailResp.data.meta_parameters
            })
            .then(inputsResp => {
              data = inputsResp.data;
              data["detail"] = detailResp.data;
              return data;
            });
        });
    }
  }

  resetInitialValues(metaParameters: { [metaParam: string]: any }): Promise<Inputs> {
    return axios
      .post(`/${this.owner}/${this.title}/api/v1/inputs/`, metaParameters)
      .then(response => {
        return response.data;
      });
  }

  getAccessStatus(): Promise<AccessStatus> {
    return axios.get(`/users/status/${this.owner}/${this.title}/`).then(resp => resp.data);
  }

  postAdjustment(url: string, data: FormData): Promise<InputsDetail> {
    return axios.post(url, data).then(function(response) {
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

  addAuthors(data: { authors: Array<string> }): Promise<{}> {
    return axios
      .put(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/authors/`, data)
      .then(response => response.data);
  }

  deleteAuthor(author: string): Promise<{}> {
    return axios.delete(`/${this.owner}/${this.title}/api/v1/${this.modelpk}/authors/${author}/`);
  }
}
