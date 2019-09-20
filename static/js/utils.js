"use strict";
import { isEmpty } from "lodash/lang";
export function makeID(title) {
    return title.split(" ").join("-");
}
export function valForForm(val) {
    if (typeof val === "boolean") {
        return val ? "True" : "False";
    }
    else {
        return val;
    }
}
export function hasServerErrors(errorsWarnings) {
    for (var _i = 0, _a = Object.entries(errorsWarnings); _i < _a.length; _i++) {
        var _b = _a[_i], msect = _b[0], ew = _b[1];
        if (!isEmpty(ew.errors)) {
            return true;
        }
    }
    return false;
}
//# sourceMappingURL=utils.js.map