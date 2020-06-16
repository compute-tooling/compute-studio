from django.contrib import auth
from rest_framework.authtoken.models import Token

from webapp.apps.users.models import Profile
from webapp.apps.billing.models import Customer, stripe


User = auth.get_user_model()


def gen_blank_customer(username, email, password):
    user = User.objects.create_user(username=username, email=email, password=password)
    Token.objects.create(user=user)
    stripe_customer = stripe.Customer.create(email=email, source="tok_bypassPending")
    customer, _ = Customer.get_or_construct(stripe_customer.id, user)
    return Profile.objects.create(user=customer.user, is_active=True)
