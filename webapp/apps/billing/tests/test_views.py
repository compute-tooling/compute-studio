import pytest

from django.contrib.auth import get_user_model
from django.shortcuts import reverse

from webapp.apps.users.models import create_profile_from_user
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
        assert resp.status_code == 302, f"Expected 302: got {resp.status_code}"
        assert resp.url == "/billing/upgrade/yearly/"

        resp = client.get(resp.url)
        assert resp.context["current_plan"] == customer.current_plan()
        assert resp.context["plan_duration"] == "yearly"
        assert resp.context["card_info"] == customer.card_info()

        resp = client.get("/billing/upgrade/monthly/")
        assert resp.status_code == 200, f"Expected 200: got {resp.status_code}"
        assert resp.context["plan_duration"] == "monthly"

        resp = client.get("/billing/upgrade/yearly/")
        assert resp.status_code == 200, f"Expected 200: got {resp.status_code}"
        assert resp.context["plan_duration"] == "yearly"

    @pytest.mark.parametrize(
        "plan_duration,other_duration", [("Monthly", "Yearly"), ("Yearly", "Monthly")]
    )
    def test_user_upgrade(
        self, client, customer, monkeypatch, plan_duration, other_duration
    ):
        """
        Test:
        - Upgrade to pro plan.
        - Change duration on pro plan (e.g. monthly vs. yearly).
        - Downgrade to free.
        """
        client.force_login(customer.user)

        # test /billing/upgrade redirects to landing page corresponding to correct duration.
        resp = client.get("/billing/upgrade/")
        assert resp.status_code == 302, f"Expected 302: got {resp.status_code}"
        next_url = resp.url
        assert next_url == reverse(
            "upgrade_plan_duration", kwargs=dict(plan_duration="yearly")
        )

        resp = client.get(f"/billing/upgrade/{plan_duration.lower()}/?upgrade_plan=pro")
        assert resp.status_code == 302, f"Expected 302: got {resp.status_code}"
        next_url = resp.url
        assert next_url == reverse(
            "upgrade_plan_duration_done",
            kwargs=dict(plan_duration=plan_duration.lower()),
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

        # test swap duration
        resp = client.get(
            f"/billing/upgrade/{other_duration.lower()}/?upgrade_plan=pro"
        )
        assert resp.status_code == 302, f"Expected 302: got {resp.status_code}"
        next_url = resp.url
        assert next_url == reverse(
            "upgrade_plan_duration_done",
            kwargs=dict(plan_duration=other_duration.lower()),
        )
        resp = client.get(next_url)
        assert resp.status_code == 200, f"Expected 200: got {resp.status_code}"
        assert resp.context["plan_duration"] == other_duration.lower()
        customer = Customer.objects.get(pk=customer.pk)
        assert (
            resp.context["current_plan"]
            == customer.current_plan()
            == {"plan_duration": other_duration.lower(), "name": "pro"}
        )

        # go back to initial plan_duration
        resp = client.get(f"/billing/upgrade/{plan_duration.lower()}/?upgrade_plan=pro")
        assert resp.status_code == 302, f"Expected 302: got {resp.status_code}"

        # Test downgrade to free plan.
        resp = client.get(
            f"/billing/upgrade/{plan_duration.lower()}/?upgrade_plan=free"
        )
        assert resp.status_code == 302, f"Expected 302: got {resp.status_code}"
        next_url = resp.url
        assert next_url == reverse(
            "upgrade_plan_duration_done",
            kwargs=dict(plan_duration=plan_duration.lower()),
        )
        resp = client.get(next_url)
        assert resp.status_code == 200, f"Expected 200: got {resp.status_code}"
        assert resp.context["plan_duration"] == plan_duration.lower()
        customer = Customer.objects.get(pk=customer.pk)
        assert (
            resp.context["current_plan"]
            == customer.current_plan()
            == {"plan_duration": None, "name": "free"}
        )

    def test_user_upgrade_next_url(self, client, customer, monkeypatch):
        """
        Test:
        - Test redirect after upgrade.
        """
        client.force_login(customer.user)
        exp_next_url = "/someone/appname/123/"
        # test /billing/upgrade redirects to landing page corresponding to correct duration.
        resp = client.get(f"/billing/upgrade/yearly/?next={exp_next_url}")
        assert resp.status_code == 200, f"Expected 200: got {resp.status_code}"

        resp = client.get(f"/billing/upgrade/yearly/?upgrade_plan=pro")
        assert resp.status_code == 302, f"Expected 302: got {resp.status_code}"
        next_url = resp.url
        assert next_url == exp_next_url

    def test_list_invoices(self, db, client, customer):
        """
        Test list invoice view:
        - Unauthenticated redirects to login.
        - List of invoices in context matches list in model.
        - Still matches after updating subscription.
        - Test with authenticated user without customer object.
        """
        resp = client.get("/billing/invoices/")
        assert resp.status_code == 302

        client.force_login(customer.user)
        resp = client.get("/billing/invoices/")
        assert resp.status_code == 200
        assert len(resp.context["invoices"]) == len(list(customer.invoices()))

        resp = client.get(f"/billing/upgrade/monthly/?upgrade_plan=pro")
        assert resp.status_code == 302, f"Expected 302: got {resp.status_code}"
        next_url = resp.url
        assert next_url == reverse(
            "upgrade_plan_duration_done", kwargs=dict(plan_duration="monthly")
        )

        resp = client.get("/billing/invoices/")
        assert resp.status_code == 200
        assert len(resp.context["invoices"]) == len(list(customer.invoices()))

        newuser = User.objects.create_user(
            "nocust", f"nocust@example.com", "heyhey2222"
        )
        create_profile_from_user(newuser)
        newuser.refresh_from_db()
        client.force_login(newuser)
        resp = client.get("/billing/invoices/")
        assert resp.status_code == 200
        assert len(resp.context["invoices"]) == 0
