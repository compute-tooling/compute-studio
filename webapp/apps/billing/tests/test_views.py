import pytest

from django.contrib.auth import get_user_model
from django.shortcuts import reverse

from webapp.apps.billing.models import Customer

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

    def test_upgrade_page(self, client, customer):
        """
        Test:
        - basic get
        - get with Monthly and Yearly durations.
        """
        client.force_login(customer.user)
        resp = client.get("/billing/upgrade/")
        assert resp.status_code == 200, f"Expected 200: got {resp.status_code}"

        assert resp.context["current_plan"] == customer.current_plan()
        assert resp.context["plan_duration"] == "monthly"
        assert resp.context["card_info"] == customer.card_info()

        resp = client.get("/billing/upgrade/monthly/")
        assert resp.status_code == 200, f"Expected 200: got {resp.status_code}"
        assert resp.context["plan_duration"] == "monthly"

        resp = client.get("/billing/upgrade/yearly/")
        assert resp.status_code == 200, f"Expected 200: got {resp.status_code}"
        assert resp.context["plan_duration"] == "yearly"

    @pytest.mark.parametrize("plan_duration", ["Monthly", "Yearly"])
    def test_user_upgrade(self, client, customer, monkeypatch, plan_duration):
        """
        Test:
        - Upgrade to pro plan.
        - Selecting team plan sends email.
        """
        client.force_login(customer.user)
        resp = client.get(f"/billing/upgrade/{plan_duration.lower()}/?upgrade_plan=pro")
        assert resp.status_code == 302, f"Expected 302: got {resp.status_code}"
        next_url = resp.url
        assert next_url == reverse(
            "upgrade_plan_duration", kwargs=dict(plan_duration=plan_duration.lower())
        )
        resp = client.get(next_url)
        assert resp.status_code == 200, f"Expected 200: got {resp.status_code}"
        assert resp.context["plan_duration"] == plan_duration.lower()
        customer = Customer.objects.get(pk=customer.pk)
        assert (
            resp.context["current_plan"]
            == customer.current_plan()
            == {"plan_duration": plan_duration.lower(), "name": "pro"}
        )

        # Test get Team sends email and does not change subscription status.

        called = []  # use list so that called keeps this memory ref.

        def mock_email(user, called=called):
            assert user == customer.user
            called += [True]

        monkeypatch.setattr(
            "webapp.apps.billing.views.send_teams_interest_mail", mock_email
        )

        resp = client.get(
            f"/billing/upgrade/{plan_duration.lower()}/?upgrade_plan=team"
        )
        assert resp.status_code == 200, f"Expected 200: got {resp.status_code}"
        assert called == [True]
        customer = Customer.objects.get(pk=customer.pk)
        assert (
            resp.context["current_plan"]
            == customer.current_plan()
            == {"plan_duration": plan_duration.lower(), "name": "pro"}
        )

        # Test get Free sends unsubscribe email and does not change subscription status.
        # (status will be changed manually for now.)

        called = []  # use list so that called keeps this memory ref.

        def mock_email2(user, called=called):
            assert user == customer.user
            called += [True]

        monkeypatch.setattr(
            "webapp.apps.billing.models.send_unsubscribe_email", mock_email2
        )

        resp = client.get(
            f"/billing/upgrade/{plan_duration.lower()}/?upgrade_plan=free"
        )
        assert resp.status_code == 302, f"Expected 302: got {resp.status_code}"
        assert resp.url == reverse(
            "upgrade_plan_duration", kwargs=dict(plan_duration=plan_duration.lower())
        )
        resp = client.get(resp.url)
        assert resp.status_code == 200, f"Expected 200: got {resp.status_code}"
        assert called == [True]
        customer = Customer.objects.get(pk=customer.pk)
        assert (
            resp.context["current_plan"]
            == customer.current_plan()
            == {"plan_duration": plan_duration.lower(), "name": "pro"}
        )
