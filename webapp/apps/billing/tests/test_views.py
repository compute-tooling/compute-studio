import pytest

from django.contrib.auth import get_user_model


User = get_user_model()


@pytest.mark.django_db
@pytest.mark.requires_stripe
class TestBillingViews:
    def test_update_payment_info(self, client, profile, password):
        """
        Test update payment information
        - change payment
        - make sure of redirect and able to get done page
        - make sure payment info is updated
        """
        success = client.login(username=profile.user.username, password=password)
        assert success

        resp = client.get("/billing/update/")
        assert resp.status_code == 200

        data = {"stripeToken": ["tok_bypassPending"]}

        resp = client.post("/billing/update/", data=data)
        assert resp.status_code == 302
        assert resp.url == "/billing/update/done/"

        resp = client.get(resp.url)
        assert resp.status_code == 200

    def test_user_add_payment_method(self, client, user, password):
        """
        Test update payment information
        - user has no customer.
        - add payment method for user and thus add a customer relation.
        - make sure customer relation exists.
        """
        success = client.login(username=user.username, password=password)
        assert success

        assert not hasattr(user, "customer")

        resp = client.get("/billing/update/")
        assert resp.status_code == 200

        data = {"stripeToken": ["tok_bypassPending"]}

        resp = client.post("/billing/update/", data=data)
        assert resp.status_code == 302
        assert resp.url == "/billing/update/done/"

        resp = client.get(resp.url)
        assert resp.status_code == 200

        # refresh user object!
        user = User.objects.get(username=user.username)
        assert user.customer
