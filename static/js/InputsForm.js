"use strict";
var __extends = (this && this.__extends) || (function () {
    var extendStatics = function (d, b) {
        extendStatics = Object.setPrototypeOf ||
            ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
            function (d, b) { for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p]; };
        return extendStatics(d, b);
    };
    return function (d, b) {
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    };
})();
import * as yup from "yup";
import React from "react";
import { Formik, Form } from "formik";
import axios from "axios";
import { MetaParameters, MajorSection, LoadingElement, Preview, SectionHeaderList, ErrorCard } from "./components";
import { ValidatingModal, RunModal, AuthModal } from "./modal";
import { formikToJSON, convertToFormik } from "./ParamTools";
import { hasServerErrors } from "./utils";
// need to require schema in model_parameters!
var tbLabelSchema = yup.object().shape({
    year: yup.number(),
    MARS: yup.string(),
    idedtype: yup.string(),
    EIC: yup.string(),
    data_source: yup.string(),
    use_full_sample: yup.bool()
});
var InputsForm = /** @class */ (function (_super) {
    __extends(InputsForm, _super);
    function InputsForm(props) {
        var _this = _super.call(this, props) || this;
        _this.state = {
            initialValues: _this.props.initialValues,
            sects: false,
            model_parameters: false,
            resetting: false,
            timer: null,
            error: null
        };
        _this.resetInitialValues = _this.resetInitialValues.bind(_this);
        _this.poll = _this.poll.bind(_this);
        _this.killTimer = _this.killTimer.bind(_this);
        return _this;
    }
    InputsForm.prototype.componentDidMount = function () {
        var _this = this;
        if (this.props.fetchInitialValues) {
            this.props
                .fetchInitialValues()
                .then(function (data) {
                var _a = convertToFormik(data), initialValues = _a[0], sects = _a[1], model_parameters = _a[2], meta_parameters = _a[3], schema = _a[4], unknownParams = _a[5];
                var hasSimData = !!data.detail && !!data.detail.sim;
                _this.setState({
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
                    initialServerErrors: !!data.detail && hasServerErrors(data.detail.errors_warnings)
                        ? data.detail.errors_warnings
                        : null,
                    accessStatus: data.accessStatus
                });
            })
                .catch(function (err) {
                _this.setState({ error: err });
            });
        }
    };
    InputsForm.prototype.resetInitialValues = function (metaParameters) {
        var _this = this;
        this.setState({ resetting: true });
        this.props
            .resetInitialValues({
            meta_parameters: tbLabelSchema.cast(metaParameters)
        })
            .then(function (data) {
            var _a = convertToFormik(data), initialValues = _a[0], sects = _a[1], model_parameters = _a[2], meta_parameters = _a[3], schema = _a[4], unknownParams = _a[5];
            _this.setState({
                initialValues: initialValues,
                sects: sects,
                model_parameters: model_parameters,
                meta_parameters: meta_parameters,
                schema: schema,
                extend: "extend" in data ? data.extend : false,
                resetting: false
            });
        })
            .catch(function (err) {
            _this.setState({ error: err });
        });
    };
    InputsForm.prototype.poll = function (actions, respData) {
        var _this = this;
        var timer = setInterval(function () {
            axios
                .get(respData.api_url)
                .then(function (response) {
                // be careful with race condidition where status is SUCCESS but
                // sim has not yet been submitted and saved!
                if (response.data.status === "SUCCESS" &&
                    response.data.sim !== null) {
                    actions.setSubmitting(false);
                    actions.setStatus({
                        status: response.data.status,
                        simUrl: response.data.sim.gui_url
                    });
                    _this.killTimer();
                    window.location.href = response.data.sim.gui_url;
                }
                else if (response.data.status === "INVALID") {
                    actions.setSubmitting(false);
                    actions.setStatus({
                        status: response.data.status,
                        serverErrors: response.data.errors_warnings,
                        editInputsUrl: response.data.edit_inputs_url
                    });
                    window.scroll(0, 0);
                    _this.killTimer();
                }
            })
                .catch(function (error) {
                console.log("polling error:");
                console.log(error);
                _this.killTimer();
                actions.setSubmitting(false);
                // request likely cancelled because timer was killed.
                if (error.message && error.message != "Request aborted") {
                    _this.setState({ error: error });
                }
            });
        }, 500);
        this.setState({ timer: timer });
    };
    InputsForm.prototype.killTimer = function () {
        if (!!this.state.timer) {
            clearInterval(this.state.timer);
            this.setState({ timer: null });
        }
    };
    InputsForm.prototype.componentWillUnmount = function () {
        this.killTimer();
    };
    InputsForm.prototype.render = function () {
        var _this = this;
        if (this.state.error !== null) {
            throw this.state.error;
        }
        if (!this.state.model_parameters ||
            !this.state.initialValues ||
            this.state.resetting) {
            return React.createElement(LoadingElement, null);
        }
        console.log("rendering");
        var meta_parameters = this.state.meta_parameters;
        var model_parameters = this.state.model_parameters;
        var initialValues = this.state.initialValues;
        var schema = this.state.schema;
        var sects = this.state.sects;
        var extend = this.state.extend;
        var hasUnknownParams = this.state.unknownParams.length > 0;
        var unknownParamsErrors = { "Unknown Parameters": { errors: {} } };
        if (hasUnknownParams) {
            for (var _i = 0, _a = this.state.unknownParams; _i < _a.length; _i++) {
                var param = _a[_i];
                unknownParamsErrors["Unknown Parameters"].errors[param] =
                    "This parameter is no longer used.";
            }
        }
        var initialStatus;
        if (this.state.initialServerErrors) {
            initialStatus = {
                serverErrors: this.state.initialServerErrors,
                status: "INVALID",
                editInputsUrl: this.state.editInputsUrl
            };
        }
        return (React.createElement("div", null,
            React.createElement(Formik, { initialValues: initialValues, validationSchema: schema, validateOnChange: false, validateOnBlur: true, enableReinitialize: true, initialStatus: initialStatus, onSubmit: function (values, actions) {
                    var _a = formikToJSON(values, _this.state.schema, tbLabelSchema, _this.state.extend), meta_parameters = _a[0], adjustment = _a[1];
                    console.log("submitting");
                    console.log(adjustment);
                    console.log(meta_parameters);
                    var formdata = new FormData();
                    formdata.append("adjustment", JSON.stringify(adjustment));
                    formdata.append("meta_parameters", JSON.stringify(meta_parameters));
                    formdata.append("client", "web-beta");
                    _this.props
                        .doSubmit(formdata)
                        .then(function (response) {
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
                        _this.poll(actions, response.data);
                    })
                        .catch(function (error) {
                        console.log("error", error);
                        actions.setSubmitting(false);
                        actions.setStatus({ status: null });
                        if (error.response.status == 403) {
                            actions.setStatus({
                                auth: "You must be logged in to publish a model."
                            });
                        }
                    });
                }, render: function (_a) {
                    var handleSubmit = _a.handleSubmit, handleChange = _a.handleChange, handleBlur = _a.handleBlur, status = _a.status, isSubmitting = _a.isSubmitting, errors = _a.errors, values = _a.values, setFieldValue = _a.setFieldValue, touched = _a.touched;
                    return (React.createElement(Form, null,
                        isSubmitting ? React.createElement(ValidatingModal, null) : React.createElement("div", null),
                        status && status.auth ? React.createElement(AuthModal, null) : React.createElement("div", null),
                        React.createElement("div", { className: "row" },
                            React.createElement("div", { className: "col-sm-4" },
                                React.createElement("ul", { className: "list-unstyled components sticky-top scroll-y" },
                                    React.createElement("li", null,
                                        React.createElement(MetaParameters, { meta_parameters: meta_parameters, values: values.meta_parameters, touched: touched, resetInitialValues: _this.resetInitialValues })),
                                    React.createElement("li", null,
                                        React.createElement(SectionHeaderList, { sects: sects })),
                                    React.createElement("li", null,
                                        React.createElement(RunModal, { handleSubmit: handleSubmit, accessStatus: _this.state.accessStatus })))),
                            React.createElement("div", { className: "col-sm-8" },
                                status &&
                                    status.status === "INVALID" &&
                                    status.serverErrors ? (React.createElement(ErrorCard, { errorMsg: React.createElement("p", null,
                                        "Some fields have errors. These must be fixed before the simulation can be submitted. You may re-visit this page a later time by entering the following link:",
                                        " ",
                                        React.createElement("a", { href: status.editInputsUrl }, status.editInputsUrl)), errors: status.serverErrors, model_parameters: model_parameters })) : (React.createElement("div", null)),
                                hasUnknownParams ? (React.createElement(ErrorCard, { errorMsg: React.createElement("p", null,
                                        "One or more parameters have been renamed or " +
                                            "removed since this simulation was run on " +
                                            (_this.state.creationDate + " with version " + _this.state.modelVersion + ". You may view the full simulation detail "),
                                        React.createElement("a", { href: _this.state.detailAPIURL }, "here.")), errors: unknownParamsErrors, model_parameters: {} })) : (React.createElement("div", null)),
                                React.createElement(Preview, { values: values, schema: schema, tbLabelSchema: tbLabelSchema, transformfunc: formikToJSON, extend: extend }),
                                Object.entries(sects).map(function (msect_item, ix) {
                                    // msect --> section_1: dict(dict) --> section_2: dict(dict)
                                    var msect = msect_item[0];
                                    var section_1_dict = msect_item[1];
                                    return (React.createElement(MajorSection, { key: msect + "-component", msect: msect, section_1_dict: section_1_dict, meta_parameters: meta_parameters, model_parameters: model_parameters, handleSubmit: handleSubmit, handleChange: handleChange, status: status, errors: errors, values: values, setFieldValue: setFieldValue, handleBlur: handleBlur, extend: extend }));
                                })))));
                } })));
    };
    return InputsForm;
}(React.Component));
export default InputsForm;
//# sourceMappingURL=InputsForm.js.map