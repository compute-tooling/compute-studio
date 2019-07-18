"use strict";

import React from "react";
import ReactLoading from "react-loading";

import { makeID } from "./utils";

export const ParamElement = (...props) => {
  var param_data = props[0].param_data;
  var tooltip = <div />;
  if (param_data.description) {
    tooltip = (
      <label
        className="input-tooltip"
        data-toggle="tooltip"
        data-placement="top"
        title={param_data.description}
      >
        {" "}
        <i className="fas fa-info-circle" />
      </label>
    );
  }
  return (
    // <div className="container" style={{ padding: "left 0" }}>
    <div className="row has-statuses col-xs-12">
      <label>
        {param_data.title} {tooltip}
      </label>
    </div>
    // </div>
  );
};

export const SectionHeader = (...props) => {
  let title = props[0].title;
  let size = props[0].size;
  let label = props[0].label;
  return (
    <h1 style={{ fontSize: { size } }}>
      {title}
      <div className="float-right">
        <button
          className="btn collapse-button"
          type="button"
          data-toggle="collapse"
          data-target={`#${makeID(title)}-collapse-${label}`}
          aria-expanded="false"
          aria-controls={`${makeID(title)}-collapse-${label}`}
          style={{ marginLeft: "20px" }}
        >
          <i className="far fa-minus-square" style={{ size: "5px" }} />
        </button>
      </div>
    </h1>
  );
};

export const LoadingElement = () => {
  return (
    <div className="row">
      <div className="col-4">
        <ul className="list-unstyled components sticky-top scroll-y">
          <li>
            <div className="card card-body card-outer">
              <div className="d-flex justify-content-center">
                <ReactLoading type="spokes" color="#2b2c2d" />
              </div>
            </div>
          </li>
        </ul>
      </div>
      <div className="col-8">
        <div className="card card-body card-outer">
          <div className="d-flex justify-content-center">
            <ReactLoading type="spokes" color="#2b2c2d" />
          </div>
        </div>
      </div>
    </div>
  );
};