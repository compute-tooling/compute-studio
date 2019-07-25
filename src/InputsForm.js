"use strict";

import * as yup from "yup";
import React from "react";
import { Formik, Form } from "formik";

import {
  MetaParameters,
  MajorSection,
  LoadingElement,
  SectionHeaderList
} from "./components";
import { ValidatingModal, RunModal } from "./modal";
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
      model_parameters: false
    };
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
          schema: schema
        });
      });
    }
  }

  render() {
    if (!this.state.model_parameters || !this.state.initialValues) {
      return <LoadingElement />;
    }
    console.log("rendering");
    let meta_parameters = this.state.meta_parameters;
    let model_parameters = this.state.model_parameters;
    let initialValues = this.state.initialValues;
    let schema = this.state.schema;
    let sects = this.state.sects;
    return (
      <div>
        <Formik
          initialValues={initialValues}
          validationSchema={schema}
          validateOnChange={false}
          validateOnBlur={true}
          onSubmit={(values, actions) => {
            const [meta_parameters, adjustment] = formikToJSON(
              values,
              this.state.schema,
              tbLabelSchema
            );
            console.log("submitting");
            console.log(adjustment);
            console.log(meta_parameters);
            let formdata = new FormData();
            formdata.append("adjustment", JSON.stringify(adjustment));
            formdata.append("meta_parameters", JSON.stringify(meta_parameters));
            alert(JSON.stringify(adjustment, null, 4));
            // this.props
            //   .doSubmit(formdata)
            //   .then(response => {
            //     console.log("success");
            //     actions.setSubmitting(false);
            //     console.log(response.data.pk);
            //     actions.setStatus({
            //       status: "PENDING",
            //       inputs_pk: response.data.pk,
            //       api_url: response.data.api_url
            //     });
            //   })
            //   .catch(error => {
            //     console.log("error", error);
            //   });
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
              <div className="row">
                <div className="col-4">
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
                <div className="col-8">
                  {/* <div className="card card-outer">
                    <pre>
                      <code>
                        {JSON.stringify(
                          formikToJSON(values, schema, tbLabelSchema),
                          null,
                          4
                        )}
                      </code>
                    </pre>
                  </div> */}
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