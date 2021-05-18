import argparse
from getpass import getpass

from cs_workers.services.api.security import get_password_hash
from cs_workers.services.api.models import User
from cs_workers.services.api.database import SessionLocal
from cs_workers.services.api.schemas import User as UserSchema

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username")
    parser.add_argument("--email")
    args = parser.parse_args()

    password = getpass()
    assert password, "Password required."

    user = User(
        username=args.username,
        hashed_password=get_password_hash(password),
        email=args.email,
        is_superuser=True,
        is_active=True,
        url=None,
    )
    session = SessionLocal()
    session.add(user)
    session.commit()
    session.refresh(user)
    print("User created successfully:")
    print(UserSchema.from_orm(user).dict())
