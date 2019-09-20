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
import React from "react";
import { Card } from "react-bootstrap";
import * as Sentry from "@sentry/browser";
var ErrorBoundary = /** @class */ (function (_super) {
    __extends(ErrorBoundary, _super);
    function ErrorBoundary(props) {
        var _this = _super.call(this, props) || this;
        _this.state = { error: null, errorInfo: null };
        return _this;
    }
    ErrorBoundary.prototype.componentDidCatch = function (error, errorInfo) {
        var _this = this;
        if (process.env.NODE_ENV === "production") {
            Sentry.withScope(function (scope) {
                scope.setExtras(errorInfo);
                var eventId = Sentry.captureException(error);
                _this.setState({
                    eventId: eventId,
                    error: error,
                    errorInfo: errorInfo
                });
            });
        }
        else {
            this.setState({
                error: error,
                errorInfo: errorInfo
            });
        }
    };
    ErrorBoundary.prototype.render = function () {
        if (this.state.errorInfo) {
            // Error path
            return (React.createElement(Card, { className: "card-outer" },
                React.createElement(Card.Body, null,
                    React.createElement(Card.Title, null,
                        React.createElement("h2", null, "Whoops! Compute Studio has experienced an error.")),
                    React.createElement(Card.Text, null,
                        "The Compute Studio technical team has been notified of this error and is working to fix it. In addition, you are welcome to discuss this issue with the Compute Studio technical team by opening an",
                        " ",
                        React.createElement("a", { href: "https://github.com/compute-tooling/compute-studio/issues/new" }, "issue"),
                        " ",
                        "in the Compute Studio source code repository or",
                        " ",
                        React.createElement("a", { href: "mailto:henrymdoupe@gmail.com" }, "emailing Hank"),
                        "."))));
        }
        return this.props.children;
    };
    return ErrorBoundary;
}(React.Component));
export default ErrorBoundary;
//# sourceMappingURL=ErrorBoundary.js.map