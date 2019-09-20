var path = require("path");
var webpack = require("webpack");

module.exports = [
  {
    devtool: "inline-source-map",
    entry: "./src/publish.tsx",
    output: {
      filename: "publish.js",
      path: path.resolve(__dirname, "dist")
    },
    module: {
      rules: [
        {
          test: /\.tsx?$/,
          loader: "ts-loader"
        },
        {
          test: /\.css$/i,
          use: ["style-loader", "css-loader"]
        }
      ]
    },
    resolve: {
      extensions: [".ts", ".tsx", ".js"]
    }
  },
  {
    devtool: "inline-source-map",
    entry: "./src/sim.tsx",
    output: {
      filename: "sim.js",
      path: path.resolve(__dirname, "dist")
    },
    module: {
      rules: [
        {
          test: /\.tsx?$/,
          loader: "ts-loader"
        },
        {
          test: /\.css$/i,
          use: ["style-loader", "css-loader"]
        }
      ]
    },
    resolve: {
      extensions: [".ts", ".tsx", ".js"]
    }
  }
];
