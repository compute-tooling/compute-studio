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
import { Button, Modal, Collapse } from "react-bootstrap";
import * as React from "react";
import * as ReactLoading from "react-loading";
import { LoginForm, SignupForm } from "./AuthForms";
import axios from "axios";
var ValidatingModal = /** @class */ (function (_super) {
    __extends(ValidatingModal, _super);
    function ValidatingModal(props) {
        var _this = _super.call(this, props) || this;
        _this.state = {
            show: true,
            setShow: true
        };
        _this.handleClose = _this.handleClose.bind(_this);
        _this.handleShow = _this.handleShow.bind(_this);
        return _this;
    }
    ValidatingModal.prototype.handleClose = function () {
        this.setState({ setShow: false, show: false });
    };
    ValidatingModal.prototype.handleShow = function () {
        this.setState({ setShow: true, show: true });
    };
    ValidatingModal.prototype.render = function () {
        return (React.createElement("div", null,
            React.createElement(Modal, { show: this.state.show, onHide: this.handleClose },
                React.createElement(Modal.Header, { closeButton: true },
                    React.createElement(Modal.Title, null, "Validating inputs...")),
                React.createElement(Modal.Body, null,
                    React.createElement("div", { className: "d-flex justify-content-center" },
                        React.createElement(ReactLoading, { type: "spokes", color: "#28a745" }))))));
    };
    return ValidatingModal;
}(React.Component));
export { ValidatingModal };
var PricingInfoCollapse = function (_a) {
    var accessStatus = _a.accessStatus;
    var _b = React.useState(false), collapseOpen = _b[0], setCollapseOpen = _b[1];
    return (React.createElement(React.Fragment, null,
        React.createElement(Button, { onClick: function () { return setCollapseOpen(!collapseOpen); }, "aria-controls": "pricing-collapse-text", "aria-expanded": collapseOpen, className: "mt-3 mb-3", variant: "outline-info" }, "Pricing"),
        React.createElement(Collapse, { in: collapseOpen },
            React.createElement("div", { id: "pricing-collapse-text" },
                "The models are offered for free, but you pay for the computational resources used to run them. The prices are equal to Google Cloud Platform compute pricing, subject to costing at least one penny for a single run.",
                React.createElement("ul", null,
                    React.createElement("li", null,
                        "The price per hour of a server running this model is: $", "" + accessStatus.server_cost,
                        "/hour."),
                    React.createElement("li", null,
                        "The expected time required for a single run of this model is: ", "" + accessStatus.exp_time,
                        " seconds."))))));
};
var RequireLoginDialog = function (_a) {
    var show = _a.show, setShow = _a.setShow, handleSubmit = _a.handleSubmit, accessStatus = _a.accessStatus;
    var _b = React.useState(false), authenticated = _b[0], setAuthStatus = _b[1];
    var _c = React.useState(false), hasSubmitted = _c[0], setHasSubmitted = _c[1];
    var _d = React.useState(null), newDialog = _d[0], updateNewDialog = _d[1];
    var _e = React.useState(true), isLogIn = _e[0], setIsLogIn = _e[1];
    if (authenticated && !hasSubmitted) {
        axios.get(accessStatus.api_url).then(function (resp) {
            var accessStatus = resp.data;
            var dialog = React.createElement(Dialog, { accessStatus: accessStatus, show: show, setShow: null, handleSubmit: handleSubmit });
            updateNewDialog(dialog);
        });
        setHasSubmitted(true);
    }
    if (newDialog !== null) {
        return newDialog;
    }
    return (React.createElement(Modal, { show: show, onHide: function () { return setShow(false); } },
        React.createElement(Modal.Header, { closeButton: true },
            React.createElement(Modal.Title, null, "You must be logged in to run simulations.")),
        React.createElement(Modal.Body, null,
            React.createElement("div", { className: "mt-2" }, isLogIn ?
                React.createElement(LoginForm, { setAuthStatus: setAuthStatus })
                :
                    React.createElement(SignupForm, { setAuthStatus: setAuthStatus })),
            React.createElement(Button, { className: "mt-3", variant: "outline-" + (!isLogIn ? "primary" : "success"), onClick: function () { return setIsLogIn(!isLogIn); } }, !isLogIn ? "Log in" : "Sign up")),
        React.createElement(Modal.Footer, null,
            React.createElement(Button, { variant: "outline-secondary", onClick: function () { return setShow(false); } }, "Close"))));
};
var RequirePmtDialog = function (_a) {
    var show = _a.show, setShow = _a.setShow, accessStatus = _a.accessStatus;
    var handleCloseWithRedirect = function (e, redirectLink) {
        e.preventDefault();
        setShow(false);
        window.location.href = redirectLink;
    };
    return (React.createElement(Modal, { show: show, onHide: function () { return setShow(false); } },
        React.createElement(Modal.Header, { closeButton: true },
            React.createElement(Modal.Title, null, "Add a payment method")),
        React.createElement(Modal.Body, null,
            "You must submit a payment method to run paid simulations.",
            React.createElement(PricingInfoCollapse, { accessStatus: accessStatus })),
        React.createElement(Modal.Footer, null,
            React.createElement(Button, { variant: "outline-secondary", onClick: function () { return setShow(false); } }, "Close"),
            React.createElement(Button, { variant: "success", onClick: function (e) { return handleCloseWithRedirect(e, "/billing/update/"); } },
                React.createElement("b", null, "Add payment method")))));
};
var RunDialog = function (_a) {
    var show = _a.show, setShow = _a.setShow, handleSubmit = _a.handleSubmit, accessStatus = _a.accessStatus;
    var handleCloseWithSubmit = function () {
        setShow(false);
        handleSubmit();
    };
    var body;
    if (accessStatus.is_sponsored) {
        body = React.createElement(Modal.Body, null, " This model's simulations are sponsored and thus, are free for you.");
    }
    else {
        body = (React.createElement(Modal.Body, null,
            React.createElement("p", null,
                "This simulation will cost $", "" + accessStatus.exp_cost,
                ". You will be billed at the end of the monthly billing period."),
            React.createElement(PricingInfoCollapse, { accessStatus: accessStatus })));
    }
    return (React.createElement(Modal, { show: show, onHide: function () { return setShow(false); } },
        React.createElement(Modal.Header, { closeButton: true },
            React.createElement(Modal.Title, null, "Are you sure that you want to run this simulation?")),
        body,
        React.createElement(Modal.Footer, null,
            React.createElement(Button, { variant: "secondary", onClick: function () { return setShow(false); } }, "Close"),
            React.createElement(Button, { variant: "success", onClick: handleCloseWithSubmit, type: "submit" }, "Run simulation"))));
};
var Dialog = function (_a) {
    var _b;
    var accessStatus = _a.accessStatus, show = _a.show, setShow = _a.setShow, handleSubmit = _a.handleSubmit;
    if (setShow == null) {
        _b = React.useState(show), show = _b[0], setShow = _b[1];
    }
    if (accessStatus.can_run) {
        return React.createElement(RunDialog, { accessStatus: accessStatus, show: show, setShow: setShow, handleSubmit: handleSubmit });
    }
    else if (accessStatus.user_status === "anon") {
        return React.createElement(RequireLoginDialog, { accessStatus: accessStatus, show: show, setShow: setShow, handleSubmit: handleSubmit });
    }
    else if (accessStatus.user_status === "profile") {
        return React.createElement(RequirePmtDialog, { accessStatus: accessStatus, show: show, setShow: setShow, handleSubmit: handleSubmit });
    }
};
export var RunModal = function (_a) {
    var handleSubmit = _a.handleSubmit, accessStatus = _a.accessStatus;
    var _b = React.useState(false), show = _b[0], setShow = _b[1];
    var handleShow = function (show) {
        setShow(show);
    };
    var runbuttontext = "Run";
    if (!accessStatus.is_sponsored) {
        runbuttontext = "Run ($" + accessStatus.exp_cost + ")";
    }
    return (React.createElement(React.Fragment, null,
        React.createElement("div", { className: "card card-body card-outer" },
            React.createElement(Button, { variant: "primary", onClick: function () { return setShow(true); }, className: "btn btn-block btn-success" },
                React.createElement("b", null, runbuttontext))),
        React.createElement(Dialog, { accessStatus: accessStatus, show: show, setShow: handleShow, handleSubmit: handleSubmit })));
};
export var AuthModal = function () {
    var _a = React.useState(true), show = _a[0], setShow = _a[1];
    var handleClose = function () { return setShow(false); };
    var handleShow = function () { return setShow(true); };
    var handleCloseWithRedirect = function (e, redirectLink) {
        e.preventDefault();
        setShow(false);
        window.location.replace(redirectLink);
    };
    return (React.createElement(React.Fragment, null,
        React.createElement(Modal, { show: show, onHide: handleClose },
            React.createElement(Modal.Header, { closeButton: true },
                React.createElement(Modal.Title, null, "Sign up")),
            React.createElement(Modal.Body, null, "You must be logged in to run simulations."),
            React.createElement(Modal.Footer, null,
                React.createElement(Button, { variant: "secondary", onClick: handleClose }, "Close"),
                React.createElement(Button, { variant: "secondary", onClick: function (e) { return handleCloseWithRedirect(e, "/users/login"); } },
                    React.createElement("b", null, "Log in")),
                React.createElement(Button, { variant: "success", onClick: function (e) { return handleCloseWithRedirect(e, "/users/signup"); } },
                    React.createElement("b", null, "Sign up"))))));
};
//# sourceMappingURL=modal.js.map