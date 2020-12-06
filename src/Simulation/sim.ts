import { RolePerms } from "../roles";
import { MiniSimulation, Simulation } from "../types";

export const Utils = {
  submitWillCreateNewSim: (sim: Simulation<any> | MiniSimulation) => {
    return !(sim && RolePerms.hasWriteAccess(sim) && sim.status === "STARTED");
  },
};
