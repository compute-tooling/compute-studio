import os

import stripe

from django.contrib.auth import get_user_model, forms
from django.contrib.contenttypes.models import ContentType

from .models import Profile
from webapp.apps.billing.models import (Customer, Plan, Subscription,
                                        SubscriptionItem)


User = get_user_model()

stripe.api_key = os.environ.get('STRIPE_SECRET')


def subscribe_to_public_plans(customer):
    public_plans = Plan.get_public_plans(usage_type='metered')
    stripe_sub = Subscription.create_stripe_object(customer, public_plans)
    sub = Subscription.construct(stripe_sub, customer, public_plans)
    for raw_si in stripe_sub['items']['data']:
        stripe_si = SubscriptionItem.get_stripe_object(raw_si['id'])
        plan = public_plans.get(stripe_id=raw_si['plan']['id'])
        si, created = SubscriptionItem.get_or_construct(stripe_si.id, plan,
                                                        sub)


class UserCreationForm(forms.UserCreationForm):

    # stripe_token = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stripe_token = kwargs.get('stripeToken')

    def save(self, commit=False):
        user = super().save()
        stripe_customer = stripe.Customer.create(
            email=user.email,
            source=self.stripe_token
        )
        customer = Customer.construct(stripe_customer, user=user)
        Profile.create_from_user(user, public_access=True)
        subscribe_to_public_plans(customer)
        return user

    class Meta(forms.UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')


class UserChangeForm(forms.UserChangeForm):

    class Meta(forms.UserChangeForm.Meta):
        model = User
        fields = ('username', 'email')
