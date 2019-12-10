"use strict";

import * as yup from "yup";
import * as React from "react";
import { Formik, Form } from "formik";
import axios from "axios";

import {
  MetaParameters,
  MajorSection,
  LoadingElement,
  Preview,
  SectionHeaderList,
  ErrorCard
} from "./components";
import { ValidatingModal, RunModal, AuthModal } from "./modal";
import { formikToJSON, convertToFormik } from "./ParamTools";
import { hasServerErrors } from "./utils";
import {
  AccessStatus,
  Sects,
  InitialValues,
  MiniSimulation,
  Inputs,
  InputsDetail
} from "./types";
import API from "./API";

// need to require schema in model_parameters!
const tbLabelSchema = yup.object().shape({
  year: yup.number(),
  MARS: yup.string(),
  idedtype: yup.string(),
  EIC: yup.string(),
  data_source: yup.string(),
  use_full_sample: yup.bool()
});

type InputsFormState = Readonly<{
  initialValues?: InitialValues;
  sects?: Sects;
  schema?: yup.Schema<any>;
  extend?: boolean;
  unknownParams?: Array<string>;
  initialServerErrors?: {
    [msect: string]: { errors: { [paramName: string]: any } };
  };
  resetting?: boolean;
  timer?: number;
  error: any;

  // data from api endpoints.
  inputs: Inputs;
  sim?: MiniSimulation;
}>;

interface InputsFormProps {
  api: API;
  readOnly: boolean;
  accessStatus: AccessStatus;
  defaultURL: string;
}

export default class InputsForm extends React.Component<
  InputsFormProps,
  InputsFormState
  > {
  constructor(props) {
    super(props);
    this.state = {
      resetting: false,
      initialValues: null,
      inputs: null,
      error: null
    };
    this.resetInitialValues = this.resetInitialValues.bind(this);
    this.poll = this.poll.bind(this);
    this.killTimer = this.killTimer.bind(this);
  }

  componentDidMount() {
    if (this.props.api) {
      this.props.api
        .getInitialValues()
        .then(data => {
          const [
            initialValues,
            sects,
            inputs,
            schema,
            unknownParams
          ] = convertToFormik(data);
          this.setState({
            initialValues: initialValues,
            sects: sects,
            schema: schema,
            extend: "extend" in inputs ? inputs.extend : false,
            unknownParams: unknownParams,
            initialServerErrors:
              data.detail && hasServerErrors(data.detail.errors_warnings)
                ? data.detail.errors_warnings
                : null,
            inputs: inputs,
            sim: inputs.detail?.sim
          });
          if (inputs.detail?.status === "PENDING") {
            this.poll(
              inputs.detail,
              (data: InputsDetail) => {
                window.location.href = data.api_url;
              },
              (data: InputsDetail) => {
                window.location.href = data.api_url;
              }
            );
          }
        })
        .catch(err => {
          this.setState({ error: err });
        });
    }
  }

  resetInitialValues(metaParameters) {
    this.setState({ resetting: true });
    this.props.api
      .resetInitialValues({
        meta_parameters: tbLabelSchema.cast(metaParameters)
      })
      .then(data => {
        const [
          initialValues,
          sects,
          inputs,
          schema,
          unknownParams
        ] = convertToFormik(data);
        this.setState({
          initialValues: initialValues,
          sects: sects,
          schema: schema,
          extend: "extend" in data ? data.extend : false,
          resetting: false,
          unknownParams: unknownParams,
          inputs: inputs,
          sim: inputs.detail?.sim
        });
      })
      .catch(err => {
        this.setState({ error: err });
      });
  }

  poll(
    respData: InputsDetail,
    onSuccess: (data: InputsDetail) => void,
    onInvalid: (data: InputsDetail) => void
  ) {
    let timer = setInterval(() => {
      axios
        .get(respData.api_url)
        .then(response => {
          // be careful with race condidition where status is SUCCESS but
          // sim has not yet been submitted and saved!
          let data: InputsDetail = response.data;
          if (data.status === "SUCCESS" && data.sim !== null) {
            this.killTimer();
            onSuccess(data);
            window.location.href = response.data.sim.gui_url;
          } else if (response.data.status === "INVALID") {
            this.killTimer();
            onInvalid(data);
            window.scroll(0, 0);
          }
        })
        .catch(error => {
          console.log("polling error:");
          console.log(error);
          this.killTimer();
          // actions.setSubmitting(false); TODO
          // request likely cancelled because timer was killed.
          if (error.message && error.message != "Request aborted") {
            this.setState({ error: error });
          }
        });
    }, 1000);
    // @ts-ignore
    this.setState({ timer: timer });
  }

  killTimer() {
    if (!!this.state.timer) {
      clearInterval(this.state.timer);
      this.setState({ timer: null });
    }
  }

  render() {
    if (
      !this.state.inputs ||
      !this.state.initialValues ||
      this.state.resetting
    ) {
      return <LoadingElement />;
    }
    console.log("rendering");

    let {
      initialValues,
      schema,
      sects,
      extend,
      unknownParams,
      initialServerErrors,
      inputs
    } = this.state;
    let { meta_parameters, model_parameters } = inputs;

    let hasUnknownParams = unknownParams.length > 0;
    let unknownParamsErrors: { [sect: string]: { errors: any } } = {
      "Unknown Parameters": { errors: {} }
    };
    if (hasUnknownParams) {
      for (const param of unknownParams) {
        unknownParamsErrors["Unknown Parameters"].errors[param] =
          "This parameter is no longer used.";
      }
    }
    let initialStatus;
    if (initialServerErrors) {
      initialStatus = {
        serverErrors: initialServerErrors,
        status: "INVALID",
        editInputsUrl: inputs.detail.api_url
      };
    }

    return (
      <div>
        <Formik
          initialValues={initialValues}
          validationSchema={schema}
          validateOnChange={false}
          validateOnBlur={true}
          enableReinitialize={true}
          initialStatus={initialStatus}
          onSubmit={(values, actions) => {
            const [meta_parameters, adjustment] = formikToJSON(
              values,
              this.state.schema,
              tbLabelSchema,
              this.state.extend
            );
            console.log("submitting");
            console.log(adjustment);
            console.log(meta_parameters);

            let formdata = new FormData();
            formdata.append("adjustment", JSON.stringify(adjustment));
            formdata.append("meta_parameters", JSON.stringify(meta_parameters));
            formdata.append("client", "web-beta");
            let url = this.props.defaultURL;
            let sim = this.state.sim;
            // clicked new simulation button
            console.log("sim", sim)
            if (
              sim &&
              this.state.inputs.detail.has_write_access &&
              sim.status === "STARTED"
            ) {
              url = sim.api_url;
            } else if (sim) {
              // sim is completed or user does not have write access
              formdata.append("parent_model_pk", sim.model_pk.toString());
            }
            this.props.api
              .postAdjustment(url, formdata)
              .then(data => {
                console.log("success", data.gui_url);
                if (data.sim.owner !== sim?.owner) {
                  window.location.href = data.gui_url;
                } else {
                  history.pushState(null, null, data.gui_url);
                  actions.setStatus({
                    status: "PENDING",
                    api_url: data.api_url,
                    editInputsUrl: data.gui_url,
                    inputsDetail: data // TODO: necessary
                  });
                  // set submitting as false in poll func.
                  if (data.status === "PENDING") {
                    this.poll(
                      data,
                      (data: InputsDetail) => {
                        actions.setStatus({
                          status: data.status,
                          simUrl: data.sim.gui_url
                        });
                        actions.setSubmitting(false);
                      },
                      (data: InputsDetail) => {
                        actions.setSubmitting(false);
                        actions.setStatus({
                          status: data.status,
                          serverErrors: data.errors_warnings,
                          editInputsUrl: data.gui_url
                        });
                        actions.setSubmitting(false);
                      }
                    );
                  }
                }
              })
              .catch(error => {
                console.log("error", error);
                actions.setSubmitting(false);
                actions.setStatus({ status: null });
                if (error.response.status == 403) {
                  actions.setStatus({
                    auth: "You must be logged in to publish a model."
                  });
                }
              });
          }}
          render={({ handleSubmit, status, isSubmitting, values, touched }) => {
            return (
              <Form>
                {isSubmitting || inputs.detail?.status === "PENDING" ? (
                  <ValidatingModal />
                ) : (
                    <div />
                  )}
                {status && status.auth ? <AuthModal /> : <div />}
                <div className="row">
                  <div className="col-sm-4">
                    <ul className="list-unstyled components sticky-top scroll-y">
                      <li>
                        <MetaParameters
                          meta_parameters={meta_parameters}
                          values={values.meta_parameters}
                          touched={touched}
                          resetInitialValues={this.resetInitialValues}
                          readOnly={this.props.readOnly}
                        />
                      </li>
                      <li>
                        <SectionHeaderList sects={sects} />
                      </li>
                      <li>
                        <RunModal
                          handleSubmit={handleSubmit}
                          accessStatus={this.props.accessStatus}
                        />
                      </li>
                    </ul>
                  </div>
                  <div className="col-sm-8">
                    {status &&
                      status.status === "INVALID" &&
                      status.serverErrors ? (
                        <ErrorCard
                          errorMsg={
                            <p>
                              Some fields have errors. These must be fixed before
                              the simulation can be submitted. You may re-visit
                              this page a later time by entering the following
                            link:{" "}
                              <a href={status.editInputsUrl}>
                                {status.editInputsUrl}
                              </a>
                            </p>
                          }
                          errors={status.serverErrors}
                          model_parameters={model_parameters}
                        />
                      ) : (
                        <div />
                      )}

                    {hasUnknownParams ? (
                      <ErrorCard
                        errorMsg={
                          <p>
                            {"One or more parameters have been renamed or " +
                              "removed since this simulation was run on " +
                              `${this.state.sim.creation_date} with version ${this.state.sim.model_version}. You may view the full simulation detail `}
                            <a href={this.state.sim.api_url}>here.</a>
                          </p>
                        }
                        errors={unknownParamsErrors}
                        model_parameters={{}}
                      />
                    ) : (
                        <div />
                      )}

                    <Preview
                      values={values}
                      schema={schema}
                      tbLabelSchema={tbLabelSchema}
                      transformfunc={formikToJSON}
                      extend={extend}
                    />
                    {Object.entries(sects).map((msect_item, ix) => {
                      // msect --> section_1: dict(dict) --> section_2: dict(dict)
                      let msect = msect_item[0];
                      let section_1_dict = msect_item[1];
                      return (
                        <MajorSection
                          key={msect}
                          msect={msect}
                          section_1_dict={section_1_dict}
                          meta_parameters={meta_parameters}
                          model_parameters={model_parameters}
                          values={values}
                          extend={extend}
                          readOnly={this.props.readOnly}
                        />
                      );
                    })}
                  </div>
                </div>
              </Form>
            );
          }}
        />
      </div>
    );
  }
}
