import httpx
import jwt
import pytest
import redis

from cs_workers.services.auth import User, redis_conn, UserNotFound, cryptkeeper


@pytest.fixture(scope="function")
def user():
    try:
        _user = User.get(username="hdoupe")
        _user.delete()
    except UserNotFound:
        pass

    yield User.create(
        username="hdoupe",
        email="hdoupe@example.com",
        url="http://localhost:8000",
        approved=False,
    )
    try:
        u = User.get(username="hdoupe")
    except UserNotFound:
        pass
    else:
        u.delete()


class TestUser:
    def test_create_user(self, user):
        with redis.Redis(**redis_conn) as rclient:
            user_vals = rclient.hgetall("users-hdoupe")

        assert user_vals
        assert cryptkeeper.decrypt(user.jwt_secret)

    def test_get_user(self, user):
        oth = User.get(username=user.username)
        assert oth == user

    def test_not_found(self, user):
        with pytest.raises(UserNotFound):
            User.get(username="whoops")

    def test_delete(self, user):
        assert user.delete()
        assert not user.delete()

        with pytest.raises(UserNotFound):
            User.get(username=user.username)

    def test_dump(self, user):
        assert list(user.dump().keys()) == user.fields
        assert "jwt_secret" not in user.dump()
        assert "jwt_secret" in user.dump(include_jwt_secret=True)

    def test_jwt(self, user):
        jwt_token = user.get_jwt_token()
        assert user.read_jwt_token(jwt_token) == user.dump()


class TestApi:
    base_url = "http://localhost:8888"
    client = httpx.Client(base_url=base_url)

    def test_get(self, user):
        resp = self.client.get("/auth/")
        assert resp.status_code == 403

        resp = self.client.get(
            "/auth/",
            headers={"Authorization": user.get_jwt_token(), "Cluster-User": "hdoupe",},
        )
        assert resp.status_code == 200
        assert resp.json() == user.dump()

        invalid_token = jwt.encode(user.dump(), "abc123")
        resp = self.client.get(
            "/auth/",
            headers={"Authorization": invalid_token, "Cluster-User": "hdoupe",},
        )
        assert resp.status_code == 403

    def test_post(self):
        resp = self.client.post(
            "/auth/",
            json={
                "username": "hdoupe",
                "email": "test@example.com",
                "url": "http://test.com",
            },
        )
        assert resp.status_code == 200
        user = User.get(username="hdoupe")
        data = resp.json()
        assert data == user.dump(include_jwt_secret=True)

        resp = self.client.post(
            "/auth/",
            json={
                "username": "hdoupe",
                "email": "test@example.com",
                "url": "http://test.com",
            },
        )
        assert resp.status_code == 400

    def test_delete(self, user):
        resp = self.client.delete("/auth/")
        assert resp.status_code == 403

        resp = self.client.delete(
            "/auth/",
            headers={"Authorization": user.get_jwt_token(), "Cluster-User": "hdoupe",},
        )
        assert resp.status_code == 204

        with pytest.raises(UserNotFound):
            User.get(username=user.username)

        invalid_token = jwt.encode(user.dump(), "abc123")
        resp = self.client.delete(
            "/auth/",
            headers={"Authorization": invalid_token, "Cluster-User": "hdoupe",},
        )
        assert resp.status_code == 403
