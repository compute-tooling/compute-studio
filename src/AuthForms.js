import React from 'react';
import { Formik, Form, Field, ErrorMessage } from 'formik';
import axios from 'axios';
import { Button } from "react-bootstrap";
import * as yup from "yup";

import { Message } from "./fields";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

let schema = yup.object().shape({
  username: yup.string().required("Username is required."),
  password: yup.string().required("Password is required.")
})

export const LoginForm = ({ setAuthStatus }) => (
  <div>
    <Formik
      initialValues={{ username: "", email: "", password: "" }}
      validationSchema={schema}
      onSubmit={(values, actions) => {
        console.log("logging in....")
        let formdata = new FormData();
        formdata.append("username", values.username);
        formdata.append("password", values.password);
        axios.post(
          "/rest-auth/login/",
          formdata
        ).then(
          resp => { setAuthStatus(true) }
        ).catch(err => {
          actions.setStatus({ errors: err.response.data })
        });
      }}
      render={({ handleSubmit, status }) => (
        <Form>
          {status && status.errors && status.errors.non_field_errors ? <div className="alert alert-danger" role="alert"> {status.errors.non_field_errors}</div> : null}
          <div className="mt-1">
            <label> Username:</label>
            <Field name="username" className="form-control" />
            <ErrorMessage
              name="username"
              render={msg => <Message msg={msg} />}
            />
          </div>
          <div className="mt-1">
            <label> Password </label>
            <Field name="password" type="password" className="form-control" />
            <ErrorMessage
              name="password"
              render={msg => <Message msg={msg} />}
            />
          </div>
          <Button onClick={e => {
            e.preventDefault();
            handleSubmit(e);
          }}
            variant="primary"
            className="mt-2"
          > Login </Button>
        </Form>
      )}

    >
    </Formik>
  </div>
);
