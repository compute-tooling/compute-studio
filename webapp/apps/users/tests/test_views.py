import pytest

from django.contrib import auth

User = auth.get_user_model()


@pytest.mark.django_db
class TestUsersViews:
    def test_get_login(self, client):
        resp = client.get("/users/signup/")
        assert resp.status_code == 200

    def test_post_signup(self, client, password):
        data = {
            "csrfmiddlewaretoken": ["abc123"],
            "username": ["testlogin"],
            "email": ["tester@testing.ai"],
            "password1": [password],
            "password2": [password],
        }

        resp = client.post("/users/signup/", data=data)
        assert resp.status_code == 302

        user = User.objects.get(username="testlogin")
        assert user
        assert user.profile
        assert user.profile.is_active

        # test email cannot be re-used.
        data = {
            "csrfmiddlewaretoken": ["abc123"],
            "username": ["testlogin"],
            "email": ["tester@testing.ai"],
            "password1": [password],
            "password2": [password],
        }

        resp = client.post("/users/signup/", data=data)
        assert resp.status_code == 200
        assert resp.context["form"].errors == {
            "email": ["A user is already registered with this e-mail address."],
            "username": ["A user with that username already exists."],
        }

    def test_didnt_break_pw_confirm_validation(self, client, password):
        # Make sure validation wasn't broken from modifying the django
        # user creation form error message dictionary.
        data = {
            "csrfmiddlewaretoken": ["abc123"],
            "username": ["testlogin"],
            "email": ["tester@testing.ai"],
            "password1": [password],
            "password2": [password + "heyo"],
        }

        resp = client.post("/users/signup/", data=data)
        assert resp.status_code == 200
        assert resp.context["form"].errors == {
            "password2": ["The two password fields didn’t match."]
        }

    def test_signup_over_api(self, api_client):
        data = {
            "email": "random@testing.com",
            "username": "random123",
            "password1": "heyhey2222",
            "password2": "heyhey2222",
        }
        resp = api_client.post("/rest-auth/registration/", data)
        assert resp.status_code == 201

        user = User.objects.get(username="random123")
        assert user.profile

    def test_get_user_settings(self, client, profile, password):
        success = client.login(username=profile.user.username, password=password)
        assert success
        resp = client.get("/users/settings/")
        assert resp.status_code == 200

    def test_change_password(self, client, profile, password):
        success = client.login(username=profile.user.username, password=password)
        assert success

        resp = client.get("/users/password_change/")
        assert resp.status_code == 200

        data = {
            "old_password": password,
            "new_password1": "newpassyo1",
            "new_password2": "newpassyo1",
        }

        resp = client.post("/users/password_change/", data=data)
        assert resp.status_code == 302
        assert resp.url == "/users/password_change/done/"

        resp = client.get("/users/password_change/done/")
        assert resp.status_code == 200

    def test_cancel_subscriptions(self, client, profile, password):
        success = client.login(username=profile.user.username, password=password)
        assert success

        resp = client.get("/users/cancel/")
        assert resp.status_code == 200
        data = {"confirm_username": profile.user.username}
        resp = client.post("/users/cancel/", data=data)
        assert resp.status_code == 302
        assert resp.url == "/users/cancel/done/"

        resp = client.get(resp.url)
        assert resp.status_code == 200

    def test_delete_user(self, client, profile, password):
        success = client.login(username=profile.user.username, password=password)
        assert success

        resp = client.get("/users/delete/")
        assert resp.status_code == 200
        data = {"confirm_username": profile.user.username}
        resp = client.post("/users/delete/", data=data)
        assert resp.status_code == 302
        assert resp.url == "/users/delete/done/"

        resp = client.get(resp.url)
        assert resp.status_code == 200
        user = auth.get_user(client)
        assert not user.is_authenticated

    def test_user_lookup(self, api_client, profile):
        resp = api_client.get("/users/autocomplete?username=hd")
        assert resp.status_code == 403

        api_client.force_login(profile.user)
        resp = api_client.get("/users/autocomplete?username=hd")
        assert resp.status_code == 200
        assert {"username": "hdoupe"} in resp.data

        resp = api_client.get("/users/autocomplete?username=''")
        assert resp.status_code == 200
        assert resp.data == []

        resp = api_client.get("/users/autocomplete?username=")
        assert resp.status_code == 200
        assert resp.data == []

    def test_access_to_profile_pages(self, client):
        user = auth.get_user(client)
        assert not user.is_authenticated
        restricted = [
            "/users/settings/",
            "/users/password_change/",
            "/users/password_change/done/",
            "/billing/update/",
            "/billing/update/done/",
            "/users/cancel/",
            "/users/cancel/done/",
            "/users/delete/",
        ]
        for url in restricted:
            resp = client.get(url)
            assert resp.status_code == 302
            assert resp.url.startswith("/users/login/")

    def test_access_api(self, api_client, profile, password, test_models):
        user = auth.get_user(api_client)
        assert not user.is_authenticated

        project, sponsored_project = test_models[0].project, test_models[1].project

        resp = api_client.get("/users/status/")
        assert resp.data == {
            "user_status": "anon",
            "api_url": "/users/status/",
            "username": None,
            "plan": {"name": "free", "plan_duration": None},
        }

        resp = api_client.get(
            f"/users/status/{project.owner.user.username}/{project.title}/"
        )
        assert resp.data == {
            "user_status": "anon",
            "is_sponsored": False,
            "sponsor_message": None,
            "can_run": False,
            "exp_cost": project.exp_job_info(adjust=True)[0],
            "exp_time": project.exp_job_info(adjust=True)[1],
            "server_cost": project.server_cost,
            "api_url": f"/users/status/{project.owner.user.username}/{project.title}/",
            "username": None,
            "plan": {"name": "free", "plan_duration": None},
        }

        resp = api_client.get(
            f"/users/status/{sponsored_project.owner.user.username}/{sponsored_project.title}/"
        )
        assert resp.data == {
            "user_status": "anon",
            "is_sponsored": True,
            "sponsor_message": None,
            "can_run": False,
            "exp_cost": sponsored_project.exp_job_info(adjust=True)[0],
            "exp_time": sponsored_project.exp_job_info(adjust=True)[1],
            "server_cost": sponsored_project.server_cost,
            "api_url": f"/users/status/{sponsored_project.owner.user.username}/{sponsored_project.title}/",
            "username": None,
            "plan": {"name": "free", "plan_duration": None},
        }

        assert api_client.login(username=profile.user.username, password=password)
        resp = api_client.get("/users/status/")
        assert resp.data == {
            "user_status": profile.status,
            "api_url": "/users/status/",
            "username": profile.user.username,
            "plan": {"name": "free", "plan_duration": None},
        }
