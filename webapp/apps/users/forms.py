import os

import stripe

from django.contrib.auth import get_user_model, forms as authforms
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _

from .models import Profile, Project, create_profile_from_user


User = get_user_model()

stripe.api_key = os.environ.get("STRIPE_SECRET")


class UserCreationForm(authforms.UserCreationForm):
    error_messages = {
        "password_mismatch": _("The two password fields didn’t match."),
        "duplicate_email": _("A user is already registered with this e-mail address."),
    }

    def save(self, commit=False):
        user = super().save()
        create_profile_from_user(user)
        return user

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                self.error_messages["duplicate_email"], code="duplicate_email"
            )
        return email

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
