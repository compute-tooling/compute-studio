import React from 'react';
import { Formik, Form, Field, ErrorMessage } from 'formik';
import axios from 'axios';
import { Button } from "react-bootstrap";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

export const LoginForm = ({ setAuthStatus }) => (
  <div>
    <Formik
      initialValues={{ username: "", email: "", password: "" }}
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
          console.log(err)
        });
      }}
      render={props => (
        <Form>
          <div className="mt-1">
            <label> Username:</label>
            <Field name="username" className="form-control" />
          </div>
          <div className="mt-1">
            <label> Password </label>
            <Field name="password" type="password" className="form-control" />
          </div>
          <Button onClick={e => {
            e.preventDefault();
            props.handleSubmit(e);
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