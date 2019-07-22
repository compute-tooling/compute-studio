"use strict";

export function makeID(title) {
  return title.replace(" ", "-");
}

export function valForForm(val) {
  if (typeof val === "boolean") {
    return val ? "True" : "False";
  } else {
    return val;
  }
}
