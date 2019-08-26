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
          <label>
            Username:
            <Field name="username" className="form-control" />
          </label>
          <label>
            Password
            <Field name="password" type="password" className="form-control" />
          </label>
          <Button onClick={e => {
            e.preventDefault();
            props.handleSubmit(e);
          }}> Login </Button>
        </Form>
      )}

    >
    </Formik>
  </div>
);