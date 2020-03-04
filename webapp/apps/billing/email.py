from django.core.mail import EmailMessage

from webapp.settings import DEBUG


def send_teams_interest_mail(user):
    email_msg = EmailMessage(
        subject="Thank you for your interest in Compute Studio Teams",
        body=(
            "Hi,\n\n"
            "Thanks for getting in touch about a Team account.\n\n"
            "Are you open to scheduling a call to discuss what you need?\n\n"
            "Best,\n"
            "Matt"
        ),
        from_email="hank@compute.studio",
        to=[user.email],
        # bcc=["matt@compute.studio"],
    )
    try:
        email_msg.send(fail_silently=True)
    except Exception as e:
        print(e)
        if not DEBUG:
            raise e


def send_unsubscribe_email(user):
    email_msg = EmailMessage(
        subject="Thank you for using Compute Studio",
        body=(
            "Hi,\n\n"
            "We are sorry to hear that you are leaving Compute Studio.\n\n"
            "Are you open to scheduling a call to discuss how we could improve?\n\n"
            "Best,\n"
            "Matt"
        ),
        from_email="hank@compute.studio",
        to=[user.email],
        # bcc=["matt@compute.studio"],
    )
    try:
        email_msg.send(fail_silently=True)
    except Exception as e:
        print(e)
        if not DEBUG:
            raise e
