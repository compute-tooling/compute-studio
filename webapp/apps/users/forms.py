import os

import stripe

from django.contrib.auth import get_user_model, forms as authforms
from django import forms
from django.contrib.contenttypes.models import ContentType

from .models import Profile
from webapp.apps.billing.models import (Customer, Plan, Subscription,
                                        SubscriptionItem)


User = get_user_model()

stripe.api_key = os.environ.get('STRIPE_SECRET')


class UserCreationForm(authforms.UserCreationForm):

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
        Profile.create_from_user(user, is_active=True)
        customer.subscribe_to_public_plans()
        return user

    class Meta(authforms.UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')


class UserChangeForm(authforms.UserChangeForm):

    class Meta(authforms.UserChangeForm.Meta):
        model = User
        fields = ('username', 'email')


class ConfirmUsernameForm(forms.ModelForm):
    confirm_username = authforms.UsernameField(
        widget=forms.TextInput(attrs={'autofocus': True}))

    class Meta:
        model = User
        fields = ('confirm_username', )

    def clean(self):
        cleaned_data = super().clean()
        confirm_username = cleaned_data.get('confirm_username')
        if confirm_username != self.instance.username:
            self.add_error('confirm_username', 'Username does not match.')


class CancelSubscriptionForm(ConfirmUsernameForm):

    def save(self, commit=True):
        user = super().save(commit=False)
        user.customer.cancel_subscriptions()
        user.profile.is_active = False
        user.profile.save()
        user.save()
        return user