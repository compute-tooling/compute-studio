var path = require("path");
var webpack = require("webpack");

module.exports = {
  context: __dirname,
  entry: "./src",
  output: {
    path: path.resolve("./static/js/"),
    filename: "[name].js"
  },
  module: {
    rules: [
      {
        // this is so that we can compile any React,
        // ES6 and above into normal ES5 syntax
        test: /\.(js|jsx)$/,
        // we do not want anything from node_modules to be compiled
        exclude: /node_modules/,
        use: ["babel-loader"]
      },
      {
        test: /\.(css|scss)$/,
        use: [
          "style-loader", // creates style nodes from JS strings
          "css-loader" // translates CSS into CommonJS
        ]
      }
    ]
  }
};
