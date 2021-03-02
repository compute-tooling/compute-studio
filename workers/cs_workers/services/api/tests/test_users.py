from .. import models


class TestUsers:
    def test_create_user(self, db, client):
        resp = client.post(
            "/api/v1/users/",
            json={
                "email": "new_user@test.com",
                "username": "new_user",
                "password": "hello world",
                "url": "https://example.com",
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json() == {
            "email": "new_user@test.com",
            "username": "new_user",
            "url": "https://example.com",
            "is_approved": False,
            "is_active": True,
        }

    def test_login_user(self, db, client, new_user):
        resp = client.post(
            "/api/v1/login/access-token",
            data={"username": "test", "password": "heyhey2222"},
        )
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        assert resp.json().get("access_token")
        assert resp.json().get("expires_at")

    def test_get_current_user(self, db, client, new_user):
        resp = client.post(
            "/api/v1/login/access-token",
            data={"username": "test", "password": "heyhey2222"},
        )
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        access_token = resp.json()["access_token"]
        resp = client.get(
            "/api/v1/users/me/", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        assert resp.json()["username"]

    def test_approve_user(self, db, client, new_user, superuser):
        resp = client.post(
            "/api/v1/login/access-token",
            data={"username": "super-user", "password": "heyhey2222"},
        )

        assert resp.status_code == 200

        assert superuser.is_superuser
        assert not new_user.is_approved
        print("user.username", new_user.username, type(new_user.username))
        access_token = resp.json()["access_token"]
        resp = client.post(
            "/api/v1/users/approve/",
            json={"username": new_user.username, "is_approved": True},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"

        db.refresh(new_user)
        assert new_user.is_approved
