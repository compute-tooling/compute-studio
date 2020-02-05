import axios from "axios";

export default class API {
  username?: string;

  constructor(username?: string) {
    this.username = username;
  }

  getSimulations(limit?: number) {
    if (this.username) {
      return axios
        .get(`/api/v1/sims/${this.username}${limit ? `?limit=${limit}` : ""}`)
        .then(resp => resp.data);
    } else {
      return axios.get(`/api/v1/sims${limit ? `?limit=${limit}` : ""}`).then(resp => resp.data);
    }
  }
}
