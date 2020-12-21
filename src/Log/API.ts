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

  buildQuery(params: {
    ordering?: ("project__owner" | "project__title" | "creation_date")[];
    title?: string;
    title__notlike?: string;
  }): { [q: string]: any } {
    const query: { [q: string]: any } = {};
    if (params.ordering && params.ordering.length > 0) {
      query.ordering = params.ordering.join(",");
    }
    if (params.title) {
      query.title = params.title;
    }
    if (params.title__notlike) {
      query.title__notlike = params.title__notlike;
    }
    return query;
  }

  querySims(params: {
    ordering?: ("project__owner" | "project__title" | "creation_date")[];
    title?: string;
    title__notlike?: string;
  }): Promise<{
    count: number;
    next: string;
    previous: string;
    results: Array<MiniSimulation>;
  }> {
    const query = this.buildQuery(params);
    if (this.username) {
      return axios
        .get(`/api/v1/sims/${this.username}`, {
          params: query,
        })
        .then(resp => resp.data);
    } else {
      return axios
        .get("/api/v1/sims", {
          params: query,
        })
        .then(resp => resp.data);
    }
  }

  updateLogOrder(params: {
    ordering?: ("project__owner" | "project__title" | "creation_date")[];
    title?: string;
    title__notlike?: string;
  }): Promise<{
    count: number;
    next: string;
    previous: string;
    results: Array<MiniSimulation>;
  }> {
    const query = this.buildQuery(params);
    return axios.get(`/api/v1/log`, { params: query }).then(resp => resp.data);
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
