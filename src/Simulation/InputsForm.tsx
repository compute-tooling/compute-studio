"use strict";

import * as yup from "yup";
import * as React from "react";
import { FormikProps } from "formik";

import {
  MetaParameters,
  MajorSection,
  LoadingElement,
  SectionHeaderList,
  ErrorCard,
} from "./components";
import { ValidatingModal, RunModal, AuthModal, PreviewModal } from "./modal";
import {
  AccessStatus,
  Sects,
  InitialValues,
  Inputs,
  InputsDetail,
  Simulation,
  RemoteOutputs,
} from "../types";
import API from "./API";
import { Card } from "react-bootstrap";

// need to require schema in model_parameters!
export const tbLabelSchema = yup.object().shape({
  year: yup.number(),
  MARS: yup.string(),
  idedtype: yup.string(),
  EIC: yup.string(),
  data_source: yup.string(),
  use_full_sample: yup.bool(),
});

interface InputsFormProps {
  api: API;
  readOnly: boolean;
  accessStatus: AccessStatus;
  sim: Simulation<RemoteOutputs>;
  resetAccessStatus: () => void;
  setNotifyOnCompletion: (notify: boolean) => void;
  notifyOnCompletion: boolean;
  setIsPublic: (is_public: boolean) => void;
  isPublic: boolean;
  inputs: Inputs;
  defaultURL: string;
  simStatus: Simulation<any>["status"];
  showRunModal: boolean;

  resetInitialValues: (metaParameters: InputsDetail["meta_parameters"]) => void;
  resetting: boolean;

  formikProps: FormikProps<InitialValues>;

  persist?: () => void;
}

interface InputsProps {
  initialValues?: InitialValues;
  sects?: Sects;
  schema?: {
    adjustment: yup.Schema<any>;
    meta_parameters: yup.Schema<any>;
  };
  extend?: boolean;
  unknownParams?: Array<string>;
  initialServerErrors?: { [msect: string]: { errors: { [paramName: string]: any } } };
}

const InputsForm: React.FC<InputsFormProps & InputsProps> = props => {
  const [showModal, setShowModal] = React.useState(props.showRunModal);

  if (!props.inputs || props.resetting) {
    return <LoadingElement />;
  }
  let {
    accessStatus,
    setNotifyOnCompletion,
    setIsPublic,
    isPublic,
    notifyOnCompletion,
    inputs,
    resetInitialValues,
    schema,
    sects,
    extend,
    persist,
    unknownParams,
    readOnly,
    simStatus,
    sim,
  } = props;
  let { meta_parameters, model_parameters, label_to_extend } = inputs;

  let hasUnknownParams = unknownParams.length > 0;
  let unknownParamsErrors: { [sect: string]: { errors: any } } = {
    "Unknown Parameters": { errors: {} },
  };
  if (hasUnknownParams) {
    for (const param of unknownParams) {
      unknownParamsErrors["Unknown Parameters"].errors[param] = "This parameter is no longer used.";
    }
  }

  let { isSubmitting, values, touched, handleSubmit, status } = props.formikProps;
  return (
    <div>
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
                resetInitialValues={resetInitialValues}
                readOnly={props.readOnly}
              />
            </li>
            <li>
              <PreviewModal
                values={values}
                schema={yup.object().shape({
                  adjustment: schema.adjustment,
                  meta_parameters: schema.meta_parameters,
                })}
                tbLabelSchema={tbLabelSchema}
                model_parameters={model_parameters}
                label_to_extend="year" // hard code until paramtools schema enforced
                extend={extend}
              />
            </li>
            <li>
              <SectionHeaderList sects={sects} />
            </li>
            <li>
              <RunModal
                action={simStatus === "STARTED" ? "Run" : "Fork and Run"}
                handleSubmit={handleSubmit}
                accessStatus={accessStatus}
                showModal={showModal}
                setShowModal={setShowModal}
                resetAccessStatus={props.resetAccessStatus}
                notify={notifyOnCompletion}
                setNotify={setNotifyOnCompletion}
                setIsPublic={setIsPublic}
                isPublic={isPublic}
                persist={persist}
                sim={sim}
              />
            </li>
          </ul>
        </div>
        <div className="col-sm-8">
          {status && status.status === "INVALID" && status.serverErrors ? (
            <ErrorCard
              errorMsg={
                <p>
                  Some fields have errors. These must be fixed before the simulation can be
                  submitted. You may re-visit this page a later time by entering the following link:{" "}
                  <a href={inputs.detail.gui_url}>{inputs.detail.gui_url}</a>
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
                    `${inputs.detail.sim.creation_date} with version ${inputs.detail.sim.model_version}. You may view the full simulation detail `}
                  <a href={inputs.detail.sim.api_url}>here.</a>
                </p>
              }
              errors={unknownParamsErrors}
              model_parameters={{}}
            />
          ) : (
            <div />
          )}

          {inputs?.detail?.status === "FAIL" && (
            <Card className="card-outer p-2">
              <Card.Body className="alert alert-danger">
                <p>
                  <a href={`/${accessStatus.project}/`}>{accessStatus.project}</a> was unable to
                  validate your inputs. The maintainers of {accessStatus.project} have been notified
                  and are working to fix the problem.
                </p>
                <details>
                  <summary>Detail</summary>
                  <pre>
                    <code>{inputs?.detail?.traceback}</code>
                  </pre>
                </details>
              </Card.Body>
            </Card>
          )}

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
                readOnly={readOnly}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};

const InputsMemoed = React.memo(InputsForm, (prevProps, nextProps) => {
  return (
    prevProps.isPublic === nextProps.isPublic &&
    prevProps.simStatus === nextProps.simStatus &&
    prevProps.accessStatus === nextProps.accessStatus &&
    prevProps.formikProps === nextProps.formikProps
  );
});
export default InputsMemoed;
