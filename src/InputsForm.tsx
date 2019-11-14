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
import { APIData, AccessStatus, Sects, InitialValues } from "./types";

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
  initialValues?: InitialValues,
  sects?: Sects,
  model_parameters?: APIData["model_parameters"],
  meta_parameters?: APIData["meta_parameters"],
  schema?: yup.Schema<any>,
  extend?: boolean,
  unknownParams?: Array<string>,
  creationDate?: Date,
  modelVersion?: string,
  detailAPIURL?: string,
  editInputsUrl?: string,
  initialServerErrors?: { [msect: string]: { errors: { [paramName: string]: any } } },
  accessStatus?: AccessStatus,
  resetting?: boolean,
  error?: any,
  timer?: number,
}>

interface InputsFormProps {
  fetchInitialValues: () => Promise<any>;
  resetInitialValues: (metaParameters: { [metaParam: string]: any }) => any,
  doSubmit: (data: FormData) => Promise<any>
}

export default class InputsForm extends React.Component<InputsFormProps, InputsFormState> {
  constructor(props) {
    super(props);
    this.state = {
      resetting: false,
      error: null,
      model_parameters: null,
      initialValues: null,
    }
    this.resetInitialValues = this.resetInitialValues.bind(this);
    this.poll = this.poll.bind(this);
    this.killTimer = this.killTimer.bind(this);
  }

  componentDidMount() {
    if (this.props.fetchInitialValues) {
      this.props
        .fetchInitialValues()
        .then(data => {
          const [
            initialValues,
            sects,
            model_parameters,
            meta_parameters,
            schema,
            unknownParams
          ] = convertToFormik(data);
          let hasSimData = !!data.detail && !!data.detail.sim;
          this.setState({
            initialValues: initialValues,
            sects: sects,
            model_parameters: model_parameters,
            meta_parameters: meta_parameters,
            schema: schema,
            extend: "extend" in data ? data.extend : false,
            unknownParams: unknownParams,
            creationDate: hasSimData ? data.detail.sim.creation_date : null,
            modelVersion: hasSimData ? data.detail.sim.model_version : null,
            detailAPIURL: !!data.detail ? data.detail.api_url : null,
            editInputsUrl: !!data.detail ? data.detail.edit_inputs_url : null,
            initialServerErrors:
              !!data.detail && hasServerErrors(data.detail.errors_warnings)
                ? data.detail.errors_warnings
                : null,
            accessStatus: data.accessStatus
          });
        })
        .catch(err => {
          this.setState({ error: err });
        });
    }
  }

  resetInitialValues(metaParameters) {
    this.setState({ resetting: true });
    this.props
      .resetInitialValues({
        meta_parameters: tbLabelSchema.cast(metaParameters)
      })
      .then(data => {
        const [
          initialValues,
          sects,
          model_parameters,
          meta_parameters,
          schema,
          unknownParams
        ] = convertToFormik(data);
        this.setState({
          initialValues: initialValues,
          sects: sects,
          model_parameters: model_parameters,
          meta_parameters: meta_parameters,
          schema: schema,
          extend: "extend" in data ? data.extend : false,
          resetting: false,
          unknownParams: unknownParams
        });
      })
      .catch(err => {
        this.setState({ error: err });
      });
  }

  poll(actions, respData) {
    let timer = setInterval(() => {
      axios
        .get(respData.api_url)
        .then(response => {
          // be careful with race condidition where status is SUCCESS but
          // sim has not yet been submitted and saved!
          if (
            response.data.status === "SUCCESS" &&
            response.data.sim !== null
          ) {
            actions.setSubmitting(false);
            actions.setStatus({
              status: response.data.status,
              simUrl: response.data.sim.gui_url
            });
            this.killTimer();
            window.location.href = response.data.sim.gui_url;
          } else if (response.data.status === "INVALID") {
            actions.setSubmitting(false);
            actions.setStatus({
              status: response.data.status,
              serverErrors: response.data.errors_warnings,
              editInputsUrl: response.data.edit_inputs_url
            });
            window.scroll(0, 0);
            this.killTimer();
          }
        })
        .catch(error => {
          console.log("polling error:");
          console.log(error);
          this.killTimer();
          actions.setSubmitting(false);
          // request likely cancelled because timer was killed.
          if (error.message && error.message != "Request aborted") {
            this.setState({ error: error });
          }
        });
    }, 500);
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
    if (this.state.error !== null) {
      throw this.state.error;
    }
    if (
      !this.state.model_parameters ||
      !this.state.initialValues ||
      this.state.resetting
    ) {
      return <LoadingElement />;
    }
    console.log("rendering");

    let meta_parameters = this.state.meta_parameters;
    let model_parameters = this.state.model_parameters;
    let initialValues = this.state.initialValues;
    let schema = this.state.schema;
    let sects = this.state.sects;
    let extend = this.state.extend;
    let hasUnknownParams = this.state.unknownParams.length > 0;
    let unknownParamsErrors: { [sect: string]: { errors: any } } = { "Unknown Parameters": { errors: {} } };
    if (hasUnknownParams) {
      for (const param of this.state.unknownParams) {
        unknownParamsErrors["Unknown Parameters"].errors[param] =
          "This parameter is no longer used.";
      }
    }
    let initialStatus;
    if (this.state.initialServerErrors) {
      initialStatus = {
        serverErrors: this.state.initialServerErrors,
        status: "INVALID",
        editInputsUrl: this.state.editInputsUrl
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
            this.props
              .doSubmit(formdata)
              .then(response => {
                console.log("success");
                console.log(response.data.hashid);
                // update url so that user can come back to inputs later on
                // model errors or some type of unforeseen error in Compute Studio.
                history.pushState(null, null, response.data.edit_inputs_url);
                actions.setStatus({
                  status: "PENDING",
                  inputs_hashid: response.data.hashid,
                  api_url: response.data.api_url,
                  editInputsUrl: response.data.edit_inputs_url
                });
                // set submitting as false in poll func.
                this.poll(actions, response.data);
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
          render={({
            handleSubmit,
            handleChange,
            handleBlur,
            status,
            isSubmitting,
            errors,
            values,
            setFieldValue,
            touched
          }) => (
              <Form>
                {isSubmitting ? <ValidatingModal /> : <div />}
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
                        />
                      </li>
                      <li>
                        <SectionHeaderList sects={sects} />
                      </li>
                      <li>
                        <RunModal
                          handleSubmit={handleSubmit}
                          accessStatus={this.state.accessStatus}
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
                              the simulation can be submitted. You may re-visit this
                          page a later time by entering the following link:{" "}
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
                              `${this.state.creationDate} with version ${this.state.modelVersion}. You may view the full simulation detail `}
                            <a href={this.state.detailAPIURL}>here.</a>
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
                    {Object.entries(sects).map(function (msect_item, ix) {
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
                        />
                      );
                    })}
                  </div>
                </div>
              </Form>
            )}
        />
      </div>
    );
  }
}
