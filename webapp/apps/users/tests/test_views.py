import pytest

from django.contrib import auth

User = auth.get_user_model()

@pytest.mark.django_db
class TestUsersViews():

    def test_get_login(self, client):
        resp = client.get('/users/signup/')
        assert resp.status_code == 200

    def test_post_login(self, client, password):
        data = {'csrfmiddlewaretoken': ['abc123'],
                'username': ['tester'],
                'email': ['tester@testing.ai'],
                'password1': [password],
                'password2': [password],
                'stripeToken': ['tok_bypassPending']}

        resp = client.post('/users/signup/', data=data)
        assert resp.status_code == 302

        user = User.objects.get(username='tester')
        assert user
        assert user.customer
        assert user.profile
        assert user.profile.is_active

    def test_get_profile(self, client, profile, password):
        success = client.login(username=profile.user.username,
                               password=password)
        assert success
        resp = client.get('/users/profile/')
        assert resp.status_code == 200

    def test_change_password(self, client, profile, password):
        success = client.login(username=profile.user.username,
                               password=password)
        assert success

        resp = client.get('/users/password_change/')
        assert resp.status_code == 200

        data = {'old_password': password,
                'new_password1': 'newpassyo1',
                'new_password2': 'newpassyo1'}

        resp = client.post('/users/password_change/', data=data)
        assert resp.status_code == 302
        assert resp.url == '/users/password_change/done/'

        resp = client.get('/users/password_change/done/')
        assert resp.status_code == 200

    def test_cancel_subscriptions(self, client, profile, password):
        success = client.login(username=profile.user.username,
                               password=password)
        assert success

        resp = client.get('/users/profile/cancel/')
        assert resp.status_code == 200
        data = {'confirm_username': profile.user.username}
        resp = client.post('/users/profile/cancel/', data=data)
        assert resp.status_code == 302
        assert resp.url == '/users/profile/cancel/done/'

        resp = client.get(resp.url)
        assert resp.status_code == 200

    def test_delete_user(self, client, profile, password):
        success = client.login(username=profile.user.username,
                               password=password)
        assert success

        resp = client.get('/users/profile/delete/')
        assert resp.status_code == 200
        data = {'confirm_username': profile.user.username}
        resp = client.post('/users/profile/delete/', data=data)
        assert resp.status_code == 302
        assert resp.url == '/users/profile/delete/done/'

        resp = client.get(resp.url)
        assert resp.status_code == 200
        user = auth.get_user(client)
        assert not user.is_authenticated

    def test_access_to_profile_pages(self, client):
        user = auth.get_user(client)
        assert not user.is_authenticated
        restricted = ['/users/profile/', '/users/password_change/',
                      '/users/password_change/done/', '/billing/update/',
                      '/billing/update/done/', '/users/profile/cancel/',
                      '/users/profile/cancel/done/', '/users/profile/delete/']
        for url in restricted:
            resp = client.get(url)
            assert resp.status_code == 302
            assert resp.url.startswith('/users/login/')