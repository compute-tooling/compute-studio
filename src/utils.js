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

// https://github.com/facebook/react/blob/v16.8.6/packages/shared/shallowEqual.js
export function shallowEqual(a, b) {
  for (var key in a) {
    if (a[key] !== b[key]) {
      return false;
    }
  }
  return true;
}
