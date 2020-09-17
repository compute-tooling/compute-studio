import { Simulation, MiniSimulation, InputsDetail } from "./types";

export const RolePerms = {
  hasAdminAccess(obj?: Simulation<any> | MiniSimulation | InputsDetail) {
    return obj?.role == "admin";
  },

  hasWriteAccess(obj?: Simulation<any> | MiniSimulation | InputsDetail) {
    return obj?.role == "write" || RolePerms.hasAdminAccess(obj);
  },

  hasReadAccess(obj?: Simulation<any> | MiniSimulation | InputsDetail) {
    return obj?.role == "read" || RolePerms.hasWriteAccess(obj);
  },
};
