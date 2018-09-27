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
        assert user.profile.public_access

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

    def test_update_payment_info(self, client, profile, password):
        """
        Test update payment information
        - change payment
        - make sure of redirect and able to get done page
        - make sure payment info is updated
        """
        success = client.login(username=profile.user.username,
                               password=password)
        assert success

        user = auth.get_user(client)
        assert user.is_authenticated
        prev_default_source = user.customer.default_source
        assert prev_default_source

        resp = client.get('/billing/update/')
        assert resp.status_code == 200

        data = {'stripeToken': ['tok_bypassPending']}

        resp = client.post('/billing/update/', data=data)
        assert resp.status_code == 302
        assert resp.url == '/billing/update/done/'

        resp = client.get(resp.url)
        assert resp.status_code == 200

        user = auth.get_user(client)
        assert user.is_authenticated

        assert user.customer.default_source
        assert user.customer.default_source != prev_default_source

    def test_access_to_profile_pages(self, client):
        user = auth.get_user(client)
        assert not user.is_authenticated
        restricted = ['/users/profile/', '/users/password_change/',
                      '/users/password_change/done/', '/billing/update/',
                      '/billing/update/done/']
        for url in restricted:
            resp = client.get(url)
            assert resp.status_code == 302
            assert resp.url.startswith('/users/login/')
