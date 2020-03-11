import React = require("react");
import { Row, Col, Button, Modal } from "react-bootstrap";
import API from "./API";
import { Simulation, RemoteOutputs, DescriptionValues } from "../types";
import { FormikProps, Field, FastField } from "formik";
import { Tip } from "../components";
import { RolePerms } from "../roles";

const ConfirmSelected: React.FC<{
  userFieldName: string;
  msgFieldName: string;
  setSelected: (selected: boolean) => void;
  formikProps: FormikProps<DescriptionValues>;
}> = ({ userFieldName, msgFieldName, setSelected, formikProps }) => {
  const { setFieldValue, handleSubmit } = formikProps;
  return (
    <>
      <FastField
        name={msgFieldName}
        type="text"
        className="form-control my-2"
        component="textarea"
        placeholder="Add a note"
      ></FastField>
      <Row className="w-100 justify-content-left p-0 my-2">
        <Col className="col-auto">
          <a
            className="btn btn-success"
            style={{ color: "white", cursor: "pointer" }}
            onClick={() => {
              setTimeout(handleSubmit, 0);
              setTimeout(() => setFieldValue(userFieldName, ""), 0);
              setTimeout(() => setFieldValue(msgFieldName, ""), 0);
              setSelected(false);
            }}
          >
            Confirm
          </a>
        </Col>
        <Col className="col-auto">
          <a
            className="btn btn-light"
            style={{ color: "black", cursor: "pointer" }}
            onClick={() => {
              setFieldValue(userFieldName, "");
              setFieldValue(msgFieldName, "");
              setSelected(false);
            }}
          >
            Cancel
          </a>
        </Col>
      </Row>
    </>
  );
};

const UserQuery: React.FC<{
  show: boolean;
  selectedUsers: Array<{ username: string }>;
  query: Array<{ username: string }>;
  onSelectUser: (user: { username: string }) => void;
}> = ({ show, selectedUsers, query, onSelectUser }) => {
  if (!query || query.length === 0 || !show) return null;

  return (
    <div className="border rounded shadow mt-2 custom-dropdown-menu">
      {query.map((user, qix) => (
        <Row className="my-2 mx-3 w-auto" key={qix}>
          <Col>
            <a
              className="color-inherit"
              role="button"
              style={{ cursor: "pointer" }}
              onClick={() => onSelectUser(user)}
            >
              {user.username}
              {selectedUsers.find(sel => sel.username === user.username) ? (
                <span className="text-muted"> &#183; Already selected.</span>
              ) : null}
            </a>
          </Col>
        </Row>
      ))}
    </div>
  );
};

export const CollaborationSettings: React.FC<{
  api: API;
  user: string;
  remoteSim?: Simulation<RemoteOutputs>;
  formikProps: FormikProps<DescriptionValues>;
}> = ({ api, user, remoteSim, formikProps }) => {
  const [show, setShow] = React.useState(false);
  const [viewAuthorQuery, setViewAuthorQuery] = React.useState(false);
  const [authorQuery, setAuthorQuery] = React.useState<Array<{ username: string }>>([]);
  const [authorSelected, setAuthorSelected] = React.useState(false);

  const [accessQuery, setAccessQuery] = React.useState<Array<{ username: string }>>([]);
  const [viewAccessQuery, setViewAccessQuery] = React.useState(false);
  const [accessSelected, setAccessSelected] = React.useState(false);

  let authors: Array<{
    username: string;
    pending?: boolean;
  }> = (remoteSim?.authors || []).map((author, ix) => ({ username: author }));
  if (remoteSim?.pending_permissions) {
    for (const pp of remoteSim.pending_permissions) {
      if (pp.permission_name === "add_author" && !pp.is_expired) {
        authors.push({ username: pp.profile, pending: true });
      }
    }
  }

  const handleQuery = (e, updateFunc: (users: Array<{ username: string }>) => void) => {
    api.queryUsers(e.target.value).then(data => {
      updateFunc(data);
    });
  };

  const { values, setFieldValue, handleSubmit } = formikProps;

  const is_public = remoteSim?.is_public !== undefined ? remoteSim.is_public : values.is_public;

  return (
    <>
      <Button
        variant="dark"
        style={{ backgroundColor: "rgba(60, 62, 62, 1)" }}
        className="mb-4 w-100 mt-1"
        onClick={() => setShow(true)}
      >
        <>
          <i className={`fas fa-${is_public ? "lock-open" : "lock"} mr-2`}></i>
          Share
        </>
      </Button>

      <Modal show={show} onHide={() => setShow(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Collaboration Settings</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {formikProps.status?.collaboratorLimit ? (
            <Row className="w-100">
              <Col>
                <div className="alert alert-danger" role="alert">
                  You have reached the limit for the number of collaborators on private simulations.
                  You may make this simulation public or upgrade to{" "}
                  <a href="/billing/upgrade/">
                    <strong>Compute Studio Pro</strong>
                  </a>{" "}
                  to add more collaborators.
                </div>
              </Col>
            </Row>
          ) : null}
          <Row className="w-100 my-2 mx-0">
            <Col>
              <p className="lead ml-0">Authors</p>
              <div className="row-flush">
                {(authors.length > 0 ? authors : [{ username: user }]).map((author, ix) => (
                  <Row key={ix} className="w-100 p-2 justify-content-between row-flush-item">
                    <Col className="col-7">
                      <span>{author.username}</span>
                    </Col>
                    <Col className="col-4">
                      {author.pending ? (
                        <Tip tip={`Waiting for ${author.username}'s approval.`}>
                          <span className="text-muted">pending</span>
                        </Tip>
                      ) : null}
                      {author.username === remoteSim?.owner ? (
                        <span className="text-success">owner</span>
                      ) : null}
                    </Col>
                    <Col className="col-1">
                      {/* owner cannt be removed, to remove an author user must have
                      write access or be removing themselves. */}
                      {remoteSim &&
                      author.username !== remoteSim?.owner &&
                      ((remoteSim && RolePerms.hasAdminAccess(remoteSim)) ||
                        user === author.username) ? (
                        <a
                          className="color-inherit"
                          role="button"
                          style={{ maxHeight: 0.5, cursor: "pointer" }}
                          onClick={() => {
                            setFieldValue("author.remove.username", author.username);
                            setTimeout(handleSubmit, 0);
                            setTimeout(() => setFieldValue("author.remove", ""), 0);
                          }}
                        >
                          <i className="far fa-trash-alt hover-red"></i>
                        </a>
                      ) : null}
                    </Col>
                  </Row>
                ))}
              </div>
            </Col>
          </Row>
          {remoteSim && RolePerms.hasAdminAccess(remoteSim) ? (
            <Row className="w-100 justify-content-left my-2">
              <Col>
                <Field name="author.add.username">
                  {({ field }) => (
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Search by email or username."
                      {...field}
                      onFocus={() => {
                        setViewAuthorQuery(true);
                      }}
                      onChange={e => {
                        setViewAuthorQuery(true);
                        handleQuery(e, users => setAuthorQuery(users));
                        setFieldValue("author.add.username", e.target.value);
                      }}
                      readOnly={authorSelected}
                    ></input>
                  )}
                </Field>
                <UserQuery
                  query={authorQuery}
                  selectedUsers={authors}
                  show={viewAuthorQuery}
                  onSelectUser={selected => {
                    if (authors.find(a => a.username === selected.username)) return;
                    setFieldValue("author.add.username", selected.username);
                    setAuthorSelected(true);
                    setAuthorQuery([]);
                  }}
                />
                {authorSelected ? (
                  <ConfirmSelected
                    userFieldName="author.add.username"
                    msgFieldName="author.add.msg"
                    setSelected={setAuthorSelected}
                    formikProps={formikProps}
                  />
                ) : null}
              </Col>
            </Row>
          ) : null}
          {RolePerms.hasAdminAccess(remoteSim) || !remoteSim ? (
            <Row className="w-100 mt-4 mb-2 mx-0">
              <Col>
                <p className="lead">Who has access</p>
                {is_public ? (
                  <p>
                    This simulation is <strong>public</strong> and can be viewed by anyone.
                  </p>
                ) : (
                  <p>
                    This simulation is <strong>private</strong> and can only be viewed by users who
                    have been granted access to it.
                  </p>
                )}
                <Row className="w-100 justify-content-center">
                  <Col className="col-auto">
                    <Button
                      variant="dark"
                      style={{ backgroundColor: "rgba(60, 62, 62, 1)", fontWeight: 450 }}
                      className="mb-4 w-100 mt-1"
                      onClick={() => {
                        setFieldValue("is_public", !is_public);
                        // put handleSubmit in setTimeout since setFieldValue is async
                        // but does not return a promise
                        // https://github.com/jaredpalmer/formik/issues/529
                        setTimeout(handleSubmit, 0);
                      }}
                    >
                      Make this simulation {is_public ? "private" : "public"}
                    </Button>
                  </Col>
                </Row>
              </Col>
            </Row>
          ) : null}
          {RolePerms.hasAdminAccess(remoteSim) ? (
            <>
              <Row className="w-100 my-2 mx-0">
                <Col>
                  <p className="lead">Manage access</p>
                  <div className="row-flush">
                    {remoteSim.access.map((accessobj, ix) => (
                      <Row key={ix} className="w-100 p-2 justify-content-between row-flush-item">
                        <Col className="col-7">
                          <span>{accessobj.username}</span>
                        </Col>
                        <Col className="col-4">
                          {accessobj.is_owner ? (
                            <span className="text-success">owner</span>
                          ) : (
                            <span className="text-muted">{accessobj.role}</span>
                          )}
                        </Col>
                        <Col className="col-1">
                          {/* owner cannot lose access, and authors must be removed as authors
                          before they can lose access to the simulation. */}
                          {accessobj.username !== remoteSim?.owner &&
                          !authors.find(author => author.username === accessobj.username) ? (
                            <a
                              className="color-inherit"
                              role="button"
                              style={{ maxHeight: 0.5, cursor: "pointer" }}
                              onClick={() => {
                                setFieldValue("access.read.remove.username", accessobj.username);
                                setTimeout(handleSubmit, 0);
                                setTimeout(
                                  () => setFieldValue("access.read.remove.username", ""),
                                  0
                                );
                              }}
                            >
                              <i className="far fa-trash-alt hover-red"></i>
                            </a>
                          ) : null}
                        </Col>
                      </Row>
                    ))}
                  </div>
                </Col>
              </Row>
              <Row className="w-100 justify-content-left my-2">
                <Col>
                  <Field name="access.read.grant.username">
                    {({ field }) => (
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Search by email or username."
                        {...field}
                        onFocus={() => {
                          setViewAccessQuery(true);
                        }}
                        onChange={e => {
                          setViewAccessQuery(true);
                          handleQuery(e, users => setAccessQuery(users));
                          setFieldValue("access.read.grant.username", e.target.value);
                        }}
                        readOnly={accessSelected}
                      ></input>
                    )}
                  </Field>
                  <UserQuery
                    query={accessQuery}
                    selectedUsers={remoteSim.access}
                    show={viewAccessQuery}
                    onSelectUser={selected => {
                      if (remoteSim.access.find(a => a.username === selected.username)) return;
                      setFieldValue("access.read.grant.username", selected.username);
                      setAccessSelected(true);
                      setAccessQuery([]);
                    }}
                  />
                  {accessSelected ? (
                    <ConfirmSelected
                      userFieldName="access.read.grant.username"
                      msgFieldName="access.read.grant.msg"
                      setSelected={setAccessSelected}
                      formikProps={formikProps}
                    />
                  ) : null}
                </Col>
              </Row>
            </>
          ) : null}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-primary" onClick={() => setShow(false)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
};
