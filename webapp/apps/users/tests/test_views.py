import pytest

from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestUsersViews():

    def test_get_login(self, client):
        resp = client.get('/users/signup/')
        assert resp.status_code == 200

    def test_post_login(self, client, password):
        data = {
            'csrfmiddlewaretoken': ['abc123'],
            'username': ['tester'],
            'email': ['tester@testing.ai'],
            'password1': [password],
            'password2': [password],
            'stripeToken': ['tok_bypassPending']
        }
        resp = client.post('/users/signup/', data=data)
        assert resp.status_code == 302

        user = User.objects.get(username='tester')
        assert user
        assert user.customer
        assert user.profile
        assert user.profile.public_access