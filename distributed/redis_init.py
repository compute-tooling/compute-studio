import redis

import os


def main():
    admin_pw = os.environ.get("REDIS_ADMIN_PW")
    if admin_pw in (None, ""):
        print("No ADMIN PW found.")
        return

    conn_kwargs = dict(
        host=os.environ.get("REDIS_HOST", "127.0.0.1"),
        port=os.environ.get("REDIS_PORT", 6379),
        db=os.environ.get("REDIS_DB"),
    )

    try:
        client = redis.Redis(username="admin", password=admin_pw, **conn_kwargs)

        users = client.acl_users()
        if not ({"admin", "scheduler", "executor"} - set(users)):
            print("ACL users have already been set up.")
            return
    except redis.exceptions.ResponseError:
        # no admin found.
        client = redis.Redis(**conn_kwargs)

    # initialize users.
    print("No ACL users found. Initializing now.")
    if client.acl_whoami() == "default":
        nopass = admin_pw in (None, "")
        client.acl_setuser(
            "admin",
            enabled=True,
            nopass=nopass,
            passwords=f"+{admin_pw}" if not nopass else None,
            commands=["+@all"],
        )

        client.close()
        del client
        admin_client = redis.Redis(username="admin", password=admin_pw, **conn_kwargs)
    else:
        admin_client = client

    assert admin_client.acl_whoami() == "admin"

    admin_client.acl_setuser("default", enabled=False, commands=["-@all"])

    sched_pw = os.environ.get("REDIS_SCHEDULER_PW")
    nopass = sched_pw in (None, "")
    admin_client.acl_setuser(
        "scheduler",
        enabled=True,
        nopass=nopass,
        passwords=f"+{sched_pw}" if not nopass else None,
        commands=["-@all", "+set", "+get", "+acl|whoami"],
        keys=["job:"],
    )

    exec_pw = os.environ.get("REDIS_EXECUTOR_PW")
    nopass = exec_pw in (None, "")
    admin_client.acl_setuser(
        "executor",
        enabled=True,
        nopass=nopass,
        passwords=f"+{exec_pw}" if not nopass else None,
        commands=["-@all", "+get", "+acl|whoami"],
        keys=["job:"],
    )
    admin_client.close()

    print(f"Successfully created users: {admin_client.acl_users()}")


if __name__ == "__main__":
    main()
