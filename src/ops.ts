import { ValueObject, FormValueObject } from "./types";

export function parseFromOps(value: FormValueObject, extendLabel: string = "year"): Array<ValueObject> {
  if (value.value[0] === "<") {
    value.value.shift();
    value[extendLabel] = value[extendLabel] - 1;
  }
  let valueObjects = [];
  for (let i = 0; i < value.value.length; i++) {
    if (value.value[i] === "*") {
      continue;
    } else {
      let newVo: ValueObject = {value: ""};
      Object.assign(newVo, value);
      newVo.value = value.value[i]
      newVo[extendLabel] = value[extendLabel] + i;
      valueObjects.push(newVo);
    }
  }
  return valueObjects;
}

export function parseToOps(valueObjects: Array<ValueObject>, metaParameters: {[key: string]: any}, extendLabel: string = "year"): Array<any> {
  if (!valueObjects.length) return [];
  let res = [];
  for (let i = 0; i < valueObjects.length; i++) {
    if (
      i == 0 &&
      valueObjects[i][extendLabel] === metaParameters[extendLabel] - 1
    ) {
      res.push("<", valueObjects[i].value);
      continue;
    } else if (i == 0) {
      res.push(valueObjects[i].value);
    } else {
      let gap = valueObjects[i][extendLabel] - valueObjects[i - 1][extendLabel];
      for (let j = 0; j < gap - 1; j++) {
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
