import axios from "axios";
import { AccessStatus, Build, Project } from "../types";

export default class API {
  owner?: string;
  title?: string;
  constructor(owner, title) {
    this.owner = owner;
    this.title = title;
  }
  async getAccessStatus(): Promise<AccessStatus> {
    if (this.owner && this.title) {
      return (await axios.get(`/users/status/${this.owner}/${this.title}/`)).data;
    } else {
      return (await axios.get(`/users/status/`)).data;
    }
  }

  async getProject(): Promise<Project> {
    return (await axios.get(`/projects/api/v1/${this.owner}/${this.title}/`)).data;
  }

  async updateProject(data): Promise<Project> {
    return (await axios.put(`/projects/api/v1/${this.owner}/${this.title}/`, data)).data;
  }

  async createProject(data): Promise<Project> {
    return (await axios.post(`/projects/api/v1/`, data)).data;
  }

  async createBuild(data): Promise<Build> {
    return (await axios.post(`/projects/api/v1/${this.owner}/${this.title}/builds/`, data)).data;
  }

  async getBuild(id: number, force_reload?: boolean): Promise<Build> {
    return (
      await axios.get(`/projects/api/v1/builds/${id}/`, {
        params: {
          force_reload: force_reload,
        },
      })
    ).data;
  }

  async promoteTag(tag: string, version?: string): Promise<Build> {
    return (
      await axios.post(`/projects/api/v1/${this.owner}/${this.title}/tags/`, {
        latest_tag: tag,
        version: version,
        staging_tag: null,
      })
    ).data;
  }

  async listBuilds(): Promise<{
    count: number;
    next?: string;
    previous: string;
    results: Build[];
  }> {
    console.log("URL", `projects/api/v1/${this.owner}/${this.title}/builds/`);
    return (await axios.get(`/projects/api/v1/${this.owner}/${this.title}/builds/`)).data;
  }

  async save(data): Promise<Project> {
    if (this.owner && this.title) {
      return await this.updateProject(data);
    } else {
      return await this.createProject(data);
    }
  }
}
