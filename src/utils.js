"use strict";

import { isEmpty } from "lodash/lang";

export function makeID(title) {
  return title.split(" ").join("-");
}

export function valForForm(val) {
  if (typeof val === "boolean") {
    return val ? "True" : "False";
  } else {
    return val;
  }
}


export function hasServerErrors(errorsWarnings) {
  for (const [msect, ew] of Object.entries(errorsWarnings)) {
    if (!isEmpty(ew.errors)) {
      return true
    }
  }
  return false;
}