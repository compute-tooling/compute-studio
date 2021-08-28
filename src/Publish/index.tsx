"use strict";

import * as ReactDOM from "react-dom";
import * as React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import axios from "axios";
import { ProjectDetail, NewProject, BuildHistory, BuildPage } from "./pages/";
axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const domContainer = document.querySelector("#publish-container");

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route exact path="/publish/" component={NewProject} />
      <Route exact path="/new/" component={NewProject} />
      <Route
        path="/:username/:app_name/settings/about/"
        render={routeProps => <ProjectDetail edit={true} section="about" {...routeProps} />}
      />
      <Route
        path="/:username/:app_name/settings/configure/"
        render={routeProps => <ProjectDetail edit={true} section="configure" {...routeProps} />}
      />
      <Route
        path="/:username/:app_name/settings/environment/"
        render={routeProps => <ProjectDetail edit={true} section="environment" {...routeProps} />}
      />
      <Route
        path="/:username/:app_name/settings/access/"
        render={routeProps => <ProjectDetail edit={true} section="access" {...routeProps} />}
      />
      <Route
        path="/:username/:app_name/settings/"
        render={routeProps => <ProjectDetail edit={true} section="about" {...routeProps} />}
      />
      <Route
        path="/:username/:app_name/builds/new/"
        render={routeProps => <BuildPage {...routeProps} />}
      />
      <Route
        path="/:username/:app_name/builds/:build_id/"
        render={routeProps => <BuildPage {...routeProps} />}
      />
      <Route
        path="/:username/:app_name/builds/"
        render={routeProps => <BuildHistory {...routeProps} />}
      />
      <Route
        path="/:username/:app_name/"
        render={routeProps => <ProjectDetail edit={false} {...routeProps} />}
      />
    </Switch>
  </BrowserRouter>,
  domContainer
);
