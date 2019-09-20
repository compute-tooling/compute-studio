var path = require("path");
var webpack = require("webpack");

module.exports = [
  {
    context: __dirname,
    entry: "./src/publish.tsx",
    output: {
      path: path.resolve("./static/js/"),
      filename: "publish.js"
    },
    resolve: {
      extensions: [".ts", ".tsx", ".js", ".tsx"]
    },
    module: {
      rules: [
        { test: /\.(t|j)sx?$/, use: { loader: "awesome-typescript-loader" } },
        { enforce: "pre", test: /\.js$/, loader: "source-map-loader" },
        { test: /\.(css|scss)$/, use: ["style-loader", "css-loader"] }
      ]
    },
    // externals: {
    //   react: "React",
    //   "react-dom": "ReactDOM"
    // },
    devtool: "source-map"
  },
  {
    context: __dirname,
    entry: "./src/sim.tsx",
    output: {
      path: path.resolve("./static/js/"),
      filename: "sim.js"
    },
    resolve: {
      extensions: [".ts", ".tsx", ".js", ".tsx"]
    },
    module: {
      rules: [
        { test: /\.(t|j)sx?$/, use: { loader: "awesome-typescript-loader" } },
        { enforce: "pre", test: /\.js$/, loader: "source-map-loader" },
        { test: /\.(css|scss)$/, use: ["style-loader", "css-loader"] }
      ]
    },
    // externals: {
    //   react: "React",
    //   "react-dom": "ReactDOM"
    // },
    devtool: "source-map"
  }
];
