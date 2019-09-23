var path = require("path");
var webpack = require("webpack");
const BundleAnalyzerPlugin = require("webpack-bundle-analyzer")
  .BundleAnalyzerPlugin;

module.exports = [
  {
    devtool: "source-map",
    entry: "./src/publish.tsx",
    output: {
      filename: "publish.js",
      path: path.resolve(__dirname, "static/js")
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
        },
        {
          enforce: "pre",
          test: /\.js$/,
          loader: "source-map-loader"
        }
      ]
    },
    // plugins: [new BundleAnalyzerPlugin({ analyzerPort: 8001 })],
    resolve: {
      extensions: [".ts", ".tsx", ".js"]
    }
  },
  {
    devtool: "source-map",
    entry: "./src/sim.tsx",
    output: {
      filename: "sim.js",
      path: path.resolve(__dirname, "static/js")
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
        },
        {
          enforce: "pre",
          test: /\.js$/,
          loader: "source-map-loader"
        }
      ]
    },
    // plugins: [new BundleAnalyzerPlugin({ analyzerPort: 8002 })],
    resolve: {
      extensions: [".ts", ".tsx", ".js"]
    }
  }
];
