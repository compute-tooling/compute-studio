import os

import stripe

from django.contrib.auth import get_user_model, forms as authforms
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMessage, send_mail

from .models import Profile, Project


User = get_user_model()

stripe.api_key = os.environ.get("STRIPE_SECRET")


class UserCreationForm(authforms.UserCreationForm):
    def save(self, commit=False):
        user = super().save()
        Profile.objects.create(user=user, is_active=True)
        email_msg = EmailMessage(
            subject="Welcome to COMP!",
            body=(
                f"Hello {user.username}, welcome to COMP. "
                f"Please write back here if you have any "
                f"questions or there is anything else we "
                f"can do to help you get up and running."
            ),
            from_email="henrymdoupe@gmail.com",
            to=[user.email],
            bcc=["matt.h.jensen@gmail.com"],
        )
        email_msg.send(fail_silently=True)
        return user

    class Meta(authforms.UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class UserChangeForm(authforms.UserChangeForm):
    class Meta(authforms.UserChangeForm.Meta):
        model = User
        fields = ("username", "email")


class ConfirmUsernameForm(forms.ModelForm):
    confirm_username = authforms.UsernameField(
        widget=forms.TextInput(attrs={"autofocus": True})
    )

    class Meta:
        model = User
        fields = ("confirm_username",)

    def clean(self):
        cleaned_data = super().clean()
        confirm_username = cleaned_data.get("confirm_username")
        if confirm_username != self.instance.username:
            self.add_error("confirm_username", "Username does not match.")


class CancelSubscriptionForm(ConfirmUsernameForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        if hasattr(user, "customer"):
            user.customer.cancel_subscriptions()
        user.profile.is_active = False
        if commit:
            user.profile.save()
            user.save()
        send_mail(
            "You have unsubscribed from COMP",
            (
                f"Hello {user.username}, you have recently unsubscribed "
                f"from COMP. We value your feedback. Please let us know why "
                f"you unsubscribed and how we can win you back in the future."
            ),
            "henrymdoupe@gmail.com",
            set([user.email, "henrymdoupe@gmail.com"]),
            fail_silently=True,
        )
        return user


class DeleteUserForm(CancelSubscriptionForm):
    def save(self, commit=True):
        user = super().save(commit=True)
        username = user.username
        email = user.email
        user.delete()
        send_mail(
            "You have deleted your account",
            (
                f"Hello {user.username}, you have recently deleted your "
                f"account. You have up to 5 days to change your mind and still "
                f"recover your data. If this is a mistake, please contact us at "
                f"admin@compmodels.com as soon as possible. If this was not a "
                f"mistake, please let us know why you deleted your account "
                f"and how we can win you back in the future."
            ),
            "henrymdoupe@gmail.com",
            set([user.email, "henrymdoupe@gmail.com"]),
            fail_silently=True,
        )
        return user
