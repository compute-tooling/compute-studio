"use strict";

import * as yup from "yup";
import React from "react";
import { Formik, Form } from "formik";

import {
  MetaParameters,
  MajorSection,
  LoadingElement,
  Preview,
  SectionHeaderList
} from "./components";
import { ValidatingModal, RunModal, AuthModal } from "./modal";
import { formikToJSON, convertToFormik } from "./ParamTools";

// need to require schema in model_parameters!
const tbLabelSchema = yup.object().shape({
  year: yup.number(),
  MARS: yup.string(),
  idedtype: yup.string(),
  EIC: yup.string(),
  data_source: yup.string()
});

class InputsForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      initialValues: this.props.initialValues,
      sects: false,
      model_parameters: false,
      resetting: false
    };
    this.resetInitialValues = this.resetInitialValues.bind(this);
  }

  componentDidMount() {
    if (this.props.fetchInitialValues) {
      this.props.fetchInitialValues().then(data => {
        const [
          initialValues,
          sects,
          model_parameters,
          meta_parameters,
          schema
        ] = convertToFormik(data);
        this.setState({
          initialValues: initialValues,
          sects: sects,
          model_parameters: model_parameters,
          meta_parameters: meta_parameters,
          schema: schema,
          extend: "extend" in data ? data.extend : false
        });
      });
    }
  }

  resetInitialValues(metaParameters) {
    this.setState({ resetting: true });
    this.props
      .resetInitialValues({ meta_parameters: metaParameters })
      .then(data => {
        const [
          initialValues,
          sects,
          model_parameters,
          meta_parameters,
          schema
        ] = convertToFormik(data);
        this.setState({
          initialValues: initialValues,
          sects: sects,
          model_parameters: model_parameters,
          meta_parameters: meta_parameters,
          schema: schema,
          extend: "extend" in data ? data.extend : false,
          resetting: false
        });
      });
  }

  render() {
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
    return (
      <div>
        <Formik
          initialValues={initialValues}
          validationSchema={schema}
          validateOnChange={false}
          validateOnBlur={true}
          enableReinitialize={true}
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
                actions.setSubmitting(false);
                console.log(response.data.pk);
                actions.setStatus({
                  status: "PENDING",
                  inputs_pk: response.data.pk,
                  api_url: response.data.api_url
                });
              })
              .catch(error => {
                console.log("error", error);
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
            errors,
            values,
            setFieldValue,
            touched
          }) => (
            <Form>
              {status && status.status === "PENDING" ? (
                <ValidatingModal inputs_url={status.api_url} />
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
                        // handleSubmit={handleSubmit}
                        // handleChange={handleChange}
                        // status={status}
                        // errors={errors}
                        values={values.meta_parameters}
                        touched={touched}
                        resetInitialValues={this.resetInitialValues}
                      />
                    </li>
                    <li>
                      <SectionHeaderList sects={sects} />
                    </li>
                    <li>
                      <RunModal handleSubmit={handleSubmit} />
                    </li>
                  </ul>
                </div>
                <div className="col-sm-8">
                  <Preview
                    values={values}
                    schema={schema}
                    tbLabelSchema={tbLabelSchema}
                    transformfunc={formikToJSON}
                    extend={extend}
                  />
                  {Object.entries(sects).map(function(msect_item, ix) {
                    // msect --> section_1: dict(dict) --> section_2: dict(dict)
                    let msect = msect_item[0];
                    let section_1_dict = msect_item[1];
                    return (
                      <MajorSection
                        key={`${msect}-component`}
                        msect={msect}
                        section_1_dict={section_1_dict}
                        model_parameters={model_parameters}
                        handleSubmit={handleSubmit}
                        handleChange={handleChange}
                        status={status}
                        errors={errors}
                        values={values}
                        setFieldValue={setFieldValue}
                        handleBlur={handleBlur}
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

export { InputsForm };
