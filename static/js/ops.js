export function parseFromOps(value, extendLabel) {
    if (extendLabel === void 0) { extendLabel = "year"; }
    if (value.value[0] === "<") {
        value.value.shift();
        value[extendLabel] = value[extendLabel] - 1;
    }
    var valueObjects = [];
    for (var i = 0; i < value.value.length; i++) {
        if (value.value[i] === "*") {
            continue;
        }
        else {
            var newVo = {};
            Object.assign(newVo, value);
            newVo.value = value.value[i];
            newVo[extendLabel] = value[extendLabel] + i;
            valueObjects.push(newVo);
        }
    }
    return valueObjects;
}
export function parseToOps(valueObjects, metaParameters, extendLabel) {
    if (extendLabel === void 0) { extendLabel = "year"; }
    if (!valueObjects.length)
        return [];
    var res = [];
    for (var i = 0; i < valueObjects.length; i++) {
        if (i == 0 &&
            valueObjects[i][extendLabel] === metaParameters[extendLabel] - 1) {
            res.push("<", valueObjects[i].value);
            continue;
        }
        else if (i == 0) {
            res.push(valueObjects[i].value);
        }
        else {
            var gap = valueObjects[i][extendLabel] - valueObjects[i - 1][extendLabel];
            for (var j = 0; j < gap - 1; j++) {
                res.push("*");
            }
            res.push(valueObjects[i].value);
        }
    }
    return res;
}
// some tests:
// let ops = {
//   value: ["Hello", "*", "*", "world"],
//   year: 2019,
//   mars: "single"
// };
// console.log(parseFromOps(ops));
// let revOps = {
//   value: ["<", "Hello", "*", "*", "world"],
//   year: 2019,
//   mars: "single"
// };
// console.log(parseFromOps(revOps));
// console.log(parseToOps(parseFromOps(ops), { year: 2019 }));
// console.log(parseToOps(parseFromOps(revOps), { year: 2019 }));
// let easy = {
//   value: ["Hello", "world"],
//   year: 2019,
//   mars: "single"
// };
// console.log(parseToOps(parseFromOps(easy), { year: 2019 }));
// let easier = {
//   value: ["Hello"],
//   year: 2019,
//   mars: "single"
// };
// console.log(parseToOps(parseFromOps(easier), { year: 2019 }));
// console.log(parseToOps([], { year: 2019 }));
//# sourceMappingURL=ops.js.map