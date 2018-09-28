import pytest

@pytest.mark.django_db
class TestBillingViews():

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

        resp = client.get('/billing/update/')
        assert resp.status_code == 200

        data = {'stripeToken': ['tok_bypassPending']}

        resp = client.post('/billing/update/', data=data)
        assert resp.status_code == 302
        assert resp.url == '/billing/update/done/'

        resp = client.get(resp.url)
        assert resp.status_code == 200

    def test_update_payment_no_customer(self, client, user, password):
        """
        Test update payment information
        - change payment
        - make sure of redirect and able to get done page
        - make sure payment info is updated
        """
        success = client.login(username=user.username,
                               password=password)
        assert success

        resp = client.get('/billing/update/')
        assert resp.status_code == 200

        data = {'stripeToken': ['tok_bypassPending']}

        resp = client.post('/billing/update/', data=data)
        assert resp.status_code == 404
