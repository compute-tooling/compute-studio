import React = require("react");
import { Row, Col, Button, Modal, Dropdown } from "react-bootstrap";
import API from "./API";
import {
  Simulation,
  RemoteOutputs,
  DescriptionValues,
  Role,
  AccessStatus,
  ResourceLimitException,
} from "../types";
import { FormikProps, FormikHelpers } from "formik";
import ReactLoading from "react-loading";
import { RolePerms } from "../roles";

export interface CollaboratorValues {
  access: {
    read: {
      grant: {
        username: string;
        msg?: string;
      };
      remove: {
        username: string;
      };
    };
  };
  author: {
    add: {
      username: string;
      msg?: string;
    };
    remove: {
      username: string;
    };
  };
}

const AddCollaboratorException = (upgradeTo: "pro") => {
  let plan;
  if (upgradeTo === "pro") {
    plan = "Compute Studio Pro";
  }
  return (
    <div className="alert alert-primary alert-dismissible fade show" role="alert">
      You have reached the limit for the number of collaborators on private simulations. You may
      make this simulation public or upgrade to{" "}
      <a href="/billing/upgrade/">
        <strong>{plan}</strong>
      </a>{" "}
      to add more collaborators.
      <Row className="w-100 justify-content-center">
        <Col className="col-auto">
          <Button
            variant="primary"
            style={{ fontWeight: 600 }}
            className="w-100 mt-3"
            href="/billing/upgrade/"
          >
            Upgrade to {plan}
          </Button>
        </Col>
      </Row>
      <button type="button" className="close" data-dismiss="alert" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>
  );
};

const MakePrivateException = (upgradeTo: "pro") => {
  let plan;
  if (upgradeTo === "pro") {
    plan = "Compute Studio Pro";
  }
  return (
    <div className="alert alert-primary alert-dismissible fade show" role="alert">
      You have exceeded the limit for collaborators on a private simulation. You may keep this
      simulation public, as is, or upgrade to{" "}
      <a href="/billing/upgrade/">
        <strong>{plan}</strong>
      </a>{" "}
      to make it private.
      <Row className="w-100 justify-content-center">
        <Col className="col-auto">
          <Button
            variant="primary"
            style={{ fontWeight: 600 }}
            className="w-100 mt-3"
            href="/billing/upgrade/"
          >
            Upgrade to {plan}
          </Button>
        </Col>
      </Row>
      <button type="button" className="close" data-dismiss="alert" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>
  );
};

const PrivateAppException = (collaborator?: string) => {
  return (
    <div className="alert alert-primary alert-dismissible fade show" role="alert">
      {collaborator || "This user"} must be granted access to this app before they can become a
      collaborator.
      <button type="button" className="close" data-dismiss="alert" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>
  );
};

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
  resetState: () => void;
  formikProps: FormikProps<{ title: string; is_public: boolean } & CollaboratorValues>;
  defaultInviteAuthor?: boolean;
}> = ({ selectedUser, resetState, formikProps, defaultInviteAuthor }) => {
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
            <strong>Invite to coauthor</strong>
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
                    remove: { username: "" },
                  },
                  access: {
                    read: { grant: { username: "", msg: "" }, remove: { username: "" } },
                  },
                });
              } else {
                setValues({
                  ...formikProps.values,
                  author: { add: { username: "", msg: "" }, remove: { username: "" } },
                  access: {
                    read: {
                      grant: { username: selectedUser, msg: msg },
                      remove: { username: "" },
                    },
                  },
                });
              }

              setTimeout(handleSubmit, 0);

              setTimeout(() =>
                setValues({
                  ...values,
                  author: { add: { username: "", msg: "" }, remove: { username: "" } },
                  access: { read: { grant: { username: "", msg: "" }, remove: { username: "" } } },
                })
              );

              resetState();
            }}
          >
            <strong>Invite</strong>
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
                access: { read: { grant: { username: "", msg: "" }, remove: { username: "" } } },
              });
              setMsg("");
              resetState();
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
  formikProps: FormikProps<{ title: string; is_public: boolean } & CollaboratorValues>;
  plan: AccessStatus["plan"]["name"];
}> = ({ api, user, remoteSim, formikProps, plan }) => {
  const [show, setShow] = React.useState(false);
  const is_public =
    remoteSim?.is_public !== undefined ? remoteSim.is_public : formikProps.values.is_public;
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
      <CollaborationModal
        api={api}
        user={user}
        remoteSim={remoteSim}
        formikProps={formikProps}
        plan={plan}
        show={show}
        setShow={setShow}
      />
    </>
  );
};

export const CollaborationModal: React.FC<{
  api: API;
  user: string;
  remoteSim?: Simulation<RemoteOutputs>;
  formikProps: FormikProps<{ title: string; is_public: boolean } & CollaboratorValues>;
  plan: AccessStatus["plan"]["name"];
  show?: boolean;
  setShow: (show: boolean) => void;
}> = ({ api, user, remoteSim, formikProps, plan, show, setShow }) => {
  const [accessQuery, setAccessQuery] = React.useState<Array<{ username: string }>>([]);
  const [viewAccessQuery, setViewAccessQuery] = React.useState(false);
  const [accessSelected, setAccessSelected] = React.useState(false);

  const [authorSelected, setAuthorSelected] = React.useState(false);

  const [selectedUser, setSelectedUser] = React.useState("");

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

  let collabExceptionMsg;
  if (!!formikProps.status?.collaboratorLimit) {
    let collabMsg: ResourceLimitException = formikProps.status?.collaboratorLimit;
    if (collabMsg.test_name === "make_private") {
      collabExceptionMsg = MakePrivateException(collabMsg.upgrade_to);
    } else if (collabMsg.test_name === "add_collaborator") {
      collabExceptionMsg = AddCollaboratorException(collabMsg.upgrade_to);
    } else if (collabMsg.test_name === "add_collaborator_on_private_app") {
      collabExceptionMsg = PrivateAppException(collabMsg.collaborator);
    }
  }

  return (
    <Modal show={show} onHide={() => setShow(false)} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>Collaboration Settings</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {!!collabExceptionMsg ? (
          <Row className="w-100">
            <Col>{collabExceptionMsg}</Col>
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
                <div className="lead d-flex">
                  People{" "}
                  {formikProps.isSubmitting ? (
                    <ReactLoading
                      className="ml-2"
                      type="spokes"
                      color="#2b2c2d"
                      height={"1.5rem"}
                      width={"1.5rem"}
                    />
                  ) : null}
                </div>
                <div className="row-flush">
                  {accessobjs.map((accessobj, ix) => {
                    const author = authors.find(author => author.username === accessobj.username);
                    return (
                      <Row key={ix} className="w-100 p-2 justify-content-between row-flush-item">
                        <Col className="col-md-5 align-self-center">
                          <span>
                            <strong>{accessobj.username}</strong>
                          </span>
                        </Col>
                        <Col className="col-md-2 align-self-center">
                          {accessobj.is_owner ? (
                            <span>Owner</span>
                          ) : (
                            <span>{prettyRole(accessobj.role)}</span>
                          )}
                        </Col>
                        <Col className="col-md-4 align-self-center">
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
                                console.log("author set", accessobj.username);
                                setSelectedUser(accessobj.username);
                                setTimeout(() => {
                                  setAuthorSelected(true);
                                  setAccessSelected(false);
                                  setAccessQuery([]);
                                });
                              }}
                            >
                              Invite to coauthor
                            </a>
                          )}
                        </Col>
                        <Col className="col-md-1 align-self-center">
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
                selectedUser={selectedUser}
                resetState={() => {
                  setAuthorSelected(false);
                  setSelectedUser("");
                }}
                formikProps={formikProps}
                defaultInviteAuthor={true}
              />
            ) : null}
            {RolePerms.hasAdminAccess(remoteSim) && plan === "free" && !remoteSim.is_public ? (
              <Row className="w-100 mt-4 justify-content-center">
                <Col className="col-auto">
                  <Button
                    variant="success"
                    style={{ fontWeight: 600 }}
                    className="mb-4 w-100 mt-1"
                    href="/billing/upgrade/"
                  >
                    Upgrade to add private collaborators
                  </Button>
                </Col>
              </Row>
            ) : null}
            {RolePerms.hasAdminAccess(remoteSim) && (plan !== "free" || remoteSim.is_public) ? (
              <>
                <Row className="w-100 mt-4">
                  <Col>
                    <p className="lead" style={{ paddingLeft: "15px" }}>
                      Invite readers and coauthors
                    </p>
                  </Col>
                </Row>
                <Row className="w-100 justify-content-left">
                  <Col>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Search by username."
                      value={selectedUser}
                      onFocus={() => {
                        setViewAccessQuery(true);
                      }}
                      onChange={e => {
                        setViewAccessQuery(true);
                        handleQuery(e, users => setAccessQuery(users));
                        setSelectedUser(e.target.value);
                      }}
                      readOnly={accessSelected}
                    ></input>
                    <UserQuery
                      query={accessQuery}
                      selectedUsers={remoteSim.access}
                      show={viewAccessQuery}
                      onSelectUser={selected => {
                        if (remoteSim.access.find(a => a.username === selected.username)) return;
                        setSelectedUser(selected.username);
                        console.log("access set", selected.username);
                        setTimeout(() => {
                          setAccessSelected(true);
                          setAuthorSelected(false);
                          setAccessQuery([]);
                        });
                      }}
                    />
                    {accessSelected ? (
                      <ConfirmSelected
                        selectedUser={selectedUser}
                        resetState={() => {
                          setAccessSelected(false);
                          setSelectedUser("");
                        }}
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
  );
};

export const saveCollaborators = (
  api: API,
  values: CollaboratorValues,
  handleSuccess: () => void
) => {
  const promises = [];
  if (values.author?.add?.username) {
    promises.push(
      api.addAuthors({ authors: [values.author.add] }).then(() => {
        handleSuccess();
      })
    );
  }
  if (values.author?.remove?.username) {
    promises.push(
      api.deleteAuthor(values.author.remove.username).then(() => {
        handleSuccess();
      })
    );
  }
  if (values.access.read?.grant?.username) {
    promises.push(
      api
        .putAccess([
          {
            username: values.access.read.grant.username,
            role: "read" as Role,
            msg: values.access.read.grant.msg,
          },
        ])
        .then(() => {
          handleSuccess();
        })
    );
  }
  if (values.access.read?.remove?.username) {
    promises.push(
      api.putAccess([{ username: values.access.read.remove.username, role: null }]).then(() => {
        handleSuccess();
      })
    );
  }

  return Promise.all(promises);
};
