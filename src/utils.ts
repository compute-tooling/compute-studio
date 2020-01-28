"use strict";

import { isEmpty } from "lodash/lang";

export function makeID(title: string): string {
  return title.split(" ").join("-");
}

export function valForForm(val) {
  if (typeof val === "boolean") {
    return val ? "True" : "False";
  } else {
    return val;
  }
}

export function hasServerErrors(errorsWarnings: {
  [msect: string]: { errors: { [paramName: string]: any } };
}): boolean {
  if (errorsWarnings) {
    for (const [msect, ew] of Object.entries(errorsWarnings)) {
      if (!isEmpty(ew.errors)) {
        return true;
      }
    }
  }
  return false;
}

export function imgDims(url: string): [number, number] {
  let img = new Image();
  img.src = url;
  let [height, width] = [img.height, img.width];
  let factor = 1;
  if (height > width) {
    factor = height / 600;
  } else {
    factor = width / 600;
  }
  height = Math.floor(height / factor);
  width = Math.floor(width / factor);
  return [width, height];
}

// https://github.com/segmentio/is-url
let protocolAndDomainRE = /^(?:\w+:)?\/\/(\S+)$/;

let localhostDomainRE = /^localhost[\:?\d]*(?:[^\:?\d]\S*)?$/;
let nonLocalhostDomainRE = /^[^\s\.]+\.\S{2,}$/;

export function isUrl(string: string): boolean {
  if (typeof string !== "string") {
    return false;
  }

  let match = string.match(protocolAndDomainRE);
  if (!match) {
    return false;
  }

  let everythingAfterProtocol = match[1];
  if (!everythingAfterProtocol) {
    return false;
  }

  if (
    localhostDomainRE.test(everythingAfterProtocol) ||
    nonLocalhostDomainRE.test(everythingAfterProtocol)
  ) {
    return true;
  }

  return false;
}
