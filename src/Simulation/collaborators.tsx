import React = require("react");
import { Row, Col, Button, Modal, Dropdown } from "react-bootstrap";
import API from "./API";
import { Simulation, RemoteOutputs, DescriptionValues, Role } from "../types";
import { FormikProps, Field, FastField, setNestedObjectValues } from "formik";
import { Tip } from "../components";
import { RolePerms } from "../roles";

const prettyRole = (role: Role | "owner") => {
  switch (role) {
    case "read":
      return "Reader";
    case "write":
      return "Write";
    case "admin":
      return "Administrator";
    case "owner":
      return "Onwer";
  }
};

const ConfirmSelected: React.FC<{
  selectedUser: string;
  setSelected: (selected: boolean) => void;
  formikProps: FormikProps<DescriptionValues>;
  defaultInviteAuthor?: boolean;
}> = ({ selectedUser, setSelected, formikProps, defaultInviteAuthor }) => {
  const [inviteAuthor, setInviteAuthor] = React.useState(
    defaultInviteAuthor !== undefined ? defaultInviteAuthor : false
  );
  const [msg, setMsg] = React.useState("");
  const { handleSubmit, setValues, values } = formikProps;

  return (
    <>
      <textarea
        name="message"
        className="form-control my-2"
        // component="textarea"
        value={msg}
        placeholder="Add a note"
        onChange={e => setMsg(e.target.value)}
      />
      <Row className="w-100 justify-content-left p-0 my-2">
        <Col className="col-auto align-self-center">
          <input
            className="form-check mt-1 d-inline-block mr-2"
            type="checkbox"
            name="inviteAuthor"
            id="inviteAuthor"
            checked={inviteAuthor}
            onChange={e => {
              setInviteAuthor(!inviteAuthor);
            }}
          />
          <label className="align-middle" htmlFor="inviteAuthor">
            <strong>Invite to author</strong>
          </label>
        </Col>
      </Row>
      <Row className="w-100 justify-content-left p-0 my-2">
        <Col className="col-auto">
          <a
            className="btn btn-success"
            style={{ color: "white", cursor: "pointer" }}
            onClick={() => {
              if (inviteAuthor) {
                setValues({
                  ...formikProps.values,
                  author: {
                    add: { username: selectedUser, msg: msg },
                    remove: { username: "" }
                  },
                  access: {
                    read: { grant: { username: "", msg: "" }, remove: { username: "" } }
                  }
                });
              } else {
                setValues({
                  ...formikProps.values,
                  author: { add: { username: "", msg: "" }, remove: { username: "" } },
                  access: {
                    read: {
                      grant: { username: selectedUser, msg: msg },
                      remove: { username: "" }
                    }
                  }
                });
              }

              setTimeout(handleSubmit, 0);

              setTimeout(() =>
                setValues({
                  ...values,
                  author: { add: { username: "", msg: "" }, remove: { username: "" } },
                  access: { read: { grant: { username: "", msg: "" }, remove: { username: "" } } }
                })
              );

              setSelected(false);
            }}
          >
            <strong>Confirm</strong>
          </a>
        </Col>
        <Col className="col-auto">
          <a
            className="btn btn-light"
            style={{ color: "black", cursor: "pointer" }}
            onClick={() => {
              setValues({
                ...values,
                author: { add: { username: "", msg: "" }, remove: { username: "" } },
                access: { read: { grant: { username: "", msg: "" }, remove: { username: "" } } }
              });
              setMsg("");
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

  const [accessQuery, setAccessQuery] = React.useState<Array<{ username: string }>>([]);
  const [viewAccessQuery, setViewAccessQuery] = React.useState(false);
  const [accessSelected, setAccessSelected] = React.useState(false);

  const [authorSelected, setAuthorSelected] = React.useState(false);

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

  let accessobjs: Simulation<any>["access"];
  if (RolePerms.hasAdminAccess(remoteSim)) {
    accessobjs = remoteSim.access;
  } else {
    accessobjs = [{ username: user, role: "read", is_owner: false }];
  }

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
          {RolePerms.hasAdminAccess(remoteSim) || !remoteSim ? (
            <Row className="w-100 mb-2 mx-0">
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
                      style={{ backgroundColor: "rgba(60, 62, 62, 1)", fontWeight: 600 }}
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
          {user !== "anon" ? (
            <>
              <Row className="w-100 my-2 mx-0">
                <Col>
                  <p className="lead">People</p>
                  <div className="row-flush">
                    {accessobjs.map((accessobj, ix) => {
                      const author = authors.find(author => author.username === accessobj.username);
                      return (
                        <Row key={ix} className="w-100 p-2 justify-content-between row-flush-item">
                          <Col className="col-5">
                            <span>
                              <strong>{accessobj.username}</strong>
                            </span>
                          </Col>
                          <Col className="col-2">
                            {accessobj.is_owner ? (
                              <span>Owner</span>
                            ) : (
                              <span>{prettyRole(accessobj.role)}</span>
                            )}
                          </Col>
                          <Col className="col-4">
                            {!!author ? (
                              author.pending ? (
                                <span className="text-muted">
                                  <i className="fas fa-user-friends mr-1"></i>
                                  <span className="text-muted">Author &#183; pending</span>
                                </span>
                              ) : (
                                <span className="text-success">
                                  <i className="fas fa-user-friends mr-1"></i>Author
                                </span>
                              )
                            ) : (
                              <a
                                href="#"
                                className="btn btn-outline-secondary lh-1"
                                onClick={e => {
                                  e.preventDefault();
                                  console.log("setting", accessobj.username);
                                  setFieldValue("author.add.username", accessobj.username);
                                  setAuthorSelected(true);
                                  setAccessSelected(false);
                                  setAccessQuery([]);
                                }}
                              >
                                Invite to author
                              </a>
                            )}
                          </Col>
                          <Col className="col-1">
                            {/* owner cannot lose access, and authors must be removed as authors
                          before they can lose access to the simulation. */}
                            {accessobj.username !== remoteSim?.owner ? (
                              <>
                                <Dropdown>
                                  <Dropdown.Toggle
                                    id="dropdown-basic"
                                    variant="link"
                                    className="caret-off"
                                    style={{ border: 0 }}
                                  >
                                    <i className="far fa-trash-alt hover-red"></i>
                                  </Dropdown.Toggle>
                                  <Dropdown.Menu>
                                    {RolePerms.hasAdminAccess(remoteSim) ? (
                                      <Dropdown.Item
                                        key={0}
                                        href=""
                                        onClick={() => {
                                          setFieldValue(
                                            "access.read.remove.username",
                                            accessobj.username
                                          );
                                          setTimeout(handleSubmit, 0);
                                          setTimeout(() =>
                                            setFieldValue("access.read.remove.username", "")
                                          );
                                        }}
                                      >
                                        Remove role: {prettyRole(accessobj.role)}
                                      </Dropdown.Item>
                                    ) : null}
                                    {author ? (
                                      <Dropdown.Item
                                        key={1}
                                        href=""
                                        onClick={() => {
                                          setFieldValue("author.remove.username", author.username);
                                          setTimeout(handleSubmit, 0);
                                          setTimeout(() => setFieldValue("author.remove", ""));
                                        }}
                                      >
                                        Remove from authors
                                      </Dropdown.Item>
                                    ) : null}
                                  </Dropdown.Menu>
                                </Dropdown>
                              </>
                            ) : null}
                          </Col>
                        </Row>
                      );
                    })}
                  </div>
                </Col>
              </Row>
              {authorSelected ? (
                <ConfirmSelected
                  selectedUser={values.author.add.username}
                  setSelected={setAuthorSelected}
                  formikProps={formikProps}
                  defaultInviteAuthor={true}
                />
              ) : null}
              {RolePerms.hasAdminAccess(remoteSim) ? (
                <>
                  <Row className="w-100 mt-4">
                    <Col>
                      <p className="lead" style={{ paddingLeft: "15px" }}>
                        Invite collaborators
                      </p>
                    </Col>
                  </Row>
                  <Row className="w-100 justify-content-left">
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
                          selectedUser={values.access.read.grant.username}
                          setSelected={setAccessSelected}
                          formikProps={formikProps}
                        />
                      ) : null}
                    </Col>
                  </Row>
                </>
              ) : null}
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
