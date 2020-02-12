import axios from "axios";
import { MiniSimulation, Project } from "../types";

export default class API {
  username?: string;

  constructor(username?: string) {
    this.username = username;
  }

  initSimulations(): Promise<{
    count: number;
    next: string;
    previous: string;
    results: Array<MiniSimulation>;
  }> {
    if (this.username) {
      return axios.get(`/api/v1/sims/${this.username}`).then(resp => resp.data);
    } else {
      return axios.get("/api/v1/sims").then(resp => resp.data);
    }
  }

  nextSimulations(
    nextUrl
  ): Promise<{
    count: number;
    next: string;
    previous: string;
    results: Array<MiniSimulation>;
  }> {
    return axios.get(nextUrl).then(resp => resp.data);
  }

  updateOrder(
    ordering: ("project__owner" | "project__title" | "creation_date")[]
  ): Promise<{
    count: number;
    next: string;
    previous: string;
    results: Array<MiniSimulation>;
  }> {
    if (this.username) {
      return axios
        .get(`/api/v1/sims/${this.username}`, { params: { ordering: ordering.join(",") } })
        .then(resp => resp.data);
    } else {
      return axios
        .get("/api/v1/sims", { params: { ordering: ordering.join(",") } })
        .then(resp => resp.data);
    }
  }

  getModels(): Promise<{ count: number; next: string; previous: string; results: Array<Project> }> {
    if (this.username) {
      return axios.get(`/api/v1/models/${this.username}`).then(resp => resp.data);
    } else {
      return axios.get(`/api/v1/models`).then(resp => resp.data);
    }
  }

  getRecentModels(): Promise<Array<Project>> {
    return axios.get("/api/v1/models/recent/").then(resp => resp.data.results);
  }
}
