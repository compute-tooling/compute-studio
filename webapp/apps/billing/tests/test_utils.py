import pytest

from django.contrib.auth import get_user_model

from webapp.apps.billing.utils import has_payment_method


User = get_user_model()


@pytest.mark.requires_stripe
def test_has_payment_method(db, customer):
    assert has_payment_method(customer.user)

    u = User.objects.create_user(
        username="pmt-test", email="testyo@email.com", password="testtest2222"
    )
    assert not has_payment_method(u)
