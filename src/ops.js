export function parseFromOps(value, extendLabel = "year") {
  if (value.value[0] === "<") {
    value.value.shift();
    value[extendLabel] = value[extendLabel] - 1;
  }
  let valueObjects = [];
  for (let i = 0; i < value.value.length; i++) {
    if (value.value[i] === "*") {
      continue;
    } else {
      let newVo = {};
      Object.assign(newVo, value);
      newVo.value = value.value[i];
      newVo[extendLabel] = value[extendLabel] + i;
      valueObjects.push(newVo);
    }
  }
  return valueObjects;
}

// some tests:
// console.log(
//   parseFromOps({
//     value: ["Hello", "*", "*", "world"],
//     year: 2019,
//     mars: "single"
//   })
// );

// console.log(
//   parseFromOps({
//     value: ["<", "Hello", "*", "*", "world"],
//     year: 2019,
//     mars: "single"
//   })
// );
