var _a, _b;
import { Field } from 'formik';
import axios from 'axios';
import { Button } from "react-bootstrap";
import * as yup from "yup";
import { Message } from "./fields";
axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";
var LoginSchema = yup.object().shape({
    username: yup.string().required("Username is required."),
    password: yup.string().required("Password is required.")
});
var SignupSchema = yup.object().shape({
    username: yup.string().required("Username is required."),
    email: yup.string().email("Must be a valid email address.").required("Email address is required."),
    password1: yup.string().required("Password is required."),
    password2: yup
        .string()
        .oneOf([yup.ref('password1'), null], "Passwords don't match")
        .required("Confirmation password is required."),
});
export var LoginForm = function (_a) {
    var setAuthStatus = _a.setAuthStatus;
    return initialValues = {};
},  = (_a = void 0, _a.username),  = _a[""],  = _a.password,  = _a[""];
validationSchema = { LoginSchema: LoginSchema };
onSubmit = {}(values, actions);
{
    var formdata = new FormData();
    formdata.append("username", values.username);
    formdata.append("password", values.password);
    axios.post("/rest-auth/login/", formdata).then(function (resp) { setAuthStatus(true); }).catch(function (err) {
        if (err.response.status == 400) {
            actions.setStatus({ errors: err.response.data });
        }
        else {
            throw err;
        }
    });
}
render = {}({ handleSubmit: handleSubmit, status: status });
({ status: status } && status.errors && status.errors.non_field_errors ? className : ) = "alert alert-danger";
role = "alert" > { status: status, : .errors.non_field_errors } < /div> : null}
    < div;
className = "mt-1" >
    Username;
/label>
    < Field;
name = "username";
className = "form-control" /  >
    name;
"username";
render = { msg: msg } < Message;
msg = { msg: msg } /  > ;
/>
    < /div>
    < div;
className = "mt-1" >
    Password;
/label>
    < Field;
name = "password";
type = "password";
className = "form-control" /  >
    name;
"password";
render = { msg: msg } < Message;
msg = { msg: msg } /  > ;
/>
    < /div>
    < Button;
onClick = { e: e };
{
    e.preventDefault();
    handleSubmit(e);
}
variant = "primary";
className = "mt-2"
    > Login < /Button>
    < /Form>;
    >
        /Formik>
    < /div>;
;
export var SignupForm = function (_a) {
    var setAuthStatus = _a.setAuthStatus;
    return initialValues = {};
},  = (_b = void 0, _b.username),  = _b[""],  = _b.email,  = _b[""],  = _b.password1,  = _b[""],  = _b.password2,  = _b[""];
validationSchema = { SignupSchema: SignupSchema };
onSubmit = {}(values, actions);
{
    var formdata = new FormData();
    formdata.append("username", values.username);
    formdata.append("email", values.email);
    formdata.append("password1", values.password1);
    formdata.append("password2", values.password2);
    axios.post("/rest-auth/registration/", formdata).then(function (resp) { setAuthStatus(true); }).catch(function (err) {
        if (err.response.status == 400) {
            actions.setStatus({ errors: err.response.data });
        }
        else {
            throw err;
        }
    });
}
render = {}({ handleSubmit: handleSubmit, status: status });
({ status: status }
    && status.errors
    && status.errors.email ?
    className : ) = "alert alert-danger";
role = "alert" > { status: status, : .errors.email } < /div> : null};
{
    status
        && status.errors
        && status.errors.username
        ? className : ;
    "alert alert-danger";
    role = "alert" > { status: status, : .errors.username } < /div> : null};
    {
        status
            && status.errors
            && status.errors.password1
            ? className : ;
        "alert alert-danger";
        role = "alert" > { status: status, : .errors.password1.map(function (msg) { return ({ msg: msg } < /li>)}</ul > /div> : null}
                < div); }, className = "mt-1" >
                Username, /label>
                < Field, name = "username", className = "form-control" /  >
                name, "username", render = { msg: msg } < Message, msg = { msg: msg } /  > ) }
            /  >
            /div>
            < div;
        className = "mt-1" >
            Email;
        /label>
            < Field;
        name = "email";
        className = "form-control";
        type = "email" /  >
            name;
        "email";
        render = { msg: msg } < Message;
        msg = { msg: msg } /  > ;
    }
    />
        < /div>
        < div;
    className = "mt-1" >
        Password;
    /label>
        < Field;
    name = "password1";
    type = "password";
    className = "form-control" /  >
        name;
    "password1";
    render = { msg: msg } < Message;
    msg = { msg: msg } /  > ;
}
/>
    < /div>
    < div;
className = "mt-1" >
    Password;
confirmation: /label>
    < Field;
name = "password2";
type = "password";
className = "form-control" /  >
    name;
"password2";
render = { msg: msg } < Message;
msg = { msg: msg } /  > ;
/>
    < /div>
    < Button;
onClick = { e: e };
{
    e.preventDefault();
    handleSubmit(e);
}
variant = "success";
className = "mt-2"
    > Signup < /Button>
    < /Form>;
    >
        /Formik>
    < /div>;
;
//# sourceMappingURL=AuthForms.js.map