"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import axios from "axios";
import { NewProject } from "./pages/";
axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const domContainer = document.querySelector("#publish-container");

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route exact path="/publish/" component={NewProject} />
      <Route exact path="/new/" component={NewProject} />
    </Switch>
  </BrowserRouter>,
  domContainer
);
