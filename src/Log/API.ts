import axios from "axios";
import { MiniSimulation, Project, AccessStatus } from "../types";

export default class API {
  username?: string;

  constructor(username?: string) {
    this.username = username;
  }

  getAccessStatus(): Promise<AccessStatus> {
    return axios.get(`/users/status/`).then(resp => resp.data);
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

  initFeed(): Promise<{
    count: number;
    next: string;
    previous: string;
    results: Array<MiniSimulation>;
  }> {
    return axios.get("/api/v1/log").then(resp => resp.data);
  }

  next(
    nextUrl
  ): Promise<{
    count: number;
    next: string;
    previous: string;
    results: Array<MiniSimulation>;
  }> {
    return axios.get(nextUrl).then(resp => resp.data);
  }

  updateSimsOrder(
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

  updateLogOrder(
    ordering: ("project__owner" | "project__title" | "creation_date")[]
  ): Promise<{
    count: number;
    next: string;
    previous: string;
    results: Array<MiniSimulation>;
  }> {
    return axios
      .get(`/api/v1/feed`, { params: { ordering: ordering.join(",") } })
      .then(resp => resp.data);
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
