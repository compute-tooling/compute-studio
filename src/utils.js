"use strict";

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
